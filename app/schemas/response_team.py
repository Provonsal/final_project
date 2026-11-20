import uuid

from pydantic import BaseModel



class ResponseTeamSchema(BaseModel):
    id: uuid.UUID
    name: str
    max_members: int
    owner_id: uuid.UUID