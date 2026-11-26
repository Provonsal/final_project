from datetime import UTC, datetime, timedelta
from typing import Sequence
from uuid import uuid4
import uuid

from sqlalchemy import func, select


from app.models.RoleEnum import RoleEnum
from app.models.models import Meeting, MeetingUser
from app.repositories.crud_protocol import BaseRepo
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import MeetingInviteCode


class MeetingRepo(BaseRepo[Meeting]):
    """
    Репозиторий для управления совещаниями.

    Provides CRUD operations for meetings and managing participants.
    """

    model = Meeting

    async def get_all_meetings(self, team_id: uuid.UUID, user_id: uuid.UUID) -> Sequence[Meeting]:
        """
        Получить все совещания команды для пользователя.

        Args:
            team_id: Идентификатор команды
            user_id: Идентификатор пользователя

        Returns:
            list[Meeting]: Список совещаний
        """
        return (
            await self.session.scalars(
                select(self.model)
                .where(
                    self.model.related_team == team_id
                ).where(
                    self.model.members.any(
                        MeetingUser.user_id == user_id
                    )
                )
            )
        ).all()

    async def get_all_meetings_from_to(self, team_id: uuid.UUID, date_from: datetime, date_until: datetime | None) -> Sequence[Meeting]:
        """
        Получить все совещания в диапазоне дат.

        Args:
            team_id: Идентификатор команды
            date_from: Дата начала (включительно)
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
                    self.model.related_team == team_id
                ).where(
                    (self.model.starts_at <= date_until) | (self.model.ends_at >= date_from)
                )
            )
        ).all()

    async def belongs_to_meeting(self, meeting_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Проверить, участвует ли пользователь в совещании.

        Args:
            meeting_id: Идентификатор совещания
            user_id: Идентификатор пользователя

        Returns:
            bool: True, если пользователь участник
        """
        return (await self.session.scalar(
            select(MeetingUser)
            .where(MeetingUser.meeting_id == meeting_id)
            .where(MeetingUser.user_id == user_id)
        )) is not None

    async def get_participants_count(self, meeting_id: uuid.UUID) -> int:
        """
        Получить количество участников совещания.

        Args:
            meeting_id: Идентификатор совещания

        Returns:
            int: Количество участников
        """
        count = 0
        counted = await self.session.scalar(
            select(func.count())
            .select_from(MeetingUser)
            .where(MeetingUser.meeting_id == meeting_id)
        )

        if counted is not None:
            count += counted

        return count

    async def add_participant(self, meeting: Meeting, user: User) -> MeetingUser:
        """
        Добавить участника в совещание.

        Args:
            meeting: Объект совещания
            user: Объект пользователя

        Returns:
            MeetingUser: Связующий объект
        """
        link = MeetingUser(
            user=user,
            meet=meeting
        )
        self.session.add(link)
        await self.session.flush()
        return link

    async def remove_participant(self, meeting: Meeting, user: User) -> bool:
        """
        Удалить участника из совещания.

        Args:
            meeting: Объект совещания
            user: Объект пользователя

        Returns:
            bool: True, если участник был удалён
        """
        link = await self.session.scalar(
            select(MeetingUser)
            .where(MeetingUser.meeting_id == meeting.id)
            .where(MeetingUser.user_id == user.id)
        )
        if link:
            await self.session.delete(link)
            await self.session.flush()
            return True
        return False

    