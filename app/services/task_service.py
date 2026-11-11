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
    """Бизнес-логика для работы с задачами."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.team_repo = TeamRepo(session)
        self.task_repo = TaskRepo(session)
        self.user_repo = UserRepo(session)
        self.evaluation_repo = EvaluationRepo(session)

    async def create_task(self, data: TaskCreate, team: Team, user: User):
        """
        Создает задачу в команде и назначает ее участнику команды.

        Аргументы:
            data: Данные для создания задачи (title, description, assignee,
                due_date, status).
            team: Команда, в которой создается задача.
            user: Пользователь, выполняющий создание задачи.

        Возвращает:
            Task: Созданная задача.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если assignee не состоит в команде.
            AuthorizationError: Если пользователь не имеет роли manager.

        Требования:
            Пользователь должен состоять в команде team.
            Assignee (data.assignee) должен состоять в команде team.

        Поведение:
            Задача создается с указанным assignee в качестве исполнителя.
            Для задачи создается оценка TaskRate со значением RateEnum.UNRATED.

        Побочные эффекты:
            Создает задачу, создает запись оценки и выполняет commit сессии.
        """

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

    async def get_all_tasks(self, team: Team, user: User):
        """
        Возвращает задачи команды с учетом роли пользователя.

        Аргументы:
            team: Команда, задачи которой запрашиваются.
            user: Пользователь, выполняющий запрос.

        Возвращает:
            list[Task]: Список задач команды. Для MANAGER — все задачи команды,
                для остальных ролей — только задачи, назначенные на пользователя.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.

        Требования:
            Пользователь должен состоять в команде team.

        Поведение:
            MANAGER получает все задачи команды (task_repo.get_all_tasks),
            остальные — только собственные (task_repo.get_all_tasks_for_user).
        """
        
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if user.role == RoleEnum.MANAGER:
            return await self.task_repo.get_all_tasks(team.id)
        else:
            return await self.task_repo.get_all_tasks_for_user(team.id, user.id)


    async def get_task(self, task: Task, team: Team, user: User):
        """
        Возвращает задачу, если у пользователя есть к ней доступ.

        Аргументы:
            task: Задача, которую нужно получить.
            team: Команда, к которой должна относиться задача.
            user: Пользователь, выполняющий запрос.

        Возвращает:
            Task: Запрошенная задача.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            WrongInputError: Если задача не относится к указанной команде.
            AuthorizationError: Если пользователь не является исполнителем задачи
                или не имеет роль MANAGER.

        Требования:
            Пользователь должен состоять в команде team.
            Задача должна принадлежать команде team.
            Доступ разрешен исполнителю задачи или пользователю с ролью MANAGER.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if task.team_id != team.id:
            raise WrongInputError(message="Task does not belong to the specified team.")

        if task.assignee != user.id and user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")

        return task
    
    async def update_task(self, data: TaskUpdate, task: Task, user: User, team: Team):
        """
        Частично обновляет задачу.

        Аргументы:
            data: Данные для частичного обновления задачи.
            task: Задача, которую нужно обновить.
            user: Пользователь, выполняющий обновление.
            team: Команда, к которой должна относиться задача.

        Возвращает:
            Task: Обновленная задача. Если изменений нет, возвращает текущую
                задачу без выполнения обновления.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            WrongInputError: Если задача не относится к указанной команде.
            AuthorizationError: Если пользователь не имеет роль MANAGER.

        Требования:
            Пользователь должен состоять в команде team.
            Задача должна принадлежать команде team.
            Изменять задачу может исполнитель задачи или пользователь с ролью MANAGER.

        Побочные эффекты:
            При наличии изменений обновляет задачу и выполняет commit сессии.
        """

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

    async def delete_task(self, task: Task, user: User, team: Team):
        """
        Удаляет задачу.

        Аргументы:
            task: Задача, которую нужно удалить.
            user: Пользователь, выполняющий удаление.
            team: Команда, к которой должна относиться задача.

        Возвращает:
            OperationSuccess: Результат успешной операции.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            WrongInputError: Если задача не относится к указанной команде.
            AuthorizationError: Если пользователь не имеет роль MANAGER.

        Требования:
            Пользователь должен состоять в команде team.
            Задача должна принадлежать команде team.
            Удалять задачу может исполнитель задачи или пользователь с ролью MANAGER.

        Побочные эффекты:
            Удаляет задачу и выполняет commit сессии.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if task.team_id != team.id:
            raise WrongInputError(message="Task does not belong to the specified team.")

        if user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")
        
        
        await self.task_repo.delete(task)
        await self.session.commit()
        return OperationSuccess()
