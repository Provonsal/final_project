from datetime import datetime
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from app.exc.exceptions import AuthorizationError, NotFoundError, WrongInputError
from app.models import RateEnum, RoleEnum
from app.models.TaskStatusEnum import TaskStatusEnum
from app.models.models import Task, TaskRate, Team, TeamInviteCode, TeamUser, User

from app.repositories.evaluation import EvaluationRepo
from app.repositories.task import TaskRepo
from app.repositories.team import TeamRepo
from app.repositories.team_invite_code import TeamInviteCodeRepo
from app.repositories.user import UserRepo
from app.schemas.success import OperationSuccess
from app.schemas.task_create import TaskCreate
from app.schemas.task_update import TaskUpdate


class TaskService:
    """Бизнес-логика для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.team_repo = TeamRepo(session)
        self.task_repo = TaskRepo(session)
        self.user_repo = UserRepo(session)
        self.evaluation_repo = EvaluationRepo(session)

    async def create_task(
        self, 
        data: TaskCreate,
        team: Team,
        user: User
    ):

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if not await self.team_repo.belongs_to_team(team.id, data.assignee):
            raise AuthorizationError(message="Assignee is not a member of the team.")

        if user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")

        assignee_user = await self.user_repo.get_by_id(data.assignee)
        
        new_task = Task(
            title=data.title,
            description=data.description,
            user=assignee_user,
            due_date=data.due_date,
            status=data.status,
            team=team
        )

        await self.task_repo.create(new_task)

        unrated_rate = TaskRate(
            user=assignee_user,
            task=new_task,
            rate=RateEnum.UNRATED
        )

        await self.evaluation_repo.create(unrated_rate)

        await self.session.commit()
        return new_task

    async def get_all_tasks(
        self,
        team: Team,
        user: User
    ):


        
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if user.role != RoleEnum.MANAGER:
            try:
                tasks = await self.task_repo.get_all_tasks_for_user(team.id, user.id)
            except NoResultFound:
                raise NotFoundError("Task", f"No tasks found for user with id {user.id}.")
        else:
            try:
                tasks = await self.task_repo.get_all_tasks(team.id)
            except NoResultFound:
                raise NotFoundError("Task", f"No tasks found for team id {team.id}.")

        return tasks

    async def get_task(
        self,
        task: Task,
        team: Team,
        user: User
    ):
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if task.team_id != team.id:
            raise WrongInputError(message="Task does not belong to the specified team.")

        if task.assignee != user.id or user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")

        return task
    
    async def update_task(
        self, 
        data: TaskUpdate,
        task: Task,
        user: User,
        team: Team
    ):
        changes = data.model_dump(exclude_unset=True)

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if task.team_id != team.id:
            raise WrongInputError(message="Task does not belong to the specified team.")

        if user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")

        if not changes:
            return task  # нечего менять
        
        task = await self.task_repo.update(task.id, changes)
        await self.session.commit()
        return task

    async def delete_task(
        self,
        task: Task,
        user: User,
        team: Team
    ):
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if task.team_id != team.id:
            raise WrongInputError(message="Task does not belong to the specified team.")

        if user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")
        
        
        await self.task_repo.delete(task)
        await self.session.commit()
        return OperationSuccess()
