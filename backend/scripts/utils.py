from pydantic import BaseModel

class Message(BaseModel):
    role: str
    content: str
    
class LoginData(BaseModel):
    username: str
    password: str

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

class UploadedDocument(BaseModel):
    filename: str
    content: str
    file_type: str