import uuid

from pydantic import BaseModel


class ResponseMeetingSchema(BaseModel):
    """
    Схема ответа с информацией о совещании.

    Attributes:
        id: Уникальный идентификатор совещания
        start_time: Дата и время начала совещания (ISO format)
        end_time: Дата и время окончания совещания (ISO format)
        team_id: Уникальный идентификатор команды совещания
        creator: Уникальный идентификатор создателя совещания

    Example:
        ResponseMeetingSchema(
            id=uuid.uuid4(),
            start_time="2023-12-31T10:00:00",
            end_time="2023-12-31T11:00:00",
            team_id=uuid.uuid4(),
            creator=uuid.uuid4()
        )
    """
    id: uuid.UUID
    start_time: str
    end_time: str
    team_id: uuid.UUID
    creator: uuid.UUID