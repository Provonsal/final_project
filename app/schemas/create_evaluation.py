import uuid

from pydantic import BaseModel

from app.models.RateEnum import RateEnum


class CreateEvaluation(BaseModel):
    """
    Схема для создания новой оценки.

    Attributes:
        task_id: Уникальный идентификатор задачи, к которой относится оценка
        rate: Значение оценки (Enum: excellent, good, neutral, poor)

    Example:
        CreateEvaluation(
            task_id=uuid.uuid4(),
            rate=RateEnum.good
        )
    """
    task_id: uuid.UUID
    rate: RateEnum
    