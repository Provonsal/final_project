import uuid

from pydantic import BaseModel, Field

from app.models import RateEnum


class ResponseEvaluationSchema(BaseModel):
    """
    Схема ответа с информацией об оценке.

    Args:
        id: Уникальный идентификатор оценки
        rate: Значение оценки (Enum: excellent, good, neutral, poor)
        author: Уникальный идентификатор автора оценки

    Example:
        id: "550e8400-e29b-41d4-a716-446655440000"
        rate: "good"
        author: "550e8400-e29b-41d4-a716-446655440001"
    """
    id: uuid.UUID = Field(..., description="Уникальный идентификатор оценки")
    rate: RateEnum = Field(..., description="Значение оценки")
    author: uuid.UUID = Field(..., description="Уникальный идентификатор автора оценки")