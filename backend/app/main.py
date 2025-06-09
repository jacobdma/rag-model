# Library-specific imports
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
# Local imports
from .rag import RAGPipeline
from .config import ModelConfig
from .utils import QueryInput, Configuration
from .llm_utils import get_llm_engine

# App initialization
app = FastAPI()
pipeline = RAGPipeline()

get_llm_engine()._load_model(ModelConfig.MODEL)
pipeline._get_retrievers()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
@app.post("/query") 
async def ask(input: QueryInput):
    response = pipeline.generate(input.query, input.history, input.use_web_search)
    return {"response": response}

CURRENT_CONFIG = {}
@app.post("/set-config")
async def set_config(config: Configuration):
    ModelConfig.TEMPERATURE = config.temperature
    ModelConfig.MODEL = config.model
    ModelConfig.TONE = config.tone
    ModelConfig.LLM_RERANKING = config.llmRerank
    CURRENT_CONFIG.update({
        "temperature": config.temperature,
        "model": config.model,
        "tone": config.tone,
        "llmRerank": config.llmRerank,
    })
    return {"message": "Config updated", "config": CURRENT_CONFIG}