import uuid

from pydantic import BaseModel


class UserMeResponse(BaseModel):
    id: uuid.UUID
    username: str
    role: str