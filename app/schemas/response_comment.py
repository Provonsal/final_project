import uuid

from pydantic import BaseModel, Field


class ResponseCommentSchema(BaseModel):
    """
    Схема ответа с информацией о комментарии.

    Args:
        id: Уникальный идентификатор комментария
        created_at: Дата и время создания комментария (ISO format)
        text: Текст комментария
        author: Уникальный идентификатор автора комментария

    Example:
        id: "550e8400-e29b-41d4-a716-446655440000"
        created_at: "2023-12-31T10:00:00"
        text: "Отличная работа!"
        author: "550e8400-e29b-41d4-a716-446655440001"
    """
    id: uuid.UUID = Field(..., description="Уникальный идентификатор комментария")
    created_at: str = Field(..., description="Дата и время создания комментария (ISO format)")
    text: str = Field(..., description="Текст комментария")
    author: uuid.UUID = Field(..., description="Уникальный идентификатор автора комментария")