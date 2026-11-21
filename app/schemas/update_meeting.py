from datetime import datetime

from pydantic import BaseModel, Field


class UpdateMeeting(BaseModel):
    """
    Схема для частичного обновления совещания.

    Все поля являются опциональными (можно обновлять часть полей).

    Args:
        starts_at: Новое время начала совещания
        ends_at: Новое время окончания совещания
        max_members: Новое максимальное количество участников совещания

    Example:
        starts_at: "2023-12-31T10:00:00"
        ends_at: "2023-12-31T11:00:00"
        max_members: 20
    """
    starts_at: datetime | None = Field(None, description="Новое время начала совещания")
    ends_at: datetime | None = Field(None, description="Новое время окончания совещания")
    max_members: int | None = Field(None, description="Новое максимальное количество участников совещания")
