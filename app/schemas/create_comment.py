
from pydantic import BaseModel


class CreateComment(BaseModel):
    """
    Схема для создания нового комментария.

    Attributes:
        text: Текст комментария

    Example:
        CreateComment(text="Great job!")
    """
    text: str
