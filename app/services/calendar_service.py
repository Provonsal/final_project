from datetime import UTC, datetime, timezone
from functools import wraps
from inspect import signature
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.exc.exceptions import AuthorizationError, WrongInputError
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
    """Бизнес-логика для работы с календарем встреч."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.meeting_repo = MeetingRepo(session)
        self.team_repo = TeamRepo(session)

    async def _ensure_access(self, user: User, team: Team, task: Task | None = None) -> None:
        """
        Проверяет базовый доступ пользователя к команде и (опционально) задаче.

        Аргументы:
            user: Пользователь, чей доступ проверяется.
            team: Команда, к которой проверяется доступ.
            task: Задача для дополнительной проверки принадлежности к команде
                (если передана). В текущих методах CalendarService не используется,
                но оставлен для совместимости с общим декоратором @requires_access.

        Возвращает:
            None

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде team.
            AuthorizationError: Если роль пользователя не MANAGER и не MEMBER.
            AuthorizationError: Если task передан и task.team_id != team.id.

        Требования:
            Пользователь должен состоять в команде team.
            Роль пользователя должна быть MANAGER или MEMBER.
            Если task передан — он должен принадлежать команде team.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")
        if task is not None:

            if task.team_id != team.id:
                raise AuthorizationError(message="You are not allowed to do that.")
            
            
    @requires_access
    async def get_meetings(
        self,
        team: Team,
        user: User,
        date_from: datetime | None = None,
        date_until: datetime | None = None,
    ):
        """
        Возвращает встречи команды в заданном временном диапазоне.

        Аргументы:
            team: Команда, встречи которой запрашиваются.
            user: Пользователь, выполняющий запрос.
            date_from: Нижняя граница диапазона (включительно).
            date_until: Верхняя граница диапазона. Если None — верхняя граница
                не ограничивается.

        Возвращает:
            list[Meeting]: Встречи команды в диапазоне [date_from, date_until],
                полученные из MeetingRepo.get_all_meetings_from_to.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если роль пользователя не MANAGER и не MEMBER.

        Требования:
            Пользователь должен состоять в команде team.
            Роль пользователя должна быть MANAGER или MEMBER.

        Поведение:
            Доступ проверяется декоратором @requires_access (через _ensure_access).
            Возвращаются только встречи указанной команды.
        """

        if date_from is None:
            date_from = datetime.now(UTC)

        if date_until and date_from >= date_until:
            WrongInputError("date_from must be <= date_until")

        return await self.meeting_repo.get_all_meetings_from_to(
            team.id, 
            date_from, 
            date_until
        )
    
    