from pydantic import BaseModel


class ResponseUser(BaseModel):
    """
    Схема ответа после регистрации пользователя.

    Attributes:
        login: Имя пользователя (login)
        message: Сообщение об успехе или ошибке
        role: Роль пользователя (опционально)

    Example:
        ResponseUser(login="user@example.com", message="Registration successful", role="user")
    """
    login: str
    message: str
    role: str | None = None