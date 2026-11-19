from datetime import UTC, datetime, timedelta
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

    model=Meeting

    async def get_all_meetings(self, team_id: uuid.UUID, user_id: uuid.UUID):
        return (
            await self.session.scalars(
                select(self.model)
                .where(
                    self.model.members.any(
                        MeetingUser.user_id == user_id
                    )
                ).where(
                    self.model.related_team == team_id
                )
            )
        ).all()

    async def get_all_meetings_from_to(
        self, 
        team_id: uuid.UUID,
        date_from: datetime, 
        date_until: datetime | None,
        
    ):

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

    async def belongs_to_meeting(self, meeting_id: uuid.UUID, user_id: uuid.UUID):
        return (await self.session.scalar(
            select(MeetingUser)
            .where(MeetingUser.meeting_id == meeting_id)
            .where(MeetingUser.user_id == user_id)
        )) is not None

    async def get_participants_count(self, meeting_id: uuid.UUID):
        count = 0
        counted = await self.session.scalar(
            select(func.count())
            .select_from(MeetingUser)
            .where(MeetingUser.meeting_id == meeting_id)
        )

        if counted is not None:
            count += counted

        return count

    async def add_participant(self, meeting: Meeting, user: User):
        link = MeetingUser(
            user=user,
            meet=meeting
        )
        self.session.add(link)
        await self.session.flush()
        return link

    async def remove_participant(self, meeting: Meeting, user: User):
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

    