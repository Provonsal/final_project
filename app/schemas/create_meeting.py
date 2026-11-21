from datetime import UTC, datetime, timedelta

from pydantic import BaseModel


class CreateMeeting(BaseModel):
    """
    Схема для создания нового совещания.

    Attributes:
        starts_at: Дата и время начала совещания (по умолчанию текущее время)
        ends_at: Дата и время окончания совещания (по умолчанию текущее время + 3 часа)
        max_members: Максимальное количество участников совещания (по умолчанию 10)

    Example:
        CreateMeeting(
            starts_at="2023-12-31T10:00:00+00:00",
            ends_at="2023-12-31T11:00:00+00:00",
            max_members=15
        )
    """
    starts_at: datetime = datetime.now(tz=UTC)
    ends_at: datetime = datetime.now(tz=UTC) + timedelta(hours=3)
    max_members: int = 10
