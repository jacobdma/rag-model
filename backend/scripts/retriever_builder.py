# Standard library imports
import gc
import os
import time
import torch

# Library specific imports
import dill
from tqdm import tqdm
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

# Local imports
from .chunk_documents import DocumentChunker
from .hybrid_retriever import HybridRetriever
from .load_utils import CACHE_DIR

class RetrieverBuilder:
    CHUNK_SIZE = 1024
    CHUNK_OVERLAP = 100

    def __init__(self, folder_paths: list[str]):
        self.folder_paths = folder_paths
        self.index_dir = os.path.join(os.path.dirname(__file__), "..", "indexes")
        os.makedirs(self.index_dir, exist_ok=True)

        self.bm25_path = os.path.join(self.index_dir, f"bm25.dill")
        self.faiss_path = os.path.join(self.index_dir, f"faiss.dill")
        self.chunker = DocumentChunker(self.folder_paths)

    def build_faiss(self, docs, embeddings):
        # Underlying SentenceTransformer model used for encoding
        model = embeddings._client
        if not os.path.exists(self.faiss_path):
            try:
                cache_path = CACHE_DIR / f"faiss_embeddings.pkl"
                
                if cache_path.exists():
                    print("[FAISS] Loading cached embeddings...")
                    embedding_vectors = self._load_embeddings(cache_path, docs)
                else:
                    print("[FAISS] Generating embeddings...")
                    embedding_vectors = self._generate_embeddings(model, cache_path, docs)
                
            finally:
                torch.cuda.empty_cache()
                gc.collect()
                print("[FAISS] Embedding model cleaned up")

        if not docs:
            print(f"[WARN] No documents to embed. Skipping FAISS build.")
            return
        
        print(f"[FAISS] Building index with {len(embedding_vectors)} documents")
        
        batch_size = 5000
        metadatas = [doc.metadata for doc in docs]
        
        # Create initial FAISS store with first batch
        first_batch_size = min(batch_size, len(embedding_vectors))
        first_batch = embedding_vectors[:batch_size]
        first_metadatas = metadatas[:batch_size]
        faiss_store = FAISS.from_embeddings(first_batch, embedding=embeddings, metadatas=first_metadatas)
        
        for i in range(batch_size, len(embedding_vectors), batch_size):
            batch = embedding_vectors[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]

            faiss_store.add_embeddings(
                text_embeddings=batch,
                metadatas=batch_metadatas
            )

            del batch, batch_metadatas
            gc.collect()

        del embedding_vectors, metadatas, model
        torch.cuda.empty_cache()
        gc.collect()
        
        faiss_store.save_local(self.faiss_path)

        return faiss_store
    

    def build_retrievers(self) -> tuple[dict[str, BM25Retriever], dict[str, FAISS], dict[str, dict[str, list[Document]]]]:
        """Load or build BM25 and FAISS retrievers, caching FAISS in memory. Returns chunk dict as dict[source] = [docs]."""
        embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-en-v1.5",
            model_kwargs={'device': 'cuda'}
        )

        # Build missing retrievers
        chunks_by_source = self.chunker.get_chunks(self.CHUNK_SIZE, self.CHUNK_OVERLAP)
        docs = [doc for doc_list in chunks_by_source.values() for doc in doc_list]

        if not os.path.exists(self.bm25_path):
            bm25 = BM25Retriever.from_documents(docs)
            with open(self.bm25_path, "wb") as f:
                dill.dump(bm25, f)
        else:
            with open(self.bm25_path, "rb") as f:
                bm25 = dill.load(f)
        if not os.path.exists(self.faiss_path):
            faiss = self.build_faiss(docs, embeddings)
        else:
            t0 = time.time()
            faiss = FAISS.load_local(self.faiss_path, embeddings, allow_dangerous_deserialization=True)
            print(f"[FAISS] Loaded in {time.time() - t0:.2f}s")

        faiss_retriever = faiss.as_retriever(search_type="mmr", search_kwargs={'k': 6})
        hybrid_retriever = HybridRetriever(bm25, faiss_retriever)

        return hybrid_retriever, chunks_by_source

    def _load_embeddings(self, cache_path: str, docs: list[Document]) -> list[tuple[str, list[float]]]:
        texts = [doc.page_content for doc in docs]
        vectors = []

        with open(cache_path, "rb") as f:
            while True:
                try:
                    batch = dill.load(f)
                    vectors.extend(batch)
                except EOFError:
                    break

        return list(zip(texts, vectors))

    def _generate_embeddings(self, model, cache_path: str, docs: list[Document]) -> list[tuple[str, list[float]]]:
        texts = [doc.page_content for doc in docs]
        batch_size = 32
        chunk_size = 5000
        embeddings = []
        
        with tqdm(total=len(texts), desc="Generating embeddings") as pbar:
            # Process and cache in chunks
            with open(cache_path, "wb") as cache_file:
                for i in range(0, len(texts), chunk_size):
                    chunk_texts = texts[i:i + chunk_size]
                    chunk_embeddings = []
                    
                    try:
                        batch_vectors = model.encode(
                            chunk_texts,
                            batch_size=batch_size,
                            show_progress_bar=False,
                            convert_to_numpy=True,
                            normalize_embeddings=True
                        )
                        # Convert to list immediately to save memory
                        batch_vectors = [v.tolist() for v in batch_vectors]
                        chunk_embeddings.extend(batch_vectors)
                        
                        pbar.update(len(chunk_texts))
                        
                    except RuntimeError as e:
                        if "CUDA out of memory" in str(e):
                            print(f"[WARN] CUDA OOM, reducing batch size")
                            batch_size = max(1, batch_size // 2)
                            continue
                        raise
                    
                    dill.dump(chunk_embeddings, cache_file)
                    embeddings.extend(list(zip(chunk_texts, chunk_embeddings)))
                    del chunk_embeddings
                    gc.collect()
        
        return embeddings