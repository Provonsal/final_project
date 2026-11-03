from datetime import datetime
import uuid

from pydantic import BaseModel

from app.models.TaskStatusEnum import TaskStatusEnum
from app.models.RateEnum import RateEnum


class EvaluationCreate(BaseModel):
    task_id: uuid.UUID
    rate: RateEnum
    