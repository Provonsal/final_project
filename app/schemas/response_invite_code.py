import uuid

from pydantic import BaseModel, Field


class ResponseInviteCodeSchema(BaseModel):
    """
    Схема ответа с информацией об invite-коде.

    Args:
        id: Уникальный идентификатор invite-кода
        code: Значение invite-кода
        team_id: Уникальный идентификатор команды, связанной с кодом
        is_active: Статус активности кода (True/False)
        creator: Уникальный идентификатор создателя кода

    Example:
        id: "550e8400-e29b-41d4-a716-446655440000"
        code: "abc123"
        team_id: "550e8400-e29b-41d4-a716-446655440001"
        is_active: true
        creator: "550e8400-e29b-41d4-a716-446655440002"
    """
    id: uuid.UUID = Field(..., description="Уникальный идентификатор invite-кода")
    code: str = Field(..., description="Значение invite-кода")
    team_id: uuid.UUID = Field(..., description="Уникальный идентификатор команды, связанной с кодом")
    is_active: bool = Field(..., description="Статус активности кода")
    creator: uuid.UUID = Field(..., description="Уникальный идентификатор создателя кода")