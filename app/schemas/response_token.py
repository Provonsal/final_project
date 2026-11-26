from pydantic import BaseModel, Field


class ResponseToken(BaseModel):
    """
    Схема ответа с токенами авторизации.

    Args:
        access_token: Строка с access-токеном
        refresh_token: Строка с refresh-токеном
        token_type: Тип токена (обычно "bearer")

    Example:
        access_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        refresh_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        token_type: "bearer"
    """
    access_token: str = Field(..., description="Строка с access-токеном")
    refresh_token: str = Field(..., description="Строка с refresh-токеном")
    token_type: str = Field(default="bearer", description="Тип токена")