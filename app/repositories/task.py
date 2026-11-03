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

    model = Task

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_tasks(self, team_id: uuid.UUID):
        
        return (await self.session.scalars(select(self.model).where(self.model.team_id == team_id))).all()
