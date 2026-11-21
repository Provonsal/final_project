from datetime import datetime

from pydantic import BaseModel


class UpdateMeeting(BaseModel):
    """
    Схема для частичного обновления совещания.

    Все поля являются опциональными (можно обновлять часть полей).

    Attributes:
        starts_at: Новое время начала совещания
        ends_at: Новое время окончания совещания
        max_members: Новое максимальное количество участников совещания

    Example:
        UpdateMeeting(starts_at="2023-12-31T10:00:00", ends_at="2023-12-31T11:00:00")
    """
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    max_members: int | None = None
