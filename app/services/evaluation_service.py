
from functools import wraps
from inspect import signature
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RoleEnum, TaskStatusEnum
from app.models.models import Comment, Task, TaskRate, Team, User
from app.repositories.commentary import CommentRepo
from app.repositories.evaluation import EvaluationRepo
from app.repositories.team import TeamRepo
from app.schemas.create_comment import CommentCreate
from app.schemas.create_evaluation import EvaluationCreate
from app.schemas.update_comment import CommentUpdate
from app.schemas.update_evaluation import EvaluationUpdate
from sqlalchemy.exc import NoResultFound

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

class EvaluationService:
    """Бизнес-логика для работы с оценками."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.evaluation_repo = EvaluationRepo(session)
        self.team_repo = TeamRepo(session)

    async def _ensure_access(
        self, user: User, team: Team, task: Task | None = None
    ) -> None:
        if user.role not in (RoleEnum.MANAGER, RoleEnum.MEMBER):
            raise HTTPException(403, "You are not allowed to do that.")
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise HTTPException(403, "You are not allowed to do that.")
        if task is not None:

            if task.team_id != team.id:
                raise HTTPException(403, "You are not allowed to do that.")
            
            if task.status != TaskStatusEnum.DONE:
                raise HTTPException(status_code=400, detail="Task is not completed yet.")

    @requires_access
    async def get_evaluation(
        self, 
        user: User,
        team: Team,
        task: Task,
    ):

        try:
            evaluation = await self.evaluation_repo.get_evaluation_for_task(task.id)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Evaluation not found.")
        
        return evaluation

    @requires_access
    async def create_evaluation(
        self, 
        data: EvaluationCreate,
        user: User,
        team: Team,
        task: Task,
    ):
        new_evaluation = TaskRate(**data.model_dump())
        await self.evaluation_repo.create(new_evaluation)
        return new_evaluation

    @requires_access
    async def update(
        self, 
        data: EvaluationUpdate,
        user: User,
        team: Team,
        task: Task,
        evaluation: TaskRate
    ):
        changes = data.model_dump(exclude_unset=True)

        if not changes:
            return evaluation
        return await self.evaluation_repo.update(evaluation.id, changes)

    @requires_access
    async def delete(
        self,
        user: User,
        team: Team,
        task: Task,
        evaluation: TaskRate
    ):
        await self.evaluation_repo.delete(evaluation)