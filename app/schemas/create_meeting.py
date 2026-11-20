from datetime import UTC, datetime, timedelta

from pydantic import BaseModel



class CreateMeeting(BaseModel):
    starts_at: datetime = datetime.now(tz=UTC)
    ends_at: datetime = datetime.now(tz=UTC) + timedelta(hours=3)
    max_members: int = 10
