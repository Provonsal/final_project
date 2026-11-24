import uuid
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models import TaskStatusEnum
from app.schemas.response_comment import ResponseCommentSchema
from app.schemas.response_evaluation import ResponseEvaluationSchema


class ResponseTaskSchema(BaseModel):
    """
    Схема ответа с информацией о задаче.

    Args:
        id: Уникальный идентификатор задачи
        title: Название задачи
        description: Описание задачи
        assignee_id: Уникальный идентификатор исполнителя задачи
        due_date: Дата выполнения задачи (ISO format)
        status: Статус задачи
        team_id: Уникальный идентификатор команды задачи
        evaluation: Оценка задачи (если есть)
        comments: Список комментариев к задаче

    Example:
        id: "550e8400-e29b-41d4-a716-446655440000"
        title: "Обзор дизайна"
        description: "Проверить дизайн интерфейса"
        assignee_id: "550e8400-e29b-41d4-a716-446655440001"
        due_date: "2023-12-31T10:00:00"
        status: "active"
        team_id: "550e8400-e29b-41d4-a716-446655440002"
        evaluation: {"id": "uuid", "rate": "good", "author": "uuid", "value": 7}
        comments: [{"id": "uuid", "created_at": "2023-12-31T10:00:00", "text": "Отличная работа!", "author": "uuid"}]
    """
    id: uuid.UUID = Field(..., description="Уникальный идентификатор задачи")
    title: str = Field(..., description="Название задачи")
    description: str = Field(..., description="Описание задачи")
    assignee_id: uuid.UUID = Field(..., description="Уникальный идентификатор исполнителя задачи")
    due_date: str = Field(..., description="Дата выполнения задачи (ISO format)")
    status: TaskStatusEnum = Field(..., description="Статус задачи")
    team_id: uuid.UUID = Field(..., description="Уникальный идентификатор команды задачи")
    evaluation: Optional[ResponseEvaluationSchema] = Field(None, description="Оценка задачи")
    comments: List[ResponseCommentSchema] = Field(default_factory=list, description="Список комментариев к задаче")