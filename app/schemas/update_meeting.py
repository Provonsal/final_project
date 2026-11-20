from datetime import datetime

from pydantic import BaseModel



class UpdateMeeting(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    max_members: int | None = None
