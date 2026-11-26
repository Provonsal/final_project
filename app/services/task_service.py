
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.exc.exceptions import AuthorizationError, BusinessRuleError, WrongInputError
from app.models import RateEnum, RoleEnum, TaskStatusEnum
from app.models.models import Task, TaskRate, Team, User

from app.repositories.evaluation import EvaluationRepo
from app.repositories.task import TaskRepo
from app.repositories.team import TeamRepo
from app.repositories.user import UserRepo
from app.schemas.create_task import CreateTask
from app.schemas.update_task import UpdateTask


class TaskService:
    """Бизнес-логика для работы с задачами."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.team_repo = TeamRepo(session)
        self.task_repo = TaskRepo(session)
        self.user_repo = UserRepo(session)
        self.evaluation_repo = EvaluationRepo(session)

    async def create_task(self, data: CreateTask, team: Team, user: User):
        """
        Создает задачу в команде и назначает ее участнику команды.

        Args:
            data: Данные для создания задачи (title, description, assignee,
                due_date, status).
            team: Команда, в которой создается задача.
            user: Пользователь, выполняющий создание задачи.

        Returns:
            Task: Созданная задача.

        Raises:
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

        Args:
            team: Команда, задачи которой запрашиваются.
            user: Пользователь, выполняющий запрос.

        Returns:
            list[Task]: Список задач команды. Для MANAGER — все задачи команды,
                для остальных ролей — только задачи, назначенные на пользователя.

        Raises:
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
            tasks = await self.task_repo.get_all_tasks(team.id)
        else:
            tasks = await self.task_repo.get_all_tasks_for_user(team.id, user.id)

        return tasks


    async def get_task(self, task: Task, team: Team, user: User):
        """
        Возвращает задачу, если у пользователя есть к ней доступ.

        Args:
            task: Задача, которую нужно получить.
            team: Команда, к которой должна относиться задача.
            user: Пользователь, выполняющий запрос.

        Returns:
            Task: Запрошенная задача.

        Raises:
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
    
    async def update_task(self, data: UpdateTask, task: Task, user: User, team: Team):
        """
        Частично обновляет задачу.

        Args:
            data: Данные для частичного обновления задачи.
            task: Задача, которую нужно обновить.
            user: Пользователь, выполняющий обновление.
            team: Команда, к которой должна относиться задача.

        Returns:
            Task: Обновленная задача. Если изменений нет, возвращает текущую
                задачу без выполнения обновления.

        Raises:
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

        Args:
            task: Задача, которую нужно удалить.
            user: Пользователь, выполняющий удаление.
            team: Команда, к которой должна относиться задача.

        Returns:
            ResponseOperationSuccess: Результат успешной операции.

        Raises:
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
        return True

    async def start_task(self, team: Team, user: User, task: Task):
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if task.team_id != team.id:
            raise WrongInputError(message="Task does not belong to the specified team.")

        if user.role != RoleEnum.MEMBER:
            raise AuthorizationError(message="You are not allowed to do that.")

        if task.status != TaskStatusEnum.OPEN:
            raise BusinessRuleError(message="Task is not ready to start or already started.")

        task = await self.task_repo.start_task(task.id)
        await self.session.commit()
        return task

    async def end_task(self, team: Team, user: User, task: Task):
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if task.team_id != team.id:
            raise WrongInputError(message="Task does not belong to the specified team.")

        if user.role != RoleEnum.MEMBER:
            raise AuthorizationError(message="You are not allowed to do that.")

        if task.status != TaskStatusEnum.IN_PROGRESS:
            raise BusinessRuleError(message="Task is not in progress to end it")

        task = await self.task_repo.end_task(task.id)
        await self.session.commit()
        return task

    async def get_tasks(
        self,
        user: User,
        team: Team,
        date_from: datetime | None = None,
        date_until: datetime | None = None,
    ):
        """
        Возвращает встречи команды в заданном временном диапазоне.

        Args:
            team: Команда, встречи которой запрашиваются.
            user: Пользователь, выполняющий запрос.
            date_from: Нижняя граница диапазона (включительно).
            date_until: Верхняя граница диапазона. Если None — верхняя граница
                не ограничивается.

        Returns:
            list[Meeting]: Встречи команды в диапазоне [date_from, date_until],
                полученные из MeetingRepo.get_all_meetings_from_to.

        Raises:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если роль пользователя не MANAGER и не MEMBER.

        Требования:
            Пользователь должен состоять в команде team.
            Роль пользователя должна быть MANAGER или MEMBER.

        Поведение:
            Доступ проверяется декоратором @requires_access (через _ensure_access).
            Возвращаются только встречи указанной команды.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if user.role not in (RoleEnum.MEMBER, RoleEnum.MANAGER):
            raise AuthorizationError(message="You are not allowed to do that.")

        if date_from is None:
            date_from = datetime.now(UTC)

        if date_until and date_from >= date_until:
            raise WrongInputError("Date_from must be <= date_until")

        return await self.task_repo.get_all_tasks_from_to(
            user.id, 
            date_from, 
            date_until
        )
