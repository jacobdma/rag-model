# Standard library imports
import json
import re
import logging
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import ProcessPoolExecutor

# Library specific imports
from tqdm import tqdm
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Local imports
from .load_utils import CACHE_DIR, DocumentLoader
from .file_readers import FileReader

class DocumentChunker:
    def __init__(self, folder_paths: list[str] = None):
        self._splitter_cache = {}
        self.folder_paths = folder_paths
        self.loader = DocumentLoader()
        self._supported_exts = {".docx", ".pptx", ".txt", ".pdf", ".csv"} # List of supported extensions to filter
        self._skip_files = self._load_empty_file_skiplist()

    @staticmethod
    def _load_empty_file_skiplist(log_path: Path = Path("logs/problem_files.tsv")) -> set:
        if not log_path.exists():
            return set()
    
        skip_files = set()
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 2 and parts[0] == "EMPTY_TEXT":
                    skip_files.add(parts[1])
        return skip_files

    def clean_paragraphs(self, docs: list[str], chunk_size: int, chunk_overlap: int, min_length: int = 50) -> list[str]:
        cleaned_chunks = []
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
    
    # Runs document chunking in parallel for faster processing
    def get_chunks(self, granularity: int, chunk_size: int, chunk_overlap: int):
        cache_path = CACHE_DIR / f"chunked_docs_{granularity}.json"
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ERROR] Chunked docs could not be loaded. Re-chunking... Exception: {e}")

        # Load or parse raw documents
        parsed_cache_path = CACHE_DIR / "parsed_text_docs.json"
        if parsed_cache_path.exists():
            print(f"[CACHE] Loaded pre-parsed documents from {parsed_cache_path}")
            with open(parsed_cache_path, "r", encoding="utf-8") as f:
                raw_documents = json.load(f)
        else:
            all_files = []
            for folder in self.folder_paths:
                all_files.extend(self.loader.gather_supported_files(folder))
            print(f"[DEBUG] Found {len(all_files)} total files to parse.")

            raw_documents = []
            with tqdm(total=len(all_files), desc="Parsing documents", unit="file") as pbar:
                with ThreadPoolExecutor(max_workers=12) as executor:
                    futures = {executor.submit(FileReader(self._supported_exts, self._skip_files).read_file, f): f for f in all_files}
                    for future in as_completed(futures):
                        try:
                            result = future.result()
                        except Exception as e:
                            logging.exception(f"[Thread Error] {e}")
                            continue
                        pbar.update(1)
                        if result:
                            # If result is a tuple (filename, text), take text
                            text = result[1] if isinstance(result, tuple) else result
                            raw_documents.append(text)
            print(f"[DEBUG] ← Total successfully loaded documents: {len(raw_documents)}")
            # Cache parsed docs as list of dicts for compatibility
            try:
                with open(parsed_cache_path, "w", encoding="utf-8") as f:
                    json.dump(raw_documents, f, ensure_ascii=False)
            except Exception as e:
                print(f"[WARN] Failed to cache parsed docs: {e}")

        if not raw_documents:
            raise ValueError("No documents were loaded. Cannot create indexes.")

        # Chunk and clean in parallel
        results = []
        with ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(self.clean_paragraphs, [doc], chunk_size, chunk_overlap, chunk_size // 10)
                for doc in raw_documents
            ]
            for future in tqdm(as_completed(futures), total=len(raw_documents), desc=f"Chunking documents with {granularity} granularity"):
                results.extend(future.result())

        # Cache chunked docs
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[WARN] Failed to cache parsed docs: {e}")
        
        return results