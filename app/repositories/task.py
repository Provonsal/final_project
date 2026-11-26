from datetime import UTC, datetime, timedelta
from uuid import uuid4
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload


from app.models.RoleEnum import RoleEnum
from app.models.models import TeamUser, User
from app.repositories.crud_protocol import BaseRepo
from app.models import Task, TaskStatusEnum
from sqlalchemy.ext.asyncio import AsyncSession



class TaskRepo(BaseRepo[Task]):
    """
    Репозиторий для операций с задачами.

    Предоставляет методы для получения списка задач по команде и пользователю.
    """

    model = Task

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория задач.

        Args:
            session (AsyncSession): Асинхронная сессия базы данных
        """
        self.session = session

    async def get_all_tasks(self, team_id: uuid.UUID):
        """
        Получает все задачи принадлежащие команде.

        Args:
            team_id (uuid.UUID): Идентификатор команды

        Returns:
            list[Task]: Список всех задач команды

        Example:
            >>> repo = TaskRepo(session)
            >>> tasks = await repo.get_all_tasks(team_uuid)
        """
        return (await self.session.scalars(
            select(self.model).where((self.model.team_id == team_id))
        )).all()

    async def get_all_tasks_for_user(self, team_id: uuid.UUID, user_id: uuid.UUID):
        """
        Получает все задачи, которые выполняет пользователь в команде.

        Args:
            team_id (uuid.UUID): Идентификатор команды
            user_id (uuid.UUID): Идентификатор пользователя

        Returns:
            list[Task]: Список задач, назначенных на пользователя

        Example:
            >>> repo = TaskRepo(session)
            >>> user_tasks = await repo.get_all_tasks_for_user(team_uuid, user_uuid)
        """
        return (await self.session.scalars(
            select(self.model).where((self.model.team_id == team_id) & (self.model.assignee == user_id))
        )).all()

    async def start_task(self, task_id: uuid.UUID):
        stmt = update(self.model).where(self.model.id == task_id).values(status=TaskStatusEnum.IN_PROGRESS).returning(self.model)
        return (await self.session.execute(stmt)).scalar_one()

    async def end_task(self, task_id: uuid.UUID):
        stmt = update(self.model).where(self.model.id == task_id).values(status=TaskStatusEnum.DONE).returning(self.model)
        return (await self.session.execute(stmt)).scalar_one()

    async def get_all_tasks_from_to(self, user_id, date_from, date_until):
        """
        Получить все задачи в диапазоне дат.

        Args:
            team_id: Идентификатор команды
            date_from: Пока не используется (Временно)
            date_until: Дата окончания (включительно, по умолчанию текущее время + 30 дней)

        Returns:
            list[Meeting]: Список совещаний в диапазоне дат
        """

        date_until = date_until if date_until is not None else datetime.now(tz=UTC) + timedelta(days=30)

        return (
            await self.session.scalars(
                select(
                    self.model
                ).where(
                    self.model.assignee == user_id
                ).where(
                    self.model.due_date <= date_until
                ).where(
                    self.model.status != TaskStatusEnum.DONE
                )
            )
        ).all()
    
