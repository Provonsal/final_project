
from pydantic import BaseModel, Field

from app.models.RateEnum import RateEnum


class UpdateEvaluation(BaseModel):
    """
    Схема для частичного обновления оценки.

    Все поля являются опциональными (можно обновлять часть полей).

    Args:
        rate: Новое значение оценки (Enum: excellent, good, neutral, poor)

    Example:
        rate: "excellent"
    """
    rate: RateEnum | None = Field(None, description="Новое значение оценки")