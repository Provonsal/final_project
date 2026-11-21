
from pydantic import BaseModel, Field


class UpdateTeam(BaseModel):
    """
    Схема для частичного обновления информации о команде.

    Все поля являются опциональными (можно обновлять часть полей).

    Args:
        name: Новое название команды
        max_per_team: Новое максимальное количество участников команды

    Example:
        name: "Новое название команды"
        max_per_team: 20
    """
    name: str | None = Field(None, description="Новое название команды")
    max_per_team: int | None = Field(None, description="Новое максимальное количество участников команды")
