
from pydantic import BaseModel, Field


class UpdateComment(BaseModel):
    """
    Схема для частичного обновления комментария.

    Все поля являются опциональными (можно обновлять часть полей).

    Args:
        text: Новый текст комментария

    Example:
        text: "Обновлённый текст комментария"
    """
    text: str | None = Field(None, description="Новый текст комментария")
