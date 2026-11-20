import uuid

from pydantic import BaseModel



class ResponseInviteCodeSchema(BaseModel):
    id: uuid.UUID
    code: str
    team_id: uuid.UUID
    is_active: bool
    creator: uuid.UUID