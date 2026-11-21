from random import Random
import secrets
import string
from uuid import uuid4
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload


from app.models.RoleEnum import RoleEnum
from app.models.models import Team, TeamUser, User
from app.repositories.crud_protocol import BaseRepo
from app.models import TeamInviteCode
from sqlalchemy.ext.asyncio import AsyncSession


class TeamInviteCodeRepo(BaseRepo[TeamInviteCode]):
    """
    Репозиторий для управления invite-кодами команд.

    Provides CRUD operations for team invite codes used for adding members.
    """

    model = TeamInviteCode

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория.

        Args:
            session: Сессия базы данных
        """
        self.session = session

    async def get_by_code(self, code: str) -> TeamInviteCode:
        """
        Получить invite-код по значению кода.

        Args:
            code: Значение кода

        Returns:
            TeamInviteCode: Invite-код

        Raises:
            NoResultFound: Если код не найден
        """
        return (await self.session.scalars(
            select(self.model).where(self.model.body == code)
        )).one()

    async def get_by_team_id(self, team_id: uuid.UUID) -> TeamInviteCode:
        """
        Получить invite-код для команды.

        Args:
            team_id: Идентификатор команды

        Returns:
            TeamInviteCode: Invite-код команды

        Raises:
            NoResultFound: Если код не найден
        """
        return (await self.session.scalars(
            select(self.model).where(self.model.connected_to == team_id)
        )).one()

    def _secure_random_string(self, n: int) -> str:
        """
        Генерация безопасной случайной строки.

        Args:
            n: Длина строки

        Returns:
            str: Случайная строка
        """
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(n))

    def create_code_body(self) -> str:
        """
        Создать уникальный код приглашения.

        Returns:
            str: Случайная строка длиной 40 символов
        """
        return self._secure_random_string(40)

    async def create(self, model_obj: TeamInviteCode) -> None:
        """
        Создать invite-код.

        Args:
            model_obj: Объект invite-кода
        """
        self.session.add(model_obj)
        await self.session.flush()

    async def delete(self, model_obj: TeamInviteCode) -> None:
        """
        Удалить invite-код.

        Args:
            model_obj: Объект invite-кода
        """
        await self.session.delete(model_obj)