# Standard library imports
import os
import time
import torch
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
        
        # Get embeddings for unique documents
        text_embeddings = self.load_embeddings(granularity, embeddings, docs)
        if not text_embeddings:
            print(f"[WARN] No embeddings generated for granularity {granularity}. Skipping FAISS build.")
            return
        
        print(f"[FAISS] Building index for {granularity} granularity with {len(text_embeddings)} documents")
        
        torch.cuda.empty_cache()
        # Process in smaller batches to avoid memory issues
        batch_size = 10000  # Reduced batch size for memory safety
        all_metadatas = [doc.metadata for doc in docs]
        
        # Create initial FAISS store with first batch
        first_batch = text_embeddings[:batch_size]
        first_metadatas = all_metadatas[:batch_size]
        faiss_store = FAISS.from_embeddings(first_batch, embedding=embeddings, metadatas=first_metadatas)
        
        # Add remaining batches incrementally
        for i in range(batch_size, len(text_embeddings), batch_size):
            batch = text_embeddings[i:i + batch_size]
            batch_metadatas = all_metadatas[i:i + batch_size]
            
            batch_text_embeddings = list(zip([item[0] for item in batch], [item[1] for item in batch]))
            faiss_store.add_embeddings(
                text_embeddings=batch_text_embeddings,
                metadatas=batch_metadatas
            )
            
            print(f"[FAISS] Processed batch {i//batch_size + 1}/{(len(text_embeddings) + batch_size - 1)//batch_size}")
            del batch, batch_metadatas
            gc.collect()

        print(f"[FAISS] Saving index to {path}")
        del text_embeddings, all_metadatas
        gc.collect()
        
        if faiss_store is not None:
            faiss_store.save_local(path)
            del faiss_store
            gc.collect()
        
        print(f"[FAISS] Index for {granularity} granularity saved to {path}")

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
                # Force garbage collection after each FAISS build
                gc.collect()

        print("[INFO] All retrievers built successfully.")
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

        # Extract texts from documents (docs are already deduplicated)
        texts = [doc.page_content for doc in docs]
        chunk_size = 10000
        batch_size = 128

        with tqdm(total=len(texts), desc=f"Embedding texts at {granularity} granularity") as pbar \
             , open(faiss_cache_path, "wb") as f:
            for i in range(0, len(texts), chunk_size):
                batch = texts[i:i + chunk_size]
                try:
                    batch_vectors = model.encode(
                        batch,
                        batch_size=batch_size,
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
                        print(f"[WARN] CUDA OOM at batch_size={128}, retrying with half size")
                        batch_size = 64
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
        
        # Return texts with their vectors
        print(f"[COMPLETE] Loaded {len(vectors)} vectors for {granularity} granularity")
        return list(zip(texts, vectors))