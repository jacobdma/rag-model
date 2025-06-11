# Standard library imports
import json
import re
from concurrent.futures import ProcessPoolExecutor

# Library specific imports
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Local imports
from .load_utils import CACHE_DIR, DocumentLoader

class DocumentChunker:
    def __init__(self, folder_paths: list[str] = None):
        self._splitter_cache = {}
        self.folder_paths = folder_paths
        self.loader = DocumentLoader()

    def clean_paragraphs(self, docs: list[str], chunk_size: int, chunk_overlap: int, min_length: int = 50) -> list[str]:
        cleaned_chunks = []

        if not hasattr(self, "_splitter_cache"):
            self._splitter_cache = {}
        splitter_key = (chunk_size, chunk_overlap)
        if splitter_key not in self._splitter_cache:
            self._splitter_cache[splitter_key] = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        splitter = self._splitter_cache[splitter_key]

        for doc in docs:
            split_chunks = splitter.split_text(doc)
            doc = re.sub(r"\s+", " ", doc).strip()
            for chunk in split_chunks:
                chunk = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", "", chunk)  # timestamps
                chunk = re.sub(r"[A-Z]{2,}\s?[0-9]{3,}", "", chunk)      # serial-like
                chunk = re.sub(r"[^A-Za-z0-9.,;:(){}\[\]\-+/=_% ]+", " ", chunk)  # remove symbols
                chunk = re.sub(r"\s+", " ", chunk).strip()               # collapse whitespace

                if len(chunk) == 0 or (sum(c.isdigit() for c in chunk) / len(chunk)) > 0.5: # filters logs, heavy tables
                    continue
                if len(chunk) >= min_length:
                    cleaned_chunks.append(chunk)

                unique_tokens = set(chunk.split())
                if len(unique_tokens) < 5:  # tune this — 5 is a good start
                    continue
        return cleaned_chunks

    def _chunk_one(self, args) -> Document:
        filename, text, chunk_size, chunk_overlap = args
        chunks = self.clean_paragraphs([text], chunk_size, chunk_overlap, min_length=chunk_size // 10)  # optional: you can tune min_length
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
    def _get_chunks(self, granularity: int, chunk_size: int, chunk_overlap: int):
        cache_path = CACHE_DIR / f"chunked_docs_{granularity}.json"
        loaded_chunked_docs = False
        if cache_path.exists():
            print(f"[CACHE] Loaded chunked documents from {cache_path}")
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    docs = [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in json.load(f)]
                loaded_chunked_docs = True
            except:
                print(f"[ERROR] Chunked docs could not be loaded. Re-chunking...")

        if not loaded_chunked_docs:
            parsed_cache_path = CACHE_DIR / "parsed_text_docs.json"
            if parsed_cache_path.exists():
                print(f"[CACHE] Loaded pre-parsed documents from {parsed_cache_path}")
                with open(parsed_cache_path, "r", encoding="utf-8") as f:
                    raw_documents = [(entry["filename"], entry["text"]) for entry in json.load(f)]
            else:
                all_files = []
                for folder in self.folder_paths:
                    all_files.extend(self.loader.gather_supported_files(folder))

                print(f"[DEBUG] Found {len(all_files)} total files to parse.")
                raw_documents = self.convert_files_to_text(all_files, verbose_label="all folders")
            if not raw_documents:
                raise ValueError("No documents were loaded. Cannot create indexes.")
            documents = [(filename, text, chunk_size, chunk_overlap) for filename, text in raw_documents]
    
            results = []
            with ProcessPoolExecutor() as executor:
                futures = [executor.submit(self._chunk_one, doc) for doc in documents]
                for future in tqdm(futures, desc=f"Chunking documents with {granularity} granularity"):
                    results.extend(future.result())
            
            serializable_docs = [{"page_content": d.page_content, "metadata": d.metadata} for d in results]

            cache_path = CACHE_DIR / f"chunked_docs_{granularity}.json"
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(serializable_docs, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[WARN] Failed to cache parsed docs: {e}")
        
        return docs