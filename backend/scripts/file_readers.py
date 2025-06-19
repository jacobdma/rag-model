# Standard imports
import threading
import time
from io import BytesIO
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
        return docx2txt.process(str(f))
    else:
        return docx2txt.process(BytesIO(f.read()))

def read_pptx(f):
    presentation = Presentation(f)
    text_lines = [
        paragraph.text
        for slide in presentation.slides
        for shape in slide.shapes
        if shape.has_text_frame
        for paragraph in shape.text_frame.paragraphs
    ]
    return "\n".join(text_lines).strip()

def read_txt(f):
    return f.read().decode("utf-8", errors="ignore")

def read_pdf(f, filename):
    start_pdf = time.time()
    f.seek(0)
    with _pdf_lock:
        with fitz.open(stream=f.read(), filetype="pdf") as doc:
            text_parts = [page.get_text() for page in doc]
    if time.time() - start_pdf > 900:
        log_problem("STALLED_LOAD", filename, time.time() - start_pdf)
    return "\n".join(text_parts)

def read_csv(f):
    try:
        df = pd.read_csv(f, encoding="utf-8")
    except Exception:
        f.seek(0)
        df = pd.read_csv(f, encoding="latin1")
    return df.to_string(index=False)

class FileReader:
    def __init__(self, _supported_exts, _skip_files):
        self._supported_exts = _supported_exts
        self._skip_files = _skip_files

    def read_file(self, file: Path) -> str | None:
        filename = str(file)
        ext = file.suffix.lower()
        if filename in self._skip_files or ext not in self._supported_exts:
            return None
        with open(file, "rb") as f:
            text = self.read_docs(f, filename, ext)

        return text, filename

    def read_docs(self, f, filename, ext):
        readers = {
            ".docx": read_docx,
            ".pptx": read_pptx,
            ".txt": read_txt,
            ".pdf": lambda f: read_pdf(f, filename),
            ".csv": read_csv,
        }
        reader = readers.get(ext)
        return reader(f) if reader else None