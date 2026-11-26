import uuid

from pydantic import BaseModel, Field


class ResponseMeetingSchema(BaseModel):
    """
    Схема ответа с информацией о совещании.

    Args:
        id: Уникальный идентификатор совещания
        start_time: Дата и время начала совещания (ISO format)
        end_time: Дата и время окончания совещания (ISO format)
        team_id: Уникальный идентификатор команды совещания
        creator: Уникальный идентификатор создателя совещания
        max_members: Максимальное количество участников собрания

    Example:
        id: "550e8400-e29b-41d4-a716-446655440000"
        start_time: "2023-12-31T10:00:00"
        end_time: "2023-12-31T11:00:00"
        team_id: "550e8400-e29b-41d4-a716-446655440001"
        creator: "550e8400-e29b-41d4-a716-446655440002"
    """
    id: uuid.UUID = Field(..., description="Уникальный идентификатор совещания")
    start_time: str = Field(..., description="Дата и время начала совещания (ISO format)")
    end_time: str = Field(..., description="Дата и время окончания совещания (ISO format)")
    team_id: uuid.UUID = Field(..., description="Уникальный идентификатор команды совещания")
    creator: uuid.UUID = Field(..., description="Уникальный идентификатор создателя совещания")
    max_members: int = Field(..., description="Максимальное количество участников собрания")