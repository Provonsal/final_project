from datetime import UTC, datetime, timezone
from functools import wraps
from inspect import signature
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RoleEnum
from app.models.models import Meeting, Task, Team, TeamInviteCode, TeamUser, User
from app.repositories.meet import MeetingRepo
from app.repositories.team import TeamRepo
from app.repositories.team_invite_code import TeamInviteCodeRepo
from app.repositories.user import UserRepo
from app.schemas.create_meeting import MeetingCreate
from app.schemas.update_meeting import MeetingUpdate


def requires_access(method):
    """Проверяет доступ по параметрам user/team (и task, если он есть)."""
    sig = signature(method)
    if "user" not in sig.parameters or "team" not in sig.parameters:
        raise TypeError(f"{method.__name__} должен принимать 'user' и 'team'")

    @wraps(method)
    async def wrapper(self, *args, **kwargs):
        bound = sig.bind(self, *args, **kwargs)
        bound.apply_defaults()
        user = bound.arguments["user"]
        team = bound.arguments["team"]
        task = bound.arguments.get("task") if "task" in sig.parameters else None

        await self._ensure_access(user, team, task)
        return await method(self, *args, **kwargs)

    return wrapper

class CalendarService:
    """Бизнес-логика для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.meeting_repo = MeetingRepo(session)
        self.team_repo = TeamRepo(session)

    async def _ensure_access(
        self, user: User, team: Team, task: Task | None = None
    ) -> None:
        if user.role not in (RoleEnum.MANAGER, RoleEnum.MEMBER):
            raise HTTPException(403, "You are not allowed to do that.")
        if not await self.team_repo.belongs_to_team(user.id, team.id):
            raise HTTPException(403, "You are not allowed to do that.")
        if task is not None:

            if task.team_id != team.id:
                raise HTTPException(403, "You are not allowed to do that.")
            
            
    @requires_access
    async def get_meetings(
        self, 
        team: Team,
        user: User,
        date_from: datetime = datetime.now(UTC), 
        date_until: datetime | None = None,
    ):
        return await self.meeting_repo.get_all_meetings_from_to(
            team.id, 
            date_from, 
            date_until
        )
    
    