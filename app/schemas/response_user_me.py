import uuid

from pydantic import BaseModel


class ResponseUserMe(BaseModel):
    id: uuid.UUID
    username: str
    role: str