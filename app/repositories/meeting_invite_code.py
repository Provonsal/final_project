from random import Random
import secrets
import string
from uuid import uuid4
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload


from app.models.RoleEnum import RoleEnum
from app.models.models import Meeting, MeetingInviteCode, Team, TeamUser, User
from app.repositories.crud_protocol import BaseRepo
from app.models import TeamInviteCode
from sqlalchemy.ext.asyncio import AsyncSession



class MeetingInviteCodeRepo(BaseRepo[MeetingInviteCode]):

    model=MeetingInviteCode

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_code(self, code: str):
        return (await self.session.scalars(select(self.model).where(self.model.body == code))).one()

    async def get_by_meeting_id(self, meeting_id):
        return (await self.session.scalars(select(self.model).where(self.model.connected_to == meeting_id))).one()

    def _secure_random_string(self, n: int) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(n))
    
    def create_code_body(self):
        
        return self._secure_random_string(40)
