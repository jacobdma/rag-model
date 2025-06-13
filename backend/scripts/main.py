# Standard library imports
import yaml

# Library-specific imports
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse

# Local imports
from .rag import RAGPipeline
from .config import ModelConfig
from .llm_utils import get_llm_engine

from pydantic import BaseModel

# App initialization
app = FastAPI()
pipeline = RAGPipeline()

pipeline._get_retrievers()
get_llm_engine()._load_model(ModelConfig.MODEL)

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

allowed_origins = config.get("cors", {}).get("allowed_origins", [])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class Message(BaseModel):
    role: str
    content: str

class QueryInput(BaseModel):
    query: str
    history: list[Message] = []
    use_web_search: bool
    use_double_retrievers: bool = True

class Configuration(BaseModel):
    temperature: float
    model: str
    tone: str

# Exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": exc.body,
        },
    )

# Endpoints
CURRENT_CONFIG = {}
@app.post("/set-config")
async def set_config(config: Configuration):
    ModelConfig.TEMPERATURE = config.temperature
    ModelConfig.MODEL = config.model
    ModelConfig.TONE = config.tone
    CURRENT_CONFIG.update({
        "temperature": config.temperature,
        "model": config.model,
        "tone": config.tone
    })
    return {"message": "Config updated", "config": CURRENT_CONFIG}

@app.post("/stream-query")
async def stream_query(input: QueryInput):
    def token_generator():
        yield from pipeline.stream_generate(
            input.query,
            input.history,
            input.use_web_search,
            input.use_double_retrievers
        )
    return StreamingResponse(token_generator(), media_type="text/plain")