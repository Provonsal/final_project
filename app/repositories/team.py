from uuid import uuid4
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload


from app.models.RoleEnum import RoleEnum
from app.models.models import TeamUser, User
from app.repositories.crud_protocol import BaseRepo
from app.models import Team
from sqlalchemy.ext.asyncio import AsyncSession



class TeamRepo(BaseRepo[Team]):

    model=Team

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_teams(self, user_id: uuid.UUID):
        
        return (await self.session.scalars(select(self.model).where(self.model.owner == user_id))).all()

    async def get_team_users(self, id: uuid.UUID):
        stmt = (
            select(User)
            .join(TeamUser, TeamUser.user_id == User.id)
            .where(TeamUser.team_id == id)
        )
        return (await self.session.scalars(stmt)).all()

    async def join_team(self, team_id: uuid.UUID, user_id: uuid.UUID):
        # 1. Проверим, что команда и юзер существуют (по желанию)
        team = await self.session.get(Team, team_id)
        user = await self.session.get(User, user_id)
        if team is None or user is None:
            raise ValueError("Team or user not found")

        # 2. Проверим, что связь уже не существует (PK не даст дубль, но лучше явно)
        existing = await self.session.get(
            TeamUser, {"team_id": team_id, "user_id": user_id}
        )
        if existing:
            return existing  # или raise

        # 3. Проверим лимит max_per_team
        count = await self.session.scalar(
            select(func.count()).select_from(TeamUser).where(TeamUser.team_id == team_id)
        )
        if count >= team.max_per_team:
            raise ValueError("Team is full")

        # 4. Создаём связь
        link = TeamUser(team=team, user=user)
        self.session.add(link)
        await self.session.flush()
        return link

    async def leave_team(self, team_id: uuid.UUID, user_id: uuid.UUID):
        link = await self.session.get(
            TeamUser, {"team_id": team_id, "user_id": user_id}
        )
        if not link:
            raise ValueError("User is not in the team")
        await self.session.delete(link)
        await self.session.flush()

    async def belongs_to_team(self, team_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        link = await self.session.get(
            TeamUser, {"team_id": team_id, "user_id": user_id}
        )
        return link is not None

    async def are_owned_by_user(self, team_ids: list[uuid.UUID], user_id: uuid.UUID) -> bool:
        stmt = select(self.model).where(
            self.model.id.in_(team_ids), self.model.owner == user_id
        )
        result = await self.session.scalars(stmt)
        return len(result.all()) == len(team_ids)

    async def is_team_name_taken(self, name: str):
        stmt = select(self.model).where(self.model.name == name)
        result = await self.session.scalars(stmt)
        return bool(result.first())