import uuid

from pydantic import BaseModel, Field


class ResponseTeamSchema(BaseModel):
    """
    Схема ответа с информацией о команде.

    Args:
        id: Уникальный идентификатор команды
        name: Название команды
        max_members: Максимальное количество участников в команде
        owner_id: Уникальный идентификатор владельца команды

    Example:
        id: "550e8400-e29b-41d4-a716-446655440000"
        name: "Команда разработки"
        max_members: 10
        owner_id: "550e8400-e29b-41d4-a716-446655440001"
    """
    id: uuid.UUID = Field(..., description="Уникальный идентификатор команды")
    name: str = Field(..., description="Название команды")
    max_members: int = Field(..., description="Максимальное количество участников в команде")
    owner_id: uuid.UUID = Field(..., description="Уникальный идентификатор владельца команды")