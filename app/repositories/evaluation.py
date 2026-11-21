


import uuid

from sqlalchemy import select

from app.models.models import TaskRate
from app.repositories.crud_protocol import BaseRepo


class EvaluationRepo(BaseRepo[TaskRate]):
    """
    Репозиторий для работы с оценками.

    Класс для управления оценками задач.
    """

    model = TaskRate

    async def get_evaluation_for_task(self, task_id: uuid.UUID) -> TaskRate:
        """
        Получить оценку для задачи.

        Args:
            task_id: Идентификатор задачи

        Returns:
            TaskRate: Оценка для задачи

        Raises:
            NoResultFound: Если оценка не найдена
        """
        return (await self.session.scalars(
            select(
                self.model
            ).where(
                self.model.task_id == task_id
            )
        )).one()