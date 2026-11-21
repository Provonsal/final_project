import uuid

from pydantic import BaseModel, Field


class ResponseUserMe(BaseModel):
    """
    Схема ответа с информацией о текущем пользователе.

    Args:
        id: Уникальный идентификатор пользователя
        username: Имя пользователя (обычно email)
        role: Роль пользователя

    Example:
        id: "550e8400-e29b-41d4-a716-446655440000"
        username: "user@example.com"
        role: "user"
    """
    id: uuid.UUID = Field(..., description="Уникальный идентификатор пользователя")
    username: str = Field(..., description="Имя пользователя (обычно email)")
    role: str = Field(..., description="Роль пользователя")