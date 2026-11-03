from uuid import uuid4
import uuid

from sqlalchemy import select


from app.models.RoleEnum import RoleEnum
from app.repositories.crud_protocol import BaseRepo
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class UserRepo(BaseRepo[User]):

    model=User

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_login(self, login: str):
        stmt = (
            select(self.model)
            .where(self.model.email == login)
            .options(selectinload(self.model.user_credentials))
        )
        return (await self.session.scalars(stmt)).one()

    async def get_users(self):
        return (await self.session.scalars(select(self.model).where(self.model.role != RoleEnum.MANAGER))).all()

    async def change_role(self, user_id: uuid.UUID, new_role: RoleEnum):
        user = await self.get_by_id(user_id)
        user.role = new_role
        await self.session.flush()

    async def create_creds(self, user_creds_model_obj) -> None:
        self.session.add(user_creds_model_obj)
        await self.session.flush()

    async def are_user_in_any_group(self, user_id: uuid.UUID) -> bool:
        stmt = (
            select(self.model)
            .where(self.model.id == user_id)
            .options(selectinload(self.model.mtm_teams_users))
        )
        user = (await self.session.scalars(stmt)).one()
        return len(user.mtm_teams_users) > 0





