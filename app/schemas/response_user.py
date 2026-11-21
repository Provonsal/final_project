import uuid

from pydantic import BaseModel, Field


class ResponseUserSchema(BaseModel):
    """
    Схема ответа с информацией о пользователе.

    Args:
        id: Уникальный идентификатор пользователя
        username: Имя пользователя (обычно email)
        email: Электронная почта пользователя
        active: Статус активности пользователя (True/False)

    Example:
        id: "550e8400-e29b-41d4-a716-446655440000"
        username: "user@example.com"
        email: "user@example.com"
        active: true
    """
    id: uuid.UUID = Field(..., description="Уникальный идентификатор пользователя")
    username: str = Field(..., description="Имя пользователя (обычно email)")
    email: str = Field(..., description="Электронная почта пользователя")
    active: bool = Field(..., description="Статус активности пользователя")