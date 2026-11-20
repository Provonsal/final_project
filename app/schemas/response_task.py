import uuid

from pydantic import BaseModel

from app.models import TaskStatusEnum


class ResponseTaskSchema(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    assignee_id: uuid.UUID
    due_date: str
    status: TaskStatusEnum
    team_id: uuid.UUID