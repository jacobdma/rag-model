# Standard imports
import threading
import time
from io import BytesIO, StringIO
from pathlib import Path

# Third-party imports
import docx2txt
import fitz
import pandas as pd
from pptx import Presentation

_pdf_lock = threading.Lock()

def log_problem(reason, filename, duration=None, notes=""):
    script_dir = Path(__file__).resolve().parent
    log_path = script_dir / "logs" / "problem_files.tsv"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    duration_str = f"{duration:.2f}" if duration else ""
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"{reason}\t{filename}\t{duration_str}\t{notes}\n")

def read_docx(f):
    if isinstance(f, Path):
        text = docx2txt.process(str(f))
    else:
        text = docx2txt.process(BytesIO(f))
    return text

def read_pptx(f):
    if isinstance(f, (bytes, bytearray)):
        f = BytesIO(f)
    presentation = Presentation(f)
    text_lines = [
        paragraph.text
        for slide in presentation.slides
        for shape in slide.shapes
        if getattr(shape, "has_text_frame", False)
        for text_frame in [getattr(shape, "text_frame", None)]
        if text_frame is not None
        for paragraph in text_frame.paragraphs
    ]
    return "\n".join(text_lines).strip()

def read_txt(f):
    if isinstance(f, (bytes, bytearray)):
        return f.decode("utf-8", errors="ignore")
    return f.read().decode("utf-8", errors="ignore")

def read_pdf(f, filename):
    start_pdf = time.time()
    if hasattr(f, "seek"):
        f.seek(0)
    with _pdf_lock:
        with fitz.open(stream=f.read(), filetype="pdf") as doc:
            text_parts = [page.get_text() for page in doc]  # type: ignore
    if time.time() - start_pdf > 900:
        log_problem("STALLED_LOAD", filename, time.time() - start_pdf)
    return "\n".join(text_parts)

def read_csv(f):
    try:
        if isinstance(f, (bytes, bytearray)):
            f = StringIO(f.decode("utf-8"))
        return pd.read_csv(f).to_string(index=False)
    except Exception:
        f.seek(0)
        return pd.read_csv(f, encoding="latin1").to_string(index=False)

class FileReader:
    def __init__(self, _supported_exts, _skip_files):
        self._supported_exts = _supported_exts
        self._skip_files = _skip_files
        
    def read_docs(self, file: Path):
        readers = {
            ".docx": read_docx,
            ".pptx": read_pptx,
            ".txt": read_txt,
            ".pdf": lambda b: read_pdf(BytesIO(b), filename),
            ".csv": read_csv,
        }
        filename = str(file)
        ext = file.suffix.lower()
        if filename in self._skip_files or ext not in self._supported_exts:
            return None
        with open(file, "rb") as f:
            file_bytes = f.read()
        reader = readers.get(ext)
        return reader(file_bytes), filename if reader else None