from datetime import datetime
import uuid

from pydantic import BaseModel

from app.models.TaskStatusEnum import TaskStatusEnum


class MeetingUpdate(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    max_members: int | None = None
