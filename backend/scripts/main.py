# Standard library imports
import time
import uuid
import yaml

# Library-specific imports
from fastapi import FastAPI, Header, HTTPException, Path, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import LDAPBindError
from jose import jwt, JWTError
from pydantic import BaseModel
from pymongo import MongoClient

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

def authenticate_user(username: str, password: str) -> str | None:
    conn = Connection(server, user=ldap["user"], password=ldap["password"], auto_bind=True)
    search_filter = ldap["search_filter"].format(username=username)
    conn.search(ldap["base_dn"], search_filter, attributes=["distinguishedName"])

    if not conn.entries:
        return None

    user_dn = conn.entries[0].entry_dn
    try:
        user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        return user_dn if user_conn.bound else None
    except LDAPBindError:
        return None

def create_jwt_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": int(time.time())
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
    chat_id: str | None = None

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

# Load chats
client = MongoClient(config["mongo_uri"])  # add to config.yaml
db = client["chat_app"]
chats_collection = db["chats"]

def get_username_from_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Endpoints

@app.post("/login")
def login(data: LoginData):
    user_dn = authenticate_user(data.username, data.password)
    if not user_dn:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_jwt_token(user_id=data.username)
    return {
        "access_token": token,
        "username": data.username
    }

CURRENT_CONFIG = {}
@app.post("/set-config")
async def set_config(config: Configuration):
    CURRENT_CONFIG.update(config.dict())
    return {"message": "Config updated", "config": CURRENT_CONFIG}

@app.post("/chat")
async def stream_query(input: QueryInput, authorization: str = Header(...)):
    username = get_username_from_token(authorization.replace("Bearer ", ""))

    # Generate chat_id if not provided
    chat_id = input.chat_id or str(uuid.uuid4())
    user_message = {"role": "user", "content": input.query}
    assistant_reply = ""

    def token_generator():
        nonlocal assistant_reply
        for chunk in pipeline.stream_generate(
            input.query,
            input.history,
            input.use_web_search,
            input.use_double_retrievers
        ):
            assistant_reply += chunk
            yield chunk

        chats_collection.update_one(
            {"_id": chat_id},
            {
                "$setOnInsert": {
                    "_id": chat_id,
                    "username": username,
                    "timestamp": time.time(),
                },
                "$push": {
                    "history": {
                        "$each": [
                            {"role": "user", "content": input.query},
                            {"role": "assistant", "content": assistant_reply}
                        ]
                    }
                }
            },
            upsert=True
        )
    
    return StreamingResponse(token_generator(), media_type="text/plain")

@app.get("/chats")
async def get_chats(authorization: str = Header(...)):
    username = get_username_from_token(authorization.replace("Bearer ", ""))
    chats = list(chats_collection.find({"username": username}))
    for chat in chats:
        chat["_id"] = str(chat["_id"])
    return JSONResponse(content=chats)

@app.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str = Path(...), authorization: str = Header(...)):
    username = get_username_from_token(authorization.replace("Bearer ", ""))
    
    result = chats_collection.delete_one({
        "_id": str(chat_id),
        "username": username
    })
    
    if result.deleted_count == 0:
        print(f"Failed to delete chat {chat_id} for user {username}")
        raise HTTPException(status_code=404, detail="Chat not found")

    return {"message": "Chat deleted"}
