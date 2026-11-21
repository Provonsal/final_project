import uuid

from pydantic import BaseModel


class ResponseUserMe(BaseModel):
    """
    Схема ответа с информацией о текущем пользователе.

    Attributes:
        id: Уникальный идентификатор пользователя
        username: Имя пользователя (обычно email)
        role: Роль пользователя

    Example:
        ResponseUserMe(id=uuid.uuid4(), username="user@example.com", role="user")
    """
    id: uuid.UUID
    username: str
    role: str