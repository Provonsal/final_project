import uuid

from pydantic import BaseModel

from app.models import TaskStatusEnum


class ResponseTaskSchema(BaseModel):
    """
    Схема ответа с информацией о задаче.

    Attributes:
        id: Уникальный идентификатор задачи
        title: Название задачи
        description: Описание задачи
        assignee_id: Уникальный идентификатор исполнителя задачи
        due_date: Дата выполнения задачи (ISO format)
        status: Статус задачи
        team_id: Уникальный идентификатор команды задачи

    Example:
        ResponseTaskSchema(
            id=uuid.uuid4(),
            title="Design Review",
            description="Review the UI design",
            assignee_id=uuid.uuid4(),
            due_date="2023-12-31T10:00:00",
            status=TaskStatusEnum.active,
            team_id=uuid.uuid4()
        )
    """
    id: uuid.UUID
    title: str
    description: str
    assignee_id: uuid.UUID
    due_date: str
    status: TaskStatusEnum
    team_id: uuid.UUID