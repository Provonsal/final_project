
from functools import wraps
from inspect import signature
from typing import Any, Callable
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RoleEnum
from app.models.models import Comment, Task, Team, User
from app.repositories.commentary import CommentRepo
from app.repositories.team import TeamRepo
from app.schemas.create_comment import CommentCreate
from app.schemas.update_comment import CommentUpdate

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

class CommentService:
    """Бизнес-логика для работы с комментариями."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.comment_repo = CommentRepo(session)
        self.team_repo = TeamRepo(session)

    async def _ensure_access(
        self, user: User, team: Team, task: Task | None = None
    ) -> None:
        if user.role not in (RoleEnum.MANAGER, RoleEnum.MEMBER):
            raise HTTPException(403, "You are not allowed to do that.")
        if not await self.team_repo.belongs_to_team(user.id, team.id):
            raise HTTPException(403, "You are not allowed to do that.")
        if task is not None and task.team_id != team.id:
            raise HTTPException(403, "You are not allowed to do that.")

    @requires_access    
    async def get_comments(
        self, 
        task: Task,
        user: User,
        team: Team
    ):

        return await self.comment_repo.get_comments_by_task(task.id)

    @requires_access   
    async def get_comment(
        self, 
        comment: Comment,
        task: Task,
        user: User,
        team: Team
    ):
        
        return comment

    @requires_access   
    async def create_comment(
        self, 
        data: CommentCreate,
        user: User,
        task: Task,
        team: Team
    ):

        new_comment = Comment(**data.model_dump(), user=user, task=task)
        await self.comment_repo.create(new_comment)
        return new_comment

    @requires_access   
    async def update(
        self, 
        data: CommentUpdate,
        comment: Comment, 
        task: Task,
        user: User,
        team: Team
    ):
        changes = data.model_dump(exclude_unset=True)

        if not changes:
            return comment

        return await self.comment_repo.update(comment.id, changes)

    @requires_access
    async def delete(
        self, 
        comment: Comment, 
        task: Task,
        user: User, 
        team: Team
    ):

        await self.comment_repo.delete(comment)