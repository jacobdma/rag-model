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
from .llm_utils import LLMEngine
from .load_utils import IndexDocumentLoader

class RetrieverBuilder:
    def __init__(self, folder_paths: list[str]):
        self.folder_paths = folder_paths
        self.index_dir = os.path.join(os.path.dirname(__file__), "..", "indexes")
        os.makedirs(self.index_dir, exist_ok=True)
        self.embeddings =  LLMEngine.load_bge_large_fp16()
        self.bm25_paths = {
            "small": os.path.join(self.index_dir, "bm25_small.pkl"),
            "large": os.path.join(self.index_dir, "bm25_large.pkl")
        }
        self.faiss_paths = {
            "small": os.path.join(self.index_dir, "faiss_small"),
            "large": os.path.join(self.index_dir, "faiss_large")
        }
        self.loader = IndexDocumentLoader(self.folder_paths)

    def _log_faiss_elapsed(self, start_time, stop_flag):
        while not stop_flag.wait(30):
            elapsed = int(time.time() - start_time)
            sys.stdout.write(f"\r[Indexing FAISS... {elapsed} seconds elapsed]")
            sys.stdout.flush()

    def _get_missing_retrievers(self):
        missing_bm25 = set()
        missing_faiss = set()

        for granularity, path in self.bm25_paths.items():
            if not os.path.exists(path):
                missing_bm25.add(granularity)

        for granularity, path in self.faiss_paths.items():
            if not os.path.exists(path):
                missing_faiss.add(granularity)

        return missing_bm25, missing_faiss

    def build_faiss(self, docs, path, embeddings, granularity):
        faiss_start_time = time.time()
        vectors, texts = self.loader._load_embeddings(granularity, embeddings, docs)

        # Create FAISS index
        faiss_build_start = time.time()
        text_embeddings = list(zip(texts, vectors))
        faiss_store = FAISS.from_embeddings(text_embeddings, embedding=embeddings)
        print(f"FAISS index built in {time.time() - faiss_build_start:.2f}s")
        faiss_store.save_local(path)

        total_time = time.time() - faiss_start_time
        print(f"Total FAISS build time: {total_time:.2f}s")
        return faiss_store
    
    @staticmethod
    def build_bm25(docs, path):
        bm25 = BM25Retriever.from_texts([d.page_content for d in docs])
        with open(path, "wb") as f:
            dill.dump(bm25, f)
        return bm25

    # Stores retrivers as indexes to cut down load time
    def build_retrievers(self) -> tuple[dict[str, BM25Retriever], dict[str, FAISS]]:
        """Load or build BM25 and FAISS retrievers, caching FAISS in memory."""
        missing_bm25, missing_faiss = self._get_missing_retrievers()
        t0 = time.time()

        if missing_bm25 or missing_faiss:
            for granularity, (chunk_size, chunk_overlap) in {"small": (512, 50), "large": (4096, 400)}.items():
                docs = self.loader._get_chunks(granularity, chunk_size, chunk_overlap)
                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = []
                    if granularity in missing_bm25:
                        futures.append(executor.submit(self.build_bm25, docs, self.bm25_paths[granularity]))
                    if granularity in missing_faiss:
                        futures.append(executor.submit(self.build_faiss, docs, self.faiss_paths[granularity], self.embeddings, granularity))
                    [f.result() for f in futures]
        else:
            t0 = time.time()
            print(f"Loading docs took {(time.time() - t0):.2f}s")
            print("[INFO] All retrievers exist, loading from disk...")

        def bm25_load(path, granularity):
            t0 = time.time()
            with open(path, "rb") as f:
                result = dill.load(f)
            print(f"[BM25] Loaded '{granularity}' in {time.time() - t0:.2f}s")
            return ('bm25', granularity, result)
        
        def faiss_load(path, granularity):
            t0 = time.time()
            index = FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization=True)
            print(f"[FAISS] Loaded '{granularity}' in {time.time() - t0:.2f}s")
            return ('faiss', granularity, index)

        with ThreadPoolExecutor(max_workers=8) as executor:
            all_futures = []
            t0 = time.time()
            # Submit all BM25 loads
            for g, path in self.bm25_paths.items():
                future = executor.submit(bm25_load, path, g)
                all_futures.append(future)
            
            # Submit all FAISS loads
            for g, path in self.faiss_paths.items():
                future = executor.submit(faiss_load, path, g)
                all_futures.append(future)
            
            # Collect results as they complete
            retrievers_bm25, retrievers_faiss = {}, {}
            for future in as_completed(all_futures):
                result_type, granularity, data = future.result()
                if result_type == 'bm25':
                    retrievers_bm25[granularity] = data
                else:  # faiss
                    retrievers_faiss[granularity] = data
            print(f"[DEBUG] Loaded all retrievers in {time.time() - t0:.2f}s")
        return retrievers_bm25, retrievers_faiss