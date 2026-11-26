from datetime import datetime
import uuid

from pydantic import BaseModel, Field

from app.models.TaskStatusEnum import TaskStatusEnum


class CreateTask(BaseModel):
    """
    Схема для создания задачи.

    Args:
        title: Название задачи
        description: Описание задачи
        assignee: Идентификатор исполнителя
        due_date: Дата выполнения задачи
        status: Статус задачи (по умолчанию OPEN)

    Example:
        title: "Разработать API"
        description: "Разработать эндпоинты для управления задачами"
        assignee: "550e8400-e29b-41d4-a716-446655440000"
        due_date: "2023-12-01T10:00:00"
        status: "open"
    """
    title: str = Field(..., description="Название задачи")
    description: str = Field(..., description="Описание задачи")
    assignee: uuid.UUID = Field(..., description="Идентификатор исполнителя")
    due_date: datetime = Field(..., description="Дата выполнения задачи")
    status: TaskStatusEnum = Field(default=TaskStatusEnum.OPEN, description="Статус задачи")
