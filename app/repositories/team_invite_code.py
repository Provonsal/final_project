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

    model=TeamInviteCode

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_code(self, code):
        return (await self.session.scalars(select(self.model).where(self.model.body == code))).one()

    async def get_by_team_id(self, team_id):
        return (await self.session.scalars(select(self.model).where(self.model.connected_to == team_id))).one()

    def _secure_random_string(self, n: int) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(n))
    
    def create_code_body(self):
        
        return self._secure_random_string(40)

    async def create(self, model_obj) -> None: 
        
        self.session.add(model_obj)
        await self.session.flush()
    
    async def delete(self, model_obj) -> None:
        await self.session.delete(model_obj)