import uuid

from pydantic import BaseModel


class ResponseTeamSchema(BaseModel):
    """
    Схема ответа с информацией о команде.

    Attributes:
        id: Уникальный идентификатор команды
        name: Название команды
        max_members: Максимальное количество участников в команде
        owner_id: Уникальный идентификатор владельца команды

    Example:
        ResponseTeamSchema(
            id=uuid.uuid4(),
            name="Development Team",
            max_members=10,
            owner_id=uuid.uuid4()
        )
    """
    id: uuid.UUID
    name: str
    max_members: int
    owner_id: uuid.UUID