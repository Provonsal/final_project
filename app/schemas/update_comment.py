
from pydantic import BaseModel


class UpdateComment(BaseModel):
    """
    Схема для частичного обновления комментария.

    Все поля являются опциональными (можно обновлять часть полей).

    Attributes:
        text: Новый текст комментария

    Example:
        UpdateComment(text="Updated comment text")
    """
    text: str | None = None
