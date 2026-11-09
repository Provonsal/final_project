from logging import Manager
from typing import Annotated, Any
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.exc.exceptions import NotFoundError
from app.models import RoleEnum
from app.models.models import Comment, Meeting, Task, TaskRate, Team, User
from app.repositories.commentary import CommentRepo
from app.repositories.evaluation import EvaluationRepo
from app.repositories.meet import MeetingRepo
from app.repositories.task import TaskRepo
from app.repositories.team import TeamRepo
from app.services.auth import AuthService
from app.services.calendar_service import CalendarService
from app.services.comment_service import CommentService
from app.services.evaluation_service import EvaluationService
from app.services.meeting_service import MeetingService
from app.services.task_service import TaskService
from app.services.team_service import TeamService
from app.services.user_service import UserService
from utils.token_manager import TKNManager


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

db_dependency = Annotated[AsyncSession, Depends(get_session)]

def get_user_service(session: db_dependency) -> UserService:
    return UserService(session)

def get_auth_service(session: db_dependency) -> AuthService:
    return AuthService(session)

def get_team_service(session: db_dependency) -> TeamService:
    return TeamService(session)

def get_task_service(session: db_dependency) -> TaskService:
    return TaskService(session)

def get_meeting_service(session: db_dependency) -> MeetingService:
    return MeetingService(session)

def get_calendar_service(session: db_dependency) -> CalendarService:
    return CalendarService(session)

def get_comment_service(session: db_dependency) -> CommentService:
    return CommentService(session)

def get_evaluation_service(session: db_dependency) -> EvaluationService:
    return EvaluationService(session)

UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
TeamServiceDep = Annotated[TeamService, Depends(get_team_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
MeetingServiceDep = Annotated[MeetingService, Depends(get_meeting_service)]
CalendarServiceDep = Annotated[CalendarService, Depends(get_calendar_service)]
CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]
EvaluationServiceDep = Annotated[EvaluationService, Depends(get_evaluation_service)]

async def get_current_user(
    user_repo_dep: UserServiceDep,
    token: str = Depends(oauth2_scheme),
) -> User:
    """Получение текущего пользователя по JWT токену"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload: dict[str, Any] = TKNManager.decode_token(token)
        user_id: str | None = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
        
        # Проверяем, что это access токен
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=401,
                detail="Invalid token type"
            )
            
    except JWTError:
        raise credentials_exception
    
    # Получаем пользователя из БД
    try:
        user = await user_repo_dep.get_user(UUID(user_id))
    except:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Inactive user"
        )
    
    return user


def require_roles(*allowed: RoleEnum):
    """Возвращает зависимость, которая пускает только перечисленные роли."""
    async def _checker(current_user: CurrentUserDep) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(r.value for r in allowed)}",
            )
        return current_user
    return _checker


async def get_team(
    team_id: UUID,
    session: db_dependency,
):
    try:
        team = await TeamRepo(session).get_by_id(team_id)
    except:
        raise NotFoundError(
            resource="Team",
            resource_id=team_id
        )
    return team


async def get_task(
    task_id: UUID,
    session: db_dependency,
):
    try:
        task = await TaskRepo(session).get_by_id(task_id)
    except:
        raise NotFoundError(
            resource="Task",
            resource_id=task_id
        )
    return task


async def get_comment(
    comment_id: UUID,
    session: db_dependency
):
    try:
        comment = await CommentRepo(session).get_by_id(comment_id)
    except:
        raise NotFoundError(
            resource="Comment",
            resource_id=comment_id
        )
    return comment

async def get_evaluation(
    task_id: UUID,
    session: db_dependency
):
    try:
        evaluation = await EvaluationRepo(session).get_evaluation_for_task(task_id)
    except:
        raise NotFoundError(
            resource="Evaluation",
            resource_id=task_id
        )
    return evaluation

async def get_meeting(
    meeting_id: UUID,
    session: db_dependency
):
    try:
        meeting = await MeetingRepo(session).get_by_id(meeting_id)
    except:
        raise NotFoundError(
            resource="Meeting",
            resource_id=meeting_id
        )
    return meeting

CurrentUserDep = Annotated[User, Depends(get_current_user)]
MemberOrManagerDep = Annotated[User, Depends(require_roles(RoleEnum.MEMBER, RoleEnum.MANAGER))]
ManagerDep = Annotated[User, Depends(require_roles(RoleEnum.MANAGER))]
MemberDep = Annotated[User, Depends(require_roles(RoleEnum.MEMBER))]
AnyAuthDep = Annotated[User, Depends(require_roles(RoleEnum.AUTH, RoleEnum.MEMBER, RoleEnum.MANAGER))]
TeamDep = Annotated[Team, Depends(get_team)]
TaskDep = Annotated[Task, Depends(get_task)]
CommentDep = Annotated[Comment, Depends(get_comment)]
EvaluationDep = Annotated[TaskRate, Depends(get_evaluation)]
MeetingDep = Annotated[Meeting, Depends(get_meeting)]

__all__ = [
    "UserServiceDep",
    "AuthServiceDep",
    "CurrentUserDep",
    "MemberOrManagerDep",

]