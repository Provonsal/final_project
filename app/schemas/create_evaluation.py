import uuid

from pydantic import BaseModel

from app.models.RateEnum import RateEnum


class CreateEvaluation(BaseModel):
    task_id: uuid.UUID
    rate: RateEnum
    