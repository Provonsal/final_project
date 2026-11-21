
from pydantic import BaseModel


class UpdateTeam(BaseModel):
    """
    Схема для частичного обновления информации о команде.

    Все поля являются опциональными (можно обновлять часть полей).

    Attributes:
        name: Новое название команды
        max_per_team: Новое максимальное количество участников команды

    Example:
        UpdateTeam(name="Updated Team Name")
    """
    name: str | None = None
    max_per_team: int | None = None
