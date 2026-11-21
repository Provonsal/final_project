from uuid import uuid4
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload


from app.models.RoleEnum import RoleEnum
from app.models.models import TeamUser, User
from app.repositories.crud_protocol import BaseRepo
from app.models import Task
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

        Аргументы:
            session (AsyncSession): Асинхронная сессия базы данных
        """
        self.session = session

    async def get_all_tasks(self, team_id: uuid.UUID):
        """
        Получает все задачи принадлежащие команде.

        Аргументы:
            team_id (uuid.UUID): Идентификатор команды

        Возвращает:
            list[Task]: Список всех задач команды

        Пример:
            >>> repo = TaskRepo(session)
            >>> tasks = await repo.get_all_tasks(team_uuid)
        """
        return (await self.session.scalars(
            select(self.model).where((self.model.team_id == team_id))
        )).all()

    async def get_all_tasks_for_user(self, team_id: uuid.UUID, user_id: uuid.UUID):
        """
        Получает все задачи, которые выполняет пользователь в команде.

        Аргументы:
            team_id (uuid.UUID): Идентификатор команды
            user_id (uuid.UUID): Идентификатор пользователя

        Возвращает:
            list[Task]: Список задач, назначенных на пользователя

        Пример:
            >>> repo = TaskRepo(session)
            >>> user_tasks = await repo.get_all_tasks_for_user(team_uuid, user_uuid)
        """
        return (await self.session.scalars(
            select(self.model).where((self.model.team_id == team_id) & (self.model.assignee == user_id))
        )).all()
