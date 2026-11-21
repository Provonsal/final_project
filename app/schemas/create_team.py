from pydantic import BaseModel, Field


class CreateTeam(BaseModel):
    """
    Схема для создания новой команды.

    Args:
        name: Название команды
        max_per_team: Максимальное количество участников команды (по умолчанию 10)

    Example:
        name: "Development Team"
        max_per_team: 10
    """
    name: str = Field(..., description="Название команды")
    max_per_team: int = Field(default=10, description="Максимальное количество участников команды")
