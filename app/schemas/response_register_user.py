from pydantic import BaseModel, Field


class ResponseUser(BaseModel):
    """
    Схема ответа после регистрации пользователя.

    Args:
        login: Имя пользователя (login)
        message: Сообщение об успехе или ошибке
        role: Роль пользователя (опционально)

    Example:
        login: "user@example.com"
        message: "Регистрация успешна"
        role: "user"
    """
    login: str = Field(..., description="Имя пользователя (login)")
    message: str = Field(..., description="Сообщение об успехе или ошибке")
    role: str | None = Field(None, description="Роль пользователя")