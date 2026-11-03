from datetime import datetime
import uuid

from pydantic import BaseModel

from app.models.TaskStatusEnum import TaskStatusEnum


class CommentCreate(BaseModel):
    text: str
