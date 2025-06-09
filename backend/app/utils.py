# Standard library imports
from pathlib import Path
from io import BytesIO

# Third-party imports
import torch
from pydantic import BaseModel
from sentence_transformers import CrossEncoder, SentenceTransformer

# Local imports
from .llm_utils import get_llm_engine

FileType = Path | tuple[str, BytesIO]

# Data models
class Message(BaseModel):
    role: str
    content: str

class QueryInput(BaseModel):
    query: str
    history: list[Message] = []
    use_web_search: bool

class Configuration(BaseModel):
    temperature: float
    model: str
    llm_rerank: bool
    tone: str

class Prompt(BaseModel):
    prompt: str
    
class RetrievalToolKit:
    @staticmethod
    def load_bge_large_fp16():
        model_name = "BAAI/bge-large-en-v1.5"
        print("[Embeddings] Loaded BGE embeddings")
        if torch.cuda.is_available():
            model = SentenceTransformer(model_name, device="cuda")
            model = model.half()
        else:
            model = SentenceTransformer(model_name, device="cpu")
        return lambda x, **kwargs: model.encode(x, **kwargs) if isinstance(x, list) else model.encode([x], **kwargs)[0]