import uuid

from pydantic import BaseModel, Field

from app.models.RateEnum import RateEnum


class CreateEvaluation(BaseModel):
    """
    Схема для создания новой оценки.

    Args:
        task_id: Уникальный идентификатор задачи, к которой относится оценка
        rate: Значение оценки (Enum: excellent, good, neutral, poor)

    Example:
        task_id: "550e8400-e29b-41d4-a716-446655440000"
        rate: "good"
    """
    task_id: uuid.UUID = Field(..., description="Уникальный идентификатор задачи")
    rate: RateEnum = Field(..., description="Значение оценки")
    