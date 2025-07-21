# Standard library imports
import json
import re
import os
import logging
import json
from collections import defaultdict
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import ProcessPoolExecutor

# Library specific imports
from tqdm import tqdm
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Local imports
from .load_utils import CACHE_DIR, DocumentLoader
from .file_readers import FileReader

class DocumentChunker:
    def __init__(self, folder_paths: list[str] = []):
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

    def clean_paragraphs(
        self, docs: list[str] | list[Document], chunk_size: int, chunk_overlap: int, granularity = None, min_length: int = 50,
        source: str = ""
    ) -> list[Document]:
        cleaned_chunks = []
        splitter_key = (chunk_size, chunk_overlap)
        if splitter_key not in self._splitter_cache:
            self._splitter_cache[splitter_key] = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        splitter = self._splitter_cache[splitter_key]
        source = os.path.normpath(source)

        for doc in docs:
            if isinstance(doc, Document):
                split_chunks = splitter.split_text(doc.page_content)
            elif isinstance(doc, str):
                split_chunks = splitter.split_text(doc)
            else:
                continue

            chunk_number = 0
            for chunk in split_chunks:
                chunk = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", "", chunk)  # timestamps
                chunk = re.sub(r"[A-Z]{2,}\s?[0-9]{3,}", "", chunk)      # serial-like
                chunk = re.sub(r"[^A-Za-z0-9.,;:(){}\[\]\-+/=_% ]+", " ", chunk)  # remove symbols
                chunk = re.sub(r"\s+", " ", chunk).strip()               # collapse whitespace

                if len(chunk) == 0 or (sum(c.isdigit() for c in chunk) / len(chunk)) > 0.5: # filters logs, heavy tables
                    continue
                if len(chunk) >= min_length:
                    metadata = {
                        "chunk_number": chunk_number,
                        "source": source,
                    }
                    if granularity:
                        metadata["granularity"] = granularity
                    doc = Document(page_content=chunk, metadata=metadata)
                    cleaned_chunks.append(doc)
                    chunk_number += 1

                unique_tokens = set(chunk.split())
                if len(unique_tokens) < 5:
                    continue
        return cleaned_chunks
    
    # Runs document chunking in parallel for faster processing
    def get_chunks(self, granularity: str, chunk_size: int, chunk_overlap: int):
        cache_path = CACHE_DIR / f"chunked_docs_{granularity}.json"
        parsed_cache_path = CACHE_DIR / "parsed_text_docs.json"

        # 1. Try to load chunked docs from cache
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    loaded_by_source = json.load(f)
                    chunks_by_source = {
                        source: [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in doc_list]
                        for source, doc_list in loaded_by_source.items()
                    }
                    return chunks_by_source
            except Exception as e:
                print(f"[ERROR] Chunked docs could not be loaded. Re-chunking... Exception: {e}")

        # 2. Load or parse raw documents
        raw_documents = []
        if parsed_cache_path.exists():
            print(f"[CACHE] Loaded pre-parsed documents from {parsed_cache_path}")
            with open(parsed_cache_path, "r", encoding="utf-8") as f:
                raw_documents = json.load(f)
        else:
            all_files = []
            for folder in self.folder_paths:
                all_files.extend(self.loader.gather_supported_files(folder))
            print(f"[DEBUG] Found {len(all_files)} total files to parse.")
            with tqdm(total=len(all_files), desc="Parsing documents", unit="file") as pbar, \
                 ThreadPoolExecutor(max_workers=32) as executor:
                futures = {executor.submit(FileReader(self._supported_exts, self._skip_files).read_docs, f): f for f in all_files}
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result is None:
                            continue
                        text, filename = result
                        if filename is not None:
                            filename = os.path.normpath(filename)
                        raw_documents.append((text, filename))
                    except Exception as e:
                        logging.exception(f"[Thread Error] {e}")
                    pbar.update(1)
            print(f"[DEBUG] ← Total successfully loaded documents: {len(raw_documents)}")
            try:
                parsed_cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(parsed_cache_path, "w", encoding="utf-8") as f:
                    json.dump(raw_documents, f, ensure_ascii=False)
            except Exception as e:
                print(f"[WARN] Failed to cache parsed docs: {e}")

        if not raw_documents:
            raise ValueError("No documents were loaded. Cannot create indexes.")

        # 3. Chunk and clean in parallel
        results = []
        with ProcessPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(self.clean_paragraphs, [text], chunk_size=chunk_size, chunk_overlap=chunk_overlap, granularity=granularity, min_length=(chunk_size // 10), source=filename)
                for text, filename in raw_documents
            ]
            for future in tqdm(as_completed(futures), total=len(raw_documents), desc=f"Chunking documents with {granularity} granularity"):
                try:
                    results.extend(future.result())
                except Exception as e:
                    print(f"[WARN] Chunking failed for a document: {e}")

        # 4. Sort by source
        chunks_by_source = defaultdict(list)
        for doc in results:
            source = doc.metadata.get("source", "unknown")

            chunks_by_source[source].append(doc)

        for chunk_list in chunks_by_source.values():
            chunk_list.sort(key=lambda d: d.metadata.get("chunk_number", 0))

        # 5. Cache chunked docs by source
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(
                {
                    source: [
                        {"page_content": doc.page_content, "metadata": doc.metadata}
                        for doc in chunk_list
                    ]
                    for source, chunk_list in chunks_by_source.items()
                },
                f,  
                indent=2,
                ensure_ascii=False,
            )
        except Exception as e:
            print(f"[WARN] Failed to cache parsed docs: {e}")

        return chunks_by_source