# Standard library imports
import collections
import logging
import json
import os
import pickle
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Third-party imports
from tqdm import tqdm
from langchain_core.documents import Document

# Local imports
from .file_readers import FileReader
from .chunk_documents import DocumentChunker
from .utils import FileType

class DocumentLoader:
    def __init__(self):
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)

        self._RAW_IGNORE_FOLDERS = config["IGNORE_FOLDERS"]
        self._IGNORE_FOLDERS = {f.lower() for f in self._RAW_IGNORE_FOLDERS}
        self._IGNORE_KEYWORDS = set(config["IGNORE_KEYWORDS"])
        self._supported_exts = {".docx", ".pptx", ".txt", ".pdf", ".csv"} # List of supported extensions to filter
        self._skip_files = self._load_empty_file_skiplist()

    def _load_empty_file_skiplist(self, log_path: Path = Path("logs/problem_files.tsv")) -> set:
        if not log_path.exists():
            return set()
    
        skip_files = set()
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 2 and parts[0] == "EMPTY_TEXT":
                    skip_files.add(parts[1])
        return skip_files

    # Gathers all file paths from a folder path
    def _gather_supported_files(self, folder_path: str) -> list[Path]:
        file_paths = []

        for root, dirs, files in os.walk(folder_path):
            root_path = Path(root)
            if any(str(root_path).lower().startswith(str(Path(f)).lower()) for f in self._IGNORE_FOLDERS):
                continue
            dirs[:] = [
                d for d in dirs
                if not any(kw in d.lower() for kw in self._IGNORE_KEYWORDS)
            ]
            for name in files:
                if any(kw in name.lower() for kw in self._IGNORE_KEYWORDS):
                    continue
                full_path = root_path / name
                file_paths.append(full_path)

        return [f for f in file_paths if f.suffix.lower() in self._supported_exts]

    def convert_files_to_text(self, all_files: list[FileType], verbose_label: str = "documents") -> list[tuple[str, str]]:
        load_times = collections.defaultdict(float)
        load_counts = collections.defaultdict(int)
        text_docs = []

        with tqdm(total=len(all_files), desc=f"Parsing {verbose_label}", unit="file") as pbar:
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
                        filename, text, ext, elapsed = result
                        text_docs.append((filename, text))
                        load_times[ext] += elapsed
                        load_counts[ext] += 1
                        
        for ext in load_times:
            print(f"[Loader] {ext}: {load_counts[ext]} files loaded in {load_times[ext]:.2f} seconds")
        print(f"[DEBUG] ← Total successfully loaded documents: {len(text_docs)}")
        cache_path = Path("docs/parsed_text_docs.json")
        cache_path.parent.mkdir(exist_ok=True)

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump([{"filename": fn, "text": txt} for fn, txt in text_docs], f, ensure_ascii=False)
        except Exception as e:
            print(f"[WARN] Failed to cache parsed docs: {e}")
        return text_docs # Returns a list of file names and extracted text as List[Tuple(str, str)]

    # Loads folders
    def load_folders(self, folder_paths: list[str]) -> list[tuple[str, str]]:
        all_files = []
        for folder in folder_paths:
            all_files.extend(self._gather_supported_files(folder))

        print(f"[DEBUG] Found {len(all_files)} total files to parse.")
        return self.convert_files_to_text(all_files, verbose_label="all folders")

class IndexDocumentLoader:
    def __init__(self, folder_paths: list[str]):
        self.folder_paths = folder_paths

    def _get_chunks(self, granularity: int, chunk_size: int, chunk_overlap: int):
        chunked_cache_path = Path(f"docs/chunked_docs_{granularity}.json")
        loaded_chunked_docs = False
        if chunked_cache_path.exists():
            print(f"[CACHE] Loaded chunked documents from {chunked_cache_path}")
            try:
                with open(chunked_cache_path, "r", encoding="utf-8") as f:
                    docs = [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in json.load(f)]
                loaded_chunked_docs = True
            except:
                print(f"[ERROR] Chunked docs could not be loaded. Re-chunking...")

        if not loaded_chunked_docs:
            raw_docs = self._get_docs()
            docs = DocumentChunker._chunk_documents(raw_docs, granularity, chunk_size, chunk_overlap)
        
        return docs
    
    def _get_docs(self):
        parsed_cache_path = Path("docs/parsed_text_docs.json")
        if parsed_cache_path.exists():
            print(f"[CACHE] Loaded pre-parsed documents from {parsed_cache_path}")
            with open(parsed_cache_path, "r", encoding="utf-8") as f:
                raw_documents = [(entry["filename"], entry["text"]) for entry in json.load(f)]
        else:
            raw_documents = DocumentLoader().load_folders(self.folder_paths)
        if not raw_documents:
            raise ValueError("No documents were loaded. Cannot create indexes.")
        return raw_documents

    @staticmethod
    def _load_embeddings(granularity: str, embeddings, docs):
        if os.path.exists(f"docs/faiss_cache_{granularity}.pkl"):
            print("[CACHE] Loading FAISS vectors from cache...")
            with open(f"docs/faiss_cache_{granularity}.pkl", "rb") as f:
                cache = pickle.load(f)
            vectors = cache["vectors"]
            texts = cache["texts"]
        else:
            texts = [d.page_content for d in docs]
            vectors = []
            unique_texts = list(set(texts))
            chunk_size = 25000
            batch_size= 256
            encoded = {}

            with tqdm(total=len(unique_texts), desc="Embedding unique texts") as pbar:
                for i in range(0, len(unique_texts), chunk_size):
                    batch = unique_texts[i:i + chunk_size]
                    try:
                        batch_vectors = embeddings(batch, batch_size=batch_size, show_progress_bar=False)
                        encoded.update(zip(batch, batch_vectors))
                        pbar.update(len(batch))
                    except RuntimeError as e:
                        if "CUDA out of memory" in str(e) and batch_size > 16:
                            print(f"[WARN] CUDA OOM at batch_size={batch_size}, retrying with half size")
                            batch_size //= 2
                            continue
                        raise

            # Reconstruct full list of vectors in original order
            vectors = [encoded[t] for t in texts]
            with open(f"docs/faiss_cache_{granularity}.pkl", "wb") as f:
                pickle.dump({
                    "vectors": vectors,
                    "texts": list(set(texts)),
                    "metadatas": None
                }, f, protocol=pickle.HIGHEST_PROTOCOL)

        return vectors, texts