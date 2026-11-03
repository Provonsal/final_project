from datetime import datetime
import uuid

from pydantic import BaseModel

from app.models.TaskStatusEnum import TaskStatusEnum


class TeamCreate(BaseModel):
    name: str
    max_per_team: int = 10
