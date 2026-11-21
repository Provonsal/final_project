import uuid

from pydantic import BaseModel

from app.models import RateEnum


class ResponseEvaluationSchema(BaseModel):
    """
    Схема ответа с информацией об оценке.

    Attributes:
        id: Уникальный идентификатор оценки
        rate: Значение оценки (Enum: excellent, good, neutral, poor)
        author: Уникальный идентификатор автора оценки

    Example:
        ResponseEvaluationSchema(
            id=uuid.uuid4(),
            rate=RateEnum.good,
            author=uuid.uuid4()
        )
    """
    id: uuid.UUID
    rate: RateEnum
    author: uuid.UUID