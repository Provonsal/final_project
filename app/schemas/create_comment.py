
from pydantic import BaseModel, Field


class CreateComment(BaseModel):
    """
    Схема для создания нового комментария.

    Args:
        text: Текст комментария

    Example:
        text: "Отличная работа!"
    """
    text: str = Field(..., description="Текст комментария")
