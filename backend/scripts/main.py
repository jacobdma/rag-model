# Standard library imports
import json
import os
import pathlib
import tempfile
import time
import uuid
import yaml
from datetime import datetime

# Library-specific imports
from fastapi import FastAPI, Header, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import LDAPBindError
from jose import jwt, JWTError
from pymongo import MongoClient
from pydantic import BaseModel
from exchangelib import Credentials, Account, Configuration as ExchangeConfig, DELEGATE

# Local imports
from .rag import RAGPipeline, Message
from .config import ModelConfig
from .llm_utils import get_llm_engine
from .file_readers import FileReader
from .utils import LoginData, QueryInput, Configuration, UploadedDocument

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

CHAT_DOCUMENTS = {}

# Exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    raw_body = await request.body()
    print(f"Validation failed for body: {raw_body.decode()}")
    print(f"Validation error details: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": json.loads(raw_body.decode())
        }
    )

# Load chats
client = MongoClient(config["mongo_uri"])
db = client["chat_app"]
chats_collection = db["chats"]

def get_username_from_token(token: str) -> str:
    token = token.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return sub
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Email Sync Models
class EmailSyncRequest(BaseModel):
    username: str
    password: str
    email_address: str
    server: str
    user_id: str

class EmailSyncResponse(BaseModel):
    status: str
    message: str
    emails_synced: int
    total_emails: int

def get_last_sync_date(existing_emails: dict) -> datetime | None:
    if not existing_emails:
        return None

    dates = []
    for email_data in existing_emails.values():
        if 'datetime_recieved' in email_data:
            try:
                date = datetime.fromisoformat(email_data['datetime_received'].replace('Z', '+00:00'))
                dates.append(date)
            except:
                continue

    return max(dates) if dates else None

# Endpoints
@app.post("/login")
def login(data: LoginData):
    user_dn = authenticate_user(data.username, data.password)
    if not user_dn:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_jwt_token(user_id=data.username)
    return {
        "access_token": token,
        "username": data.username,
        "password": data.password
    }

CURRENT_CONFIG = {}
@app.post("/set-config")
async def set_config(config: Configuration):
    CURRENT_CONFIG.update(config.dict())
    return {"message": "Config updated", "config": CURRENT_CONFIG}

@app.post("/chat")
async def stream_query(
    input: QueryInput, 
    request: Request, 
    authorization: str | None = Header(default=None)
):
    if authorization:
        try:
            username = get_username_from_token(authorization.replace("Bearer ", ""))
        except Exception as e:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        username = "guest"
    
    chat_id = input.chat_id or str(uuid.uuid4())
    assistant_reply = ""

    async def token_generator():
        nonlocal assistant_reply
        generator = pipeline.generate(
            input.query,
            input.history,
            input.use_web_search,
            input.use_double_retrievers,
            chat_id=chat_id
        )
        first_yield = next(generator)
        if isinstance(first_yield, list):
            # Send the full group structure, not a flattened list
            context_str = f"[CONTEXT START]{json.dumps(first_yield)}[CONTEXT END]"
            yield context_str
        else:  # String token
            yield first_yield
        for chunk in generator:
            if await request.is_disconnected():
                break
            assistant_reply += str(chunk)
            yield chunk

        # Only save if not interrupted
        if not await request.is_disconnected():
            existing_chat = chats_collection.find_one({"_id": chat_id})
            print("Saving chat history...")
            if existing_chat is not None and len(input.history) < len(existing_chat.get("history", [])):
                print("Editing...")
                chats_collection.update_one(
                    {"_id": chat_id},
                    {
                        "$set": {
                            "history": [msg.dict() if hasattr(msg, 'dict') else {'role': msg.role, 'content': msg.content} for msg in input.history] + [
                                {"role": "user", "content": input.query},
                                {"role": "assistant", "content": assistant_reply}
                            ]
                        }
                    }
                )
            else:

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
        else:
            print("Request disconnected, not saving chat history.")

    async def string_generator():
        async for item in token_generator():
            yield str(item)
    
    return StreamingResponse(string_generator(), media_type="text/plain")

@app.get("/chats")
async def get_chats(authorization: str = Header(...)):
    username = get_username_from_token(authorization)
    chats = list(chats_collection.find({"username": username}))
    for chat in chats:
        chat["_id"] = str(chat["_id"])
    return JSONResponse(content=chats)

@app.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str, authorization: str = Header(...)):
    username = get_username_from_token(authorization)
    
    result = chats_collection.delete_one({
        "_id": str(chat_id),
        "username": username
    })
    
    if result.deleted_count == 0:
        print(f"Failed to delete chat {chat_id} for user {username}")
        raise HTTPException(status_code=404, detail="Chat not found")

    return {"message": "Chat deleted"}

