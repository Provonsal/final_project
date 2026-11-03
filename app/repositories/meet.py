from datetime import UTC, datetime, timedelta
from uuid import uuid4
import uuid

from sqlalchemy import select


from app.models.RoleEnum import RoleEnum
from app.models.models import Meeting
from app.repositories.crud_protocol import BaseRepo
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession



class MeetingRepo(BaseRepo[Meeting]):

    model=Meeting

    async def get_all_meetings(self, team_id: uuid.UUID):
        return (await self.session.scalars(select(self.model).where(self.model.related_team == team_id))).all()

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


