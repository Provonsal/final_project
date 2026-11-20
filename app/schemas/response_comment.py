import uuid

from pydantic import BaseModel



class ResponseCommentSchema(BaseModel):
    id: uuid.UUID
    created_at: str
    text: str
    author: uuid.UUID