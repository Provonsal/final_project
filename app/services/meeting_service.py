from datetime import datetime
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.exc.exceptions import AuthorizationError, WrongInputError
from app.models.RoleEnum import RoleEnum
from app.models.models import Meeting, Team, TeamInviteCode, TeamUser, User
from app.repositories.meet import MeetingRepo
from app.repositories.team import TeamRepo
from app.repositories.team_invite_code import TeamInviteCodeRepo
from app.repositories.user import UserRepo
from app.schemas.create_meeting import MeetingCreate
from app.schemas.success import OperationSuccess
from app.schemas.update_meeting import MeetingUpdate
from sqlalchemy.exc import NoResultFound


class MeetingService:
    """Бизнес-логика для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.meeting_repo = MeetingRepo(session)
        self.team_repo = TeamRepo(session)

    async def get_meetings(
        self, 
        team: Team,
        user: User
    ):
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")
        
        return await self.meeting_repo.get_all_meetings(team.id)
    
    async def get_meeting(
        self, 
        meeting: Meeting,
        team: Team,
        user: User
    ):
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if not await self.meeting_repo.belongs_to_meeting(meeting.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if meeting.related_team != team.id:
            raise WrongInputError(message="Meeting does not belong to the specified team.")

        return meeting

    async def create_meeting(
        self, 
        data: MeetingCreate,
        team: Team,
        user: User
    ):

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")

        if data.starts_at >= data.ends_at:
            raise BusinessRuleError(message="Meeting start time must be before end time.")

        if data.max_members <= 0:
            raise BusinessRuleError(message="Meeting must allow at least one member.")

        if data.max_members > team.max_per_team:
            raise BusinessRuleError(message="Meeting max members cannot exceed team max members.")

        if data.starts_at < datetime.now():
            raise BusinessRuleError(message="Meeting start time cannot be in the past.")

        new_meeting = Meeting(
            starts_at=data.starts_at,
            ends_at=data.ends_at,
            max_members=data.max_members,
            team=team,
            user=user
        )

        await self.meeting_repo.create(new_meeting)
        await self.session.commit()
        return new_meeting

    async def update(
        self,
        meeting: Meeting,
        team: Team,
        data: MeetingUpdate,
        user: User
    ):
        changes = data.model_dump(exclude_unset=True)

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")

        if meeting.related_team != team.id:
            raise WrongInputError(message="Meeting does not belong to the specified team.")

        if meeting.creator != user.id:
            raise AuthorizationError(message="You do not have permission to update this meeting.")
        
        if not changes:
            return meeting  # нечего менять
        
        meeting = await self.meeting_repo.update(meeting.id, changes)
        
        await self.session.commit()
        return meeting
        
    async def delete(
        self,
        meeting: Meeting,
        team: Team,
        user: User
    ):
        if user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")

        if meeting.related_team != team.id:
            raise WrongInputError(message="Meeting does not belong to the specified team.")

        if meeting.creator != user.id:
            raise AuthorizationError(message="You do not have permission to delete this meeting.")
        
        await self.meeting_repo.delete(meeting)
        await self.session.commit()
        return OperationSuccess()