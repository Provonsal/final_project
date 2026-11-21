import uuid

from pydantic import BaseModel


class ResponseInviteCodeSchema(BaseModel):
    """
    Схема ответа с информацией об invite-коде.

    Attributes:
        id: Уникальный идентификатор invite-кода
        code: Значение invite-кода
        team_id: Уникальный идентификатор команды, связанной с кодом
        is_active: Статус активности кода (True/False)
        creator: Уникальный идентификатор создателя кода

    Example:
        ResponseInviteCodeSchema(
            id=uuid.uuid4(),
            code="abc123",
            team_id=uuid.uuid4(),
            is_active=True,
            creator=uuid.uuid4()
        )
    """
    id: uuid.UUID
    code: str
    team_id: uuid.UUID
    is_active: bool
    creator: uuid.UUID