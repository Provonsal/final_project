from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field


class CreateMeeting(BaseModel):
    """
    Схема для создания нового совещания.

    Args:
        starts_at: Дата и время начала совещания (по умолчанию текущее время)
        ends_at: Дата и время окончания совещания (по умолчанию текущее время + 3 часа)
        max_members: Максимальное количество участников совещания (по умолчанию 10)

    Example:
        starts_at: "2023-12-31T10:00:00+00:00"
        ends_at: "2023-12-31T11:00:00+00:00"
        max_members: 15
    """
    starts_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="Дата и время начала совещания")
    ends_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC) + timedelta(hours=3), description="Дата и время окончания совещания")
    max_members: int = Field(default=10, description="Максимальное количество участников совещания")
