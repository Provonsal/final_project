from datetime import datetime
import uuid

from pydantic import BaseModel

from app.models.TaskStatusEnum import TaskStatusEnum


class TeamUpdate(BaseModel):
    name: str | None = None
    max_per_team: int | None = None
