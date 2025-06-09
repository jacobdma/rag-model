# Standard library imports
import json
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

# Library specific imports
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentChunker:    
    def _chunk_one(self, args) -> Document:
        filename, text, chunk_size, chunk_overlap = args
        if not hasattr(self, "_splitter_cache"):
            self._splitter_cache = {}
        splitter_key = (chunk_size, chunk_overlap)
        if splitter_key not in self._splitter_cache:
            self._splitter_cache[splitter_key] = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        splitter = self._splitter_cache[splitter_key]

        chunks = splitter.split_text(text)
        return [
            Document(
                page_content=chunk,
                metadata={
                    "source": filename,
                    "chunk_id": i,
                    "chunk_size": len(chunk),
                    "doc_type": filename.split('.')[-1] if '.' in filename else "unknown"
                }
            )
            for i, chunk in enumerate(chunks)
        ]

    # Runs document chunking in parallel for faster processing
    def _chunk_documents(self, raw_documents, granularity, chunk_size, chunk_overlap) -> list[str]:
        docs = [(filename, text, chunk_size, chunk_overlap) for filename, text in raw_documents]
     
        results = []
        with ProcessPoolExecutor() as executor:
            futures = [executor.submit(self._chunk_one, doc) for doc in docs]
            for future in tqdm(futures, desc=f"Chunking documents with {granularity} granularity"):
                results.extend(future.result())
        
        serializable_docs = [{"page_content": d.page_content, "metadata": d.metadata} for d in results]

        cache_dir = os.getenv("CACHE_DIR", "docs")
        cache_path = Path(cache_dir) / f"chunked_docs_{granularity}.json"
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(serializable_docs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[WARN] Failed to cache parsed docs: {e}")
            
        return results