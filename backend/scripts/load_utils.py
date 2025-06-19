# Standard library imports
import os
import dill
import yaml
from pathlib import Path

# Third-party imports
from numpy import ndarray
from tqdm import tqdm
from langchain_core.documents import Document

def get_cache_dir() -> tuple[Path, Path, Path, Path]:
    """
    Finds the project root (by searching for __init__.py), then returns
    (CACHE_DIR, ROOT_DIR, LOG_DIR, INDEX_DIR) as Path objects.
    CACHE_DIR can be overridden by the CACHE_DIR environment variable.
    """
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "__init__.py").exists():
            root_dir = parent
            break
    else:
        raise RuntimeError("Could not find project root (missing __init__.py)")
    cache_dir = Path(os.getenv("CACHE_DIR", root_dir / "cache")).resolve()
    log_dir = root_dir / "logs"
    index_dir = root_dir / "indexes"
    return cache_dir, root_dir, log_dir, index_dir

CACHE_DIR, ROOT_DIR, LOG_DIR, INDEX_DIR = get_cache_dir()

class DocumentLoader:
    def __init__(self):
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        self._RAW_IGNORE_FOLDERS = config["IGNORE_FOLDERS"]
        self._IGNORE_FOLDERS = {f.lower() for f in self._RAW_IGNORE_FOLDERS}
        self._IGNORE_KEYWORDS = set(config["IGNORE_KEYWORDS"])

    # Gathers all file paths from a folder path
    def gather_supported_files(self, folder_path: str) -> list[Path]:
        file_paths = []
        ignore_folders = {str(Path(f)).lower() for f in self._IGNORE_FOLDERS}
        ignore_keywords = {kw.lower() for kw in self._IGNORE_KEYWORDS}

        for root, dirs, files in os.walk(folder_path):
            root_path = Path(root)
            root_str = str(root_path).lower()
            if any(root_str.startswith(f) for f in ignore_folders):
                continue
            dirs[:] = [d for d in dirs if not any(kw in d.lower() for kw in ignore_keywords)] # Filter out ignored keywords
            for name in files:
                if any(kw in name.lower() for kw in ignore_keywords): # Skip files with ignored keywords
                    continue
                file_paths.append(root_path / name)
        return file_paths

    @staticmethod
    def load_embeddings(granularity: str, embeddings, docs: list[Document]) -> list[tuple[str, ndarray]]:
        """
        Embeds docs (list of str), caches and loads vectors for FAISS.
        Returns list of (doc, vector) pairs in original order.
        """
        faiss_cache_path = CACHE_DIR / f"faiss_cache_{granularity}.pkl"
        if faiss_cache_path.exists():
            texts = [doc.page_content for doc in docs]
            print("[CACHE] Loading FAISS vectors from cache...")
            with open(faiss_cache_path, "rb") as f:
                vectors = dill.load(f)
            return list(zip(texts, vectors))

        # Deduplicate while preserving order
        unique_texts = []
        text_to_metadata = {}
        for doc in docs:
            text = doc.page_content
            if text not in text_to_metadata:
                unique_texts.append(text)
                text_to_metadata[text] = doc.metadata
        chunk_size = 100000
        batch_size = 1024
        embedded = {}

        with tqdm(total=len(unique_texts), desc="Embedding unique texts") as pbar:
            for i in range(0, len(unique_texts), chunk_size):
                batch = unique_texts[i:i + chunk_size]
                try:
                    batch_vectors = embeddings(batch, batch_size=batch_size, show_progress_bar=False)
                    embedded.update(zip(batch, batch_vectors))
                    pbar.update(len(batch))
                except RuntimeError as e:
                    if "CUDA out of memory" in str(e):
                        print(f"[WARN] CUDA OOM at batch_size={batch_size}, retrying with half size")
                        batch_size //= 2
                        continue
                    raise

        # Reconstruct full list of vectors in original order
        vectors = [embedded[doc.page_content] for doc in docs]
        with open(faiss_cache_path, "wb") as f:
            dill.dump(vectors, f, protocol=dill.HIGHEST_PROTOCOL)

        texts = [doc.page_content for doc in docs]

        return list(zip(texts, vectors))