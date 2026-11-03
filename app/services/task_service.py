from datetime import datetime
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from app.models import RoleEnum
from app.models.TaskStatusEnum import TaskStatusEnum
from app.models.models import Task, Team, TeamInviteCode, TeamUser, User

from app.repositories.task import TaskRepo
from app.repositories.team import TeamRepo
from app.repositories.team_invite_code import TeamInviteCodeRepo
from app.repositories.user import UserRepo
from app.schemas.task_create import TaskCreate
from app.schemas.task_update import TaskUpdate


class TaskService:
    """Бизнес-логика для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.team_repo = TeamRepo(session)
        self.task_repo = TaskRepo(session)
        self.user_repo = UserRepo(session)

    async def create_task(
        self, 
        data: TaskCreate,
        team: Team,
        user: User
    ):

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

        if not await self.team_repo.belongs_to_team(team.id, data.assignee):
            raise HTTPException(status_code=403, detail="Assignee is not a member of the team.")

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
        await self.session.commit()

    async def get_all_tasks(
        self,
        team: Team,
        user: User
    ):


        
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

        try:
            tasks = await self.task_repo.get_all_tasks(team.id)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Tasks not found")

        return tasks

    async def get_task(
        self,
        task: Task,
        team: Team,
        user: User
    ):
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

        if task.team_id != team.id:
            raise HTTPException(status_code=400, detail="Task does not belong to the specified team.")

        if task.assignee != user.id and user.role != RoleEnum.MANAGER:
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

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
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

        if task.team_id != team.id:
            raise HTTPException(status_code=400, detail="Task does not belong to the specified team.")

        if task.assignee != user.id and user.role != RoleEnum.MANAGER:
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

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
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")

        if task.team_id != team.id:
            raise HTTPException(status_code=400, detail="Task does not belong to the specified team.")
        
        if task.assignee != user.id and user.role != RoleEnum.MANAGER:
            raise HTTPException(status_code=403, detail="You are not allowed to do that.")
        
        
        await self.task_repo.delete(task)
        await self.session.commit()

    async def belong_to_team(self, team_id: uuid.UUID, task_id: uuid.UUID):
        task = await self.task_repo.get_by_id(task_id)
        return task.team_id == team_id