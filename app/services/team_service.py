import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RoleEnum
from app.models.models import Team, TeamInviteCode, TeamUser, User
from app.repositories.team import TeamRepo
from app.repositories.team_invite_code import TeamInviteCodeRepo
from app.repositories.user import UserRepo
from app.schemas.create_team import TeamCreate
from app.schemas.task_create import TaskCreate
from app.schemas.update_team import TeamUpdate


class TeamService:
    """Бизнес-логика для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.team_repo = TeamRepo(session)
        self.user_repo = UserRepo(session)
        self.team_invite_code_repo = TeamInviteCodeRepo(session)

    async def get_teams(
        self, 
        user: User
    ):
        if user.role not in (RoleEnum.MANAGER, RoleEnum.MEMBER):
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")
        
        return await self.team_repo.get_teams(user.id)

    async def get_team_users(
        self, 
        team: Team, 
        user: User
    ):
        if user.role not in (RoleEnum.MANAGER, RoleEnum.MEMBER):
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")
        
        members_list = await self.team_repo.get_team_users(team.id)
        
        return members_list

    async def update(
        self, 
        team: Team,
        user: User,
        data: TeamUpdate
    ):

        changes = data.model_dump(exclude_unset=True)

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

        if not changes:
            return await self.team_repo.get_by_id(team.id)  # нечего менять

        if team.owner != user.id:
            raise HTTPException(status_code=403, detail="Only the owner can update the team.")

        team = await self.team_repo.update(team.id, changes)
        await self.session.commit()
        return team

    async def delete(
        self, 
        team: Team, 
        user: User
    ):
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

        if team.owner != user.id:
            raise HTTPException(status_code=403, detail="Only the owner can delete the team.")

        await self.team_repo.delete(team)
        await self.session.commit()


    async def get_team(
        self,
        team: Team,
        user: User
    ):
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

        if team.owner != user.id and user.role != RoleEnum.MANAGER:
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")
        
        return team

    async def join_team(
        self, 
        user: User, 
        invite_code: str
    ):

        code = await self.team_invite_code_repo.get_by_code(invite_code)

        if not code.active: 
            raise HTTPException(status_code=400, detail="Invite code not active")

        if user.role == RoleEnum.AUTH:

            await self.user_repo.change_role(user.id, RoleEnum.MEMBER)

        await self.team_repo.join_team(code.connected_to, user.id)
        
        await self.session.commit()

    async def leave_team(
        self, 
        user: User, 
        team: Team
    ):

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

        if team.owner == user.id:
            raise HTTPException(status_code=403, detail="Owner cannot leave the team. Transfer ownership or delete the team.")

        if user.role not in (RoleEnum.MEMBER, RoleEnum.MANAGER):
            raise HTTPException(status_code=403, detail="Only team members can leave the team.")

        await self.team_repo.leave_team(team.id, user.id)

        if (not await self.user_repo.are_user_in_any_group(user.id)) and user.role == RoleEnum.MEMBER:
            await self.user_repo.change_role(user.id, RoleEnum.AUTH)
        
        await self.session.commit()

    async def create_team(
        self, 
        user: User, 
        data: TeamCreate
    ):

        if user.role != RoleEnum.MANAGER:
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

        if await self.team_repo.is_team_name_taken(data.name):
            raise HTTPException(status_code=400, detail="Team name already taken.")

        if data.max_per_team < 1:
            raise HTTPException(status_code=400, detail="max_per_team must be at least 1.")

        if data.max_per_team > 100:
            raise HTTPException(status_code=400, detail="max_per_team cannot exceed 100.")
        
        new_team = Team(
            name=data.name,
            max_per_team=data.max_per_team,
            owner=user.id
        )

        await self.team_repo.create(new_team)
        await self.create_invite_code(new_team, user)
        await self.session.commit()
        return new_team

    async def create_invite_code(
        self,
        team: Team,
        user: User
    ):
        if not await self.team_repo.are_owned_by_user([team.id], user.id):
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

        if team.owner != user.id:
            raise HTTPException(status_code=403, detail="Only the owner can create invite codes.")

        new_invite_code = TeamInviteCode(
            creator=user.id,
            team=team,
            body=self.team_invite_code_repo.create_code_body()
        )

        await self.team_invite_code_repo.create(new_invite_code)
        await self.session.commit()

    async def get_invite_code(
        self,
        team: Team,
        user: User
    ):
        if not await self.team_repo.are_owned_by_user([team.id], user.id):
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

        if team.owner != user.id:
            raise HTTPException(status_code=403, detail="Only the owner can get invite codes.")

        invite_code = await self.team_invite_code_repo.get_by_team_id(team.id)

        return invite_code
        
    async def belongs_to_team(self, user: User, team: Team) -> bool:
        
        return await self.team_repo.belongs_to_team(team.id, user.id)