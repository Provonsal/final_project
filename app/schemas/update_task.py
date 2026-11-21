from datetime import datetime

from pydantic import BaseModel

from app.models import TaskStatusEnum


class UpdateTask(BaseModel):
    """
    Схема для частичного обновления задачи.

    Все поля являются опциональными (можно обновлять часть полей).

    Attributes:
        title: Новое название задачи
        description: Новое описание задачи
        due_date: Новая дата выполнения задачи
        status: Новый статус задачи

    Example:
        UpdateTask(title="Updated Task", due_date="2023-12-31")
    """
    title: str | None = None
    description: str | None = None
    due_date: datetime | None = None
    status: TaskStatusEnum | None = None