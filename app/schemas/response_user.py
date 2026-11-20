import uuid

from pydantic import BaseModel



class ResponseUserSchema(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    active: bool