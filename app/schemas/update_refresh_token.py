
from pydantic import BaseModel


class UpdateRefreshToken(BaseModel):
    """
    Схема для частичного обновления refresh-токена.

    Все поля являются опциональными (можно обновлять часть полей).

    Attributes:
        revoked: Статус отзыва токена (True/False)

    Example:
        UpdateRefreshToken(revoked=True)
    """
    revoked: bool | None = None
