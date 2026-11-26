from random import Random
import secrets
import string
from typing import Sequence
from uuid import uuid4
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload


from app.models.RoleEnum import RoleEnum
from app.models.models import Meeting, MeetingInviteCode, Team, TeamUser, User
from app.repositories.crud_protocol import BaseRepo
from app.models import TeamInviteCode
from sqlalchemy.ext.asyncio import AsyncSession


class MeetingInviteCodeRepo(BaseRepo[MeetingInviteCode]):
    """
    Репозиторий для управления invite-кодами совещаний.

    Provides methods for managing meeting invite codes.
    """

    model = MeetingInviteCode

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория invite-кодов совещаний.

        Args:
            session: Асинхронная сессия базы данных
        """
        self.session = session

    async def get_by_code(self, code: str) -> MeetingInviteCode:
        """
        Получить invite-код по коду.

        Args:
            code: Код приглашения

        Returns:
            MeetingInviteCode: Объект кода

        Raises:
            NoResultFound: Если код не найден
        """
        return (await self.session.scalars(
            select(self.model).where(self.model.body == code)
        )).one()

    async def get_by_meeting_id(self, meeting_id) -> MeetingInviteCode:
        """
        Получить invite-код по идентификатору совещания.

        Args:
            meeting_id: Идентификатор совещания

        Returns:
            MeetingInviteCode: Объект кода

        Raises:
            NoResultFound: Если код не найден
        """
        return (await self.session.scalars(
            select(self.model).where(self.model.connected_to == meeting_id)
        )).one()

    async def get_all_by_meeting_id(self, meeting_id) -> Sequence[MeetingInviteCode]:
        """
        Получить все invite-коды для совещания.

        Args:
            meeting_id: Идентификатор совещания

        Returns:
            list[MeetingInviteCode]: Список кодов
        """
        return (await self.session.scalars(
            select(self.model).where(self.model.connected_to == meeting_id)
        )).all()

    async def deactivate_all_codes_for_meeting(self, meeting_id) -> None:
        """
        Деактивировать все invite-коды для совещания.

        Args:
            meeting_id: Идентификатор совещания
        """
        stmt = (
            update(self.model)
            .where(self.model.connected_to == meeting_id)
            .values(active=False)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    def _secure_random_string(self, n: int) -> str:
        """
        Создать безопасную случайную строку.

        Args:
            n: Длина строки

        Returns:
            str: Случайная строка из букв и цифр
        """
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(n))

    def create_code_body(self) -> str:
        """
        Создать уникальный код для приглашения.

        Returns:
            str: Случайный код длиной 40 символов
        """
        return self._secure_random_string(40)