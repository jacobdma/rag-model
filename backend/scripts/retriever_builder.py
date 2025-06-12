# Standard library imports
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Library specific imports
import dill
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.retrievers import BM25Retriever

# Local imports
from .chunk_documents import DocumentChunker
from .llm_utils import LLMEngine
from .load_utils import DocumentLoader

class RetrieverBuilder:
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
        missing_bm25 = {g for g, path in self.bm25_paths.items() if not os.path.exists(path)}
        missing_faiss = {g for g, path in self.faiss_paths.items() if not os.path.exists(path)}
        return missing_bm25, missing_faiss

    def build_faiss(self, docs, path, embeddings, granularity):
        text_embeddings = DocumentLoader()._load_embeddings(granularity, embeddings, docs)
        faiss_store = FAISS.from_embeddings(text_embeddings, embedding=embeddings)
        faiss_store.save_local(path)

    def _faiss_load(self, path, granularity):
        t0 = time.time()
        embeddings = LLMEngine.load_bge_large_fp16()
        index = FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
        print(f"[FAISS] Loaded '{granularity}' in {time.time() - t0:.2f}s")
        return ('faiss', granularity, index)

    def build_bm25(self, docs, path):
        bm25 = BM25Retriever.from_texts(docs)
        with open(path, "wb") as f:
            dill.dump(bm25, f)

    def _bm25_load(self, path, granularity):
        t0 = time.time()
        with open(path, "rb") as f:
            result = dill.load(f)
        print(f"[BM25] Loaded '{granularity}' in {time.time() - t0:.2f}s")
        return ('bm25', granularity, result)

    def build_retrievers(self) -> tuple[dict[str, BM25Retriever], dict[str, FAISS]]:
        """Load or build BM25 and FAISS retrievers, caching FAISS in memory."""
        missing_bm25, missing_faiss = self._get_missing_retrievers()

        # Build missing retrievers
        for granularity in self.GRANULARITIES:
            if granularity in missing_bm25 or granularity in missing_faiss:
                chunk_size, chunk_overlap = self.GRANULARITIES[granularity]
                docs = self.chunker._get_chunks(granularity, chunk_size, chunk_overlap)
                if granularity in missing_bm25:
                    self.build_bm25(docs, self.bm25_paths[granularity])
                if granularity in missing_faiss:
                    self.build_faiss(docs, self.faiss_paths[granularity], self.embeddings, granularity)
        if not (missing_bm25 or missing_faiss):
            print("[INFO] All retrievers exist, loading from disk...")

        # Load all retrievers in parallel
        with ThreadPoolExecutor(max_workers=8) as executor:
            bm25_futures = [
                executor.submit(self._bm25_load, path, g)
                for g, path in self.bm25_paths.items()
            ]
            faiss_futures = [
                executor.submit(self._faiss_load, path, g)
                for g, path in self.faiss_paths.items()
            ]
            retrievers_bm25, retrievers_faiss = {}, {}
            for future in as_completed(bm25_futures + faiss_futures):
                result_type, granularity, data = future.result()
                if result_type == 'bm25':
                    retrievers_bm25[granularity] = data
                else:
                    retrievers_faiss[granularity] = data
        return retrievers_bm25, retrievers_faiss