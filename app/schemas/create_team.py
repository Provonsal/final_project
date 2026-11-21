from pydantic import BaseModel


class CreateTeam(BaseModel):
    """
    Схема для создания новой команды.

    Attributes:
        name: Название команды
        max_per_team: Максимальное количество участников команды (по умолчанию 10)

    Example:
        CreateTeam(name="My Team")
    """
    name: str
    max_per_team: int = 10
