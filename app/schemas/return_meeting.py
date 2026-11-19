import uuid

from pydantic import BaseModel


class ReturnMeetingSchema(BaseModel):
    id: uuid.UUID
    start_time: str
    end_time: str
    team_id: uuid.UUID