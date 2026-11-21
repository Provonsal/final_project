
from pydantic import BaseModel

from app.models.RateEnum import RateEnum


class UpdateEvaluation(BaseModel):
    """
    Схема для частичного обновления оценки.

    Все поля являются опциональными (можно обновлять часть полей).

    Attributes:
        rate: Новое значение оценки (Enum: excellent, good, neutral, poor)

    Example:
        UpdateEvaluation(rate=RateEnum.excellent)
    """
    rate: RateEnum | None = None