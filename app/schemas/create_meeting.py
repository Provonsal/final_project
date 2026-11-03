from datetime import UTC, datetime, timedelta
import uuid

from pydantic import BaseModel

from app.models.TaskStatusEnum import TaskStatusEnum


class MeetingCreate(BaseModel):
    starts_at: datetime = datetime.now(tz=UTC)
    ends_at: datetime = datetime.now(tz=UTC) + timedelta(hours=3)
    max_members: int = 10
