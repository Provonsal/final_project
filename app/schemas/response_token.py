from pydantic import BaseModel


class ResponseToken(BaseModel):
    """
    Схема ответа с токенами авторизации.

    Attributes:
        access_token: Строка с access-токеном
        refresh_token: Строка с refresh-токеном
        token_type: Тип токена (обычно "bearer")

    Example:
        ResponseToken(
            access_token="eyJhbGc...",
            refresh_token="eyJhbGc...",
            token_type="bearer"
        )
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"