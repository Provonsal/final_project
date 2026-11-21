import uuid

from pydantic import BaseModel


class ResponseUserSchema(BaseModel):
    """
    Схема ответа с информацией о пользователе.

    Attributes:
        id: Уникальный идентификатор пользователя
        username: Имя пользователя (обычно email)
        email: Электронная почта пользователя
        active: Статус активности пользователя (True/False)

    Example:
        ResponseUserSchema(
            id=uuid.uuid4(),
            username="user@example.com",
            email="user@example.com",
            active=True
        )
    """
    id: uuid.UUID
    username: str
    email: str
    active: bool