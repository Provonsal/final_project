from datetime import datetime
import uuid

from pydantic import BaseModel

from app.models.TaskStatusEnum import TaskStatusEnum


class TaskCreate(BaseModel):
    title: str
    description: str
    assignee: uuid.UUID
    due_date: datetime
    status: TaskStatusEnum = TaskStatusEnum.OPEN