@app.post("/upload-files/{chat_id}")
async def upload_files(
    chat_id: str,
    files: list[UploadFile] = File(),
):
    if chat_id not in CHAT_DOCUMENTS:
        CHAT_DOCUMENTS[chat_id] = []
    
    supported_extensions = {".docx", ".pptx", ".txt", ".pdf", ".csv"}
    processed_files = []
    
    for file in files:
        try:
            # Check file extension
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in supported_extensions:
                processed_files.append({
                    "filename": file.filename,
                    "status": "error",    
                    "message": f"Unsupported file type: {file_ext}"
                })
                continue
            
            file_content = await file.read()
            reader = FileReader(supported_extensions)
            
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file.flush()
                temp_path = pathlib.Path(temp_file.name)
            
            try:
                result = reader.read_docs(temp_path)
                if result is None:
                    processed_files.append({
                        "filename": file.filename,
                        "status": "error", 
                        "message": "Failed to process file"
                    })
                    continue

                text_content, _ = result
                if not text_content or len(text_content.strip()) < 10:
                    processed_files.append({
                        "filename": file.filename,
                        "status": "error",
                        "message": "File appears to be empty or unreadable"
                    })
                    continue
                
                doc = UploadedDocument(
                    filename=file.filename,
                    content=text_content,
                    file_type=file_ext
                )
                
                CHAT_DOCUMENTS[chat_id].append(doc)
                
                processed_files.append({
                    "filename": file.filename,
                    "status": "success",
                    "message": "File processed successfully"
                })
                
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            processed_files.append({
                "filename": file.filename,
                "status": "error",
                "message": f"A processing error occurred: {str(e)}"
            })
    
    return {
        "chat_id": chat_id,
        "processed_files": processed_files,
        "total_documents": len(CHAT_DOCUMENTS[chat_id])
    }

@app.get("/chat-documents/{chat_id}")
async def get_chat_documents(chat_id: str):
    """Get uploaded documents for a specific chat"""
    documents = CHAT_DOCUMENTS.get(chat_id, [])
    return {
        "chat_id": chat_id,
        "documents": [
            {
                "filename": doc.filename,
                "file_type": doc.file_type,
                "size": len(doc.content)
            }
            for doc in documents
        ]
    }

@app.delete("/chat-documents/{chat_id}/{filename}")
async def delete_chat_document(chat_id: str, filename: str):
    """Delete a specific document from a chat"""
    if chat_id not in CHAT_DOCUMENTS:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    documents = CHAT_DOCUMENTS[chat_id]
    for i, doc in enumerate(documents):
        if doc.filename == filename:
            del documents[i]
            return {"message": f"Document {filename} deleted"}
    
    raise HTTPException(status_code=404, detail="Document not found")

# Email Sync Endpoints

@app.post("/sync-emails", response_model=EmailSyncResponse)
async def sync_emails(request: EmailSyncRequest):
    """Sync emails from Exchange server to MongoDB per user"""
    try:
        credentials = Credentials(username=request.username, password=request.password)
        exchange_config = ExchangeConfig(
            server=request.server,
            credentials=credentials
        )
        account = Account(
            primary_smtp_address=request.email_address,
            config=exchange_config,
            autodiscover=False,
            access_type=DELEGATE
        )

        # Load existing emails from MongoDB
        user_emails_doc = db["emails"].find_one({"user_id": request.user_id})
        existing_emails = user_emails_doc["emails"] if user_emails_doc and "emails" in user_emails_doc else {}
        last_sync_date = get_last_sync_date(existing_emails)

        batch_size = 100
        query = account.inbox.all().order_by("-datetime_received")

        if last_sync_date:
            query = account.inbox.filter(datetime_received_gt=last_sync_date).order_by("-datetime_received")

        emails_to_process = list(query[:batch_size])
        total_emails = len(emails_to_process)

        if total_emails == 0:
            # Save (or update) the doc in MongoDB even if no new emails
            db["emails"].update_one(
                {"user_id": request.user_id},
                {"$set": {"emails": existing_emails}},
                upsert=True
            )
            return EmailSyncResponse(
                status="success",
                message="No new emails to sync",
                emails_synced=0,
                total_emails=len(existing_emails)
            )

        emails_synced = 0

        for item in emails_to_process:
            try:
                email_id = str(item.message_id) if hasattr(item, 'message_id') and item.message_id else f"{item.subject}_{item.datetime_received.isoformat()}"

                if email_id in existing_emails:
                    continue

                email_data = {
                    "id": email_id,
                    "subject": str(item.subject) if item.subject else "No Subject",
                    "sender": str(item.sender) if item.sender else "Unknown",
                    "datetime_received": item.datetime_received.isoformat() if item.datetime_received else None,
                    "body": str(item.text_body) if item.text_body else (str(item.body) if item.body else ""),
                    "synced_at": datetime.now().isoformat()
                }

                existing_emails[email_id] = email_data
                emails_synced += 1

                time.sleep(0.1)

            except Exception as e:
                continue

        # Save updated emails to MongoDB
        db["emails"].update_one(
            {"user_id": request.user_id},
            {"$set": {"emails": existing_emails}},
            upsert=True
        )

        return EmailSyncResponse(
            status="success",
            message=f"Successfully synced {emails_synced} new emails",
            emails_synced=emails_synced,
            total_emails=len(existing_emails)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email sync failed: {str(e)}")
    
@app.get("/emails/{user_id}")
async def get_user_emails(user_id: str):
    try:
        user_emails_doc = db["emails"].find_one({"user_id": user_id})
        emails = user_emails_doc["emails"] if user_emails_doc and "emails" in user_emails_doc else {}
        return {
            "status": "success",
            "total_emails": len(emails),
            "emails": list(emails.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load emails: {str(e)}")