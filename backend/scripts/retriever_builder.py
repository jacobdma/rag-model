# Standard library imports
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Library specific imports
import dill
from tqdm import tqdm
from numpy import ndarray
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.retrievers import BM25Retriever
from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document
import gc

# Local imports
from .chunk_documents import DocumentChunker
from .load_utils import CACHE_DIR

class RetrieverBuilder:
    # Dict of retriever granularities with granularity, size, and overlap
    GRANULARITIES = {
        "small": (512, 50),
        "medium": (1024, 100),
        "large": (2048, 200)
    }

    def __init__(self, folder_paths: list[str]):
        self.folder_paths = folder_paths
        self.index_dir = os.path.join(os.path.dirname(__file__), "..", "indexes")
        os.makedirs(self.index_dir, exist_ok=True)
        self.bm25_paths = {g: os.path.join(self.index_dir, f"bm25_{g}.dill") for g in self.GRANULARITIES}
        self.faiss_paths = {g: os.path.join(self.index_dir, f"faiss_{g}") for g in self.GRANULARITIES}
        self.chunker = DocumentChunker(self.folder_paths)

    def _get_missing_retrievers(self):
        """
        Gathers missing retrievers 
        """
        missing_bm25 = {g for g, path in self.bm25_paths.items() if not os.path.exists(path)}
        missing_faiss = {g for g, path in self.faiss_paths.items() if not os.path.exists(path)}
        return missing_bm25, missing_faiss

    def build_faiss(self, docs, path, granularity, embeddings):
        if not docs:
            print(f"[WARN] No documents to embed for granularity {granularity}. Skipping FAISS build.")
            return
        text_embeddings = self.load_embeddings(granularity, embeddings, docs)
        if not text_embeddings:
            print(f"[WARN] No embeddings generated for granularity {granularity}. Skipping FAISS build.")
            return
        
        # Extract texts and vectors from the embeddings
        texts, vectors = zip(*text_embeddings)
        
        # Create metadata for deduplicated texts
        # We need to reconstruct metadata for the deduplicated texts
        unique_metadata = []
        seen_texts = set()
        for doc in docs:
            text = doc.page_content
            if text not in seen_texts:
                unique_metadata.append(doc.metadata)
                seen_texts.add(text)
        
        # Add vectors to FAISS in batches to prevent memory errors
        batch_size = 10000  # Adjust this value based on your memory constraints
        faiss_store = None
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_vectors = vectors[i:i + batch_size]
            batch_metadata = unique_metadata[i:i + batch_size]
            batch_embeddings = list(zip(batch_texts, batch_vectors))
            
            if faiss_store is None:
                faiss_store = FAISS.from_embeddings(batch_embeddings, embedding=embeddings, metadatas=batch_metadata)
            else:
                faiss_store.add_embeddings(batch_embeddings, metadatas=batch_metadata)
        
        if faiss_store is not None:
            faiss_store.save_local(path)

    def _faiss_load(self, path, granularity, embeddings):
        t0 = time.time()
        index = FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
        print(f"[FAISS] Loaded '{granularity}' in {time.time() - t0:.2f}s")
        return ('faiss', granularity, index)

    def build_bm25(self, docs, path):
        bm25 = BM25Retriever.from_documents(docs)
        with open(path, "wb") as f:
            dill.dump(bm25, f)

    def _bm25_load(self, path, granularity):
        t0 = time.time()
        with open(path, "rb") as f:
            result = dill.load(f)
        print(f"[BM25] Loaded '{granularity}' in {time.time() - t0:.2f}s")
        return ('bm25', granularity, result)

    def build_retrievers(self) -> tuple[dict[str, BM25Retriever], dict[str, FAISS], dict[str, dict[str, list[Document]]]]:
        """Load or build BM25 and FAISS retrievers, caching FAISS in memory. Returns chunk dict as dict[granularity][source] = [docs]."""
        missing_bm25, missing_faiss = self._get_missing_retrievers()
        model = SentenceTransformer("BAAI/bge-large-en-v1.5", device="cuda")
        model = model.half()

        # Build missing retrievers
        chunks_by_granularity = {}
        for granularity in self.GRANULARITIES:
            chunk_size, chunk_overlap = self.GRANULARITIES[granularity]
            chunks_by_source = self.chunker.get_chunks(granularity, chunk_size, chunk_overlap)
            chunks_by_granularity[granularity] = chunks_by_source
            docs = [doc for doc_list in chunks_by_source.values() for doc in doc_list]
            if granularity in missing_bm25:
                self.build_bm25(docs, self.bm25_paths[granularity])
            if granularity in missing_faiss:
                self.build_faiss(docs, self.faiss_paths[granularity], granularity, model)

        # Load all retrievers in parallel
        with ThreadPoolExecutor(max_workers=8) as executor:
            bm25_futures = [
                executor.submit(self._bm25_load, path, g)
                for g, path in self.bm25_paths.items()
            ]
            faiss_futures = [
                executor.submit(self._faiss_load, path, g, model)
                for g, path in self.faiss_paths.items()
            ]
            retrievers_bm25, retrievers_faiss = {}, {}
            for future in as_completed(bm25_futures + faiss_futures):
                result_type, granularity, data = future.result()
                if result_type == 'bm25':
                    retrievers_bm25[granularity] = data
                else:
                    retrievers_faiss[granularity] = data
        return retrievers_bm25, retrievers_faiss, chunks_by_granularity

    @staticmethod
    def load_embeddings(granularity: str, model, docs: list[Document]) -> list[tuple[str, list[float]]]:
        """
        Embeds docs (list of Documents), caches and loads vectors for FAISS.
        Streams embedding batches to disk to minimize memory usage.
        Returns list of zipped(text, vector) pairs in original order.
        """
        import gc
        faiss_cache_path = CACHE_DIR / f"faiss_cache_{granularity}.pkl"
        if faiss_cache_path.exists():
            texts = [doc.page_content for doc in docs]
            print("[CACHE] Loading FAISS vectors from cache...")
            vectors = []
            with open(faiss_cache_path, "rb") as f:
                while True:
                    try:
                        batch = dill.load(f)
                        vectors.extend(batch)
                    except EOFError:
                        break
            # Convert cached vectors to lists if they're numpy arrays
            vectors = [v.tolist() if hasattr(v, 'tolist') else v for v in vectors]
            return list(zip(texts, vectors))

        # Deduplicate texts while preserving metadata correspondence
        unique_texts = []
        unique_metadata = []
        seen = set()
        for doc in docs:
            text = doc.page_content
            if text not in seen:
                unique_texts.append(text)
                unique_metadata.append(doc.metadata)
                seen.add(text)
        chunk_size = 50000

        with tqdm(total=len(unique_texts), desc=f"Embedding unique texts at {granularity} granularity") as pbar:
            with open(faiss_cache_path, "wb") as f:
                for i in range(0, len(unique_texts), chunk_size):
                    batch = unique_texts[i:i + chunk_size]
                    try:
                        batch_vectors = model.encode(
                            batch,
                            batch_size=256,
                            show_progress_bar=False,
                            convert_to_numpy=True,
                            normalize_embeddings=True
                        )
                        # Write each batch to disk immediately
                        dill.dump(batch_vectors, f)
                        pbar.update(len(batch))
                        del batch_vectors
                        gc.collect()
                    except RuntimeError as e:
                        if "CUDA out of memory" in str(e):
                            print(f"[WARN] CUDA OOM at batch_size={batch_size}, retrying with half size")
                            batch_size //= 2
                            continue
                        raise

        # Reconstruct full list of vectors in original order by reading all batches from disk
        vectors = []
        with open(faiss_cache_path, "rb") as f:
            while True:
                try:
                    batch = dill.load(f)
                    vectors.extend(batch)
                except EOFError:
                    break
        vectors = [v.tolist() if hasattr(v, 'tolist') else v for v in vectors]
        
        # Return deduplicated texts with their vectors
        return list(zip(unique_texts, vectors))