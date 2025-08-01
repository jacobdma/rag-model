# Standard library imports
import os
import yaml
from pathlib import Path

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

    def gather_supported_files(self, folder_path: str) -> list[Path]:
        """
        Gathers all file paths from a specific folder path
        """
        file_paths = []
        ignore_folders = {str(Path(f)).lower() for f in self._IGNORE_FOLDERS}
        ignore_keywords = {kw.lower() for kw in self._IGNORE_KEYWORDS}

        for root, dirs, files in os.walk(folder_path):
            root_path = Path(root)
            root_str = str(root_path).lower()
            if any(root_str.startswith(f) for f in ignore_folders):
                continue
            dirs[:] = [d for d in dirs if not any(kw in d.lower() for kw in ignore_keywords)]
            for name in files:
                if any(kw in name.lower() for kw in ignore_keywords):
                    continue
                file_paths.append(root_path / name)
        return file_paths