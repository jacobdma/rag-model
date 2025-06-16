# Standard library imports
import time
import yaml

# Library-specific imports
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import LDAPBindError
from jose import jwt
from pydantic import BaseModel

# Local imports
from .rag import RAGPipeline
from .config import ModelConfig
from .llm_utils import get_llm_engine

# Open and read config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# App initialization
app = FastAPI()
pipeline = RAGPipeline()

ldap = config.get("ldap", {})
SECRET_KEY = config.get("secret_key", "your-secret-key")
server = Server(ldap["server"], get_info=ALL)

def authenticate_user(username: str, password: str) -> str:
    conn = Connection(server, user=ldap["user"], password=ldap["password"], auto_bind=True)
    search_filter = ldap["search_filter"].format(username=username)
    conn.search(ldap["base_dn"], search_filter, attributes=["distinguishedName"])

    if conn.entries:
        return conn.entries[0].entry_dn
    return None

def create_jwt_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

pipeline._get_retrievers()
get_llm_engine()._load_model(ModelConfig.MODEL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Data models
class LoginData(BaseModel):
    username: str
    password: str

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
        content={"detail": exc.errors(), "body": exc.body}
    )

# Endpoints

@app.post("/login")
def login(data: LoginData):
    user_dn = authenticate_user(data.username, data.password)
    if not user_dn:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    try:
        conn = Connection(server, user=user_dn, password=data.password, auto_bind=True)
    except LDAPBindError:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_jwt_token(user_id=data.username)
    return {"access_token": token}

CURRENT_CONFIG = {}
@app.post("/set-config")
async def set_config(config: Configuration):
    CURRENT_CONFIG.update(config.dict())
    return {"message": "Config updated", "config": CURRENT_CONFIG}

@app.post("/chat")
async def stream_query(input: QueryInput):
    def token_generator():
        yield from pipeline.stream_generate(
            input.query,
            input.history,
            input.use_web_search,
            input.use_double_retrievers
        )
    return StreamingResponse(token_generator(), media_type="text/plain")