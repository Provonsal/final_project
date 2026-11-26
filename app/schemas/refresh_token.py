from pydantic import BaseModel


class RefreshTokenSchema(BaseModel):
    """
    Схема токена обновления.

    Attributes:
        refresh_token: Строка с токеном обновления

    Example:
        RefreshTokenSchema(refresh_token="abc123def456...")
    """
    refresh_token: str