import uuid

from pydantic import BaseModel


class ResponseCommentSchema(BaseModel):
    """
    Схема ответа с информацией о комментарии.

    Attributes:
        id: Уникальный идентификатор комментария
        created_at: Дата и время создания комментария (ISO format)
        text: Текст комментария
        author: Уникальный идентификатор автора комментария

    Example:
        ResponseCommentSchema(
            id=uuid.uuid4(),
            created_at="2023-12-31T10:00:00",
            text="Great job!",
            author=uuid.uuid4()
        )
    """
    id: uuid.UUID
    created_at: str
    text: str
    author: uuid.UUID