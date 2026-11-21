from datetime import datetime

from pydantic import BaseModel, Field

from app.models import TaskStatusEnum


class UpdateTask(BaseModel):
    """
    Схема для частичного обновления задачи.

    Все поля являются опциональными (можно обновлять часть полей).

    Args:
        title: Новое название задачи
        description: Новое описание задачи
        due_date: Новая дата выполнения задачи
        status: Новый статус задачи

    Example:
        title: "Обновлённое название"
        description: "Новое описание задачи"
        due_date: "2024-01-15T10:00:00"
        status: "done"
    """
    title: str | None = Field(None, description="Новое название задачи")
    description: str | None = Field(None, description="Новое описание задачи")
    due_date: datetime | None = Field(None, description="Новая дата выполнения задачи")
    status: TaskStatusEnum | None = Field(None, description="Новый статус задачи")