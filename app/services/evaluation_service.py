
from functools import wraps
from inspect import signature
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.exc.exceptions import AuthorizationError, BusinessRuleError, NotFoundError
from app.models import RoleEnum, TaskStatusEnum
from app.models.models import Comment, Task, TaskRate, Team, User
from app.repositories.commentary import CommentRepo
from app.repositories.evaluation import EvaluationRepo
from app.repositories.team import TeamRepo
from app.schemas.create_comment import CommentCreate
from app.schemas.create_evaluation import EvaluationCreate
from app.schemas.success import OperationSuccess
from app.schemas.update_comment import CommentUpdate
from app.schemas.update_evaluation import EvaluationUpdate
from sqlalchemy.exc import NoResultFound

class EvaluationService:
    """Бизнес-логика для работы с оценками."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.evaluation_repo = EvaluationRepo(session)
        self.team_repo = TeamRepo(session)
    
    async def get_evaluation(self, user: User, team: Team, task: Task, evaluation: TaskRate):
        """
        Возвращает оценку после проверки базового доступа.

        Аргументы:
            user: Пользователь, выполняющий запрос.
            team: Команда, в контексте которой запрашивается оценка.
            task: Задача, к которой относится оценка.
            evaluation: Оценка, которую нужно вернуть.

        Возвращает:
            TaskRate: Переданная оценка без изменений.

        Исключения:
            AuthorizationError: Если пользователь не MANAGER/MEMBER, не состоит
                в команде или задача не принадлежит команде (см. _ensure_access).

        Требования:
            Пользователь должен быть MANAGER или MEMBER.
            Пользователь должен состоять в команде team.
            task должен принадлежать team.

        Замечание:
            Метод не обращается к репозиторию — оценка должна быть загружена
            вызывающим кодом (обычно в роуте). Соответствие evaluation → task
            и права пользователя на конкретную оценку здесь не проверяются.
        """

        if user.role not in (RoleEnum.MANAGER, RoleEnum.MEMBER):
            raise AuthorizationError(message="You are not allowed to do that.")
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")
        if task.team_id != team.id:
            raise AuthorizationError(message="You are not allowed to do that.")
        if evaluation.task_id != task.id:
            raise AuthorizationError(message="You are not allowed to do that.")
        
        return evaluation

    
    async def create_evaluation(self, data: EvaluationCreate, user: User, team: Team, task: Task):
        """
        Создает оценку задачи от имени указанного пользователя.

        Аргументы:
            data: Данные для создания оценки.
            user: Пользователь, выполняющий создание.
            team: Команда, в контексте которой создается оценка.
            task: Задача, к которой относится оценка.

        Возвращает:
            TaskRate: Созданная оценка.

        Исключения:
            AuthorizationError: Если пользователь не MANAGER/MEMBER, не состоит
                в команде или задача не принадлежит команде (см. _ensure_access).

        Требования:
            Пользователь должен быть MANAGER или MEMBER.
            Пользователь должен состоять в команде team.
            task должен принадлежать team.

        Побочные эффекты:
            Создает запись TaskRate в репозитории.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")
        if user.role not in (RoleEnum.MANAGER):
            raise AuthorizationError(message="You are not allowed to do that.")
        if task.team_id != team.id:
            raise AuthorizationError(message="You are not allowed to do that.")
        try:
            existing_rating = await self.evaluation_repo.get_evaluation_for_task(task.id)
            if existing_rating:
                raise BusinessRuleError(message="Rate already exists for this task")
        except NoResultFound:
            pass

        new_evaluation = TaskRate(**data.model_dump(), user=user, task=task)
        await self.evaluation_repo.create(new_evaluation)
        await self.session.commit()
        return new_evaluation

    
    async def update(self, data: EvaluationUpdate, user: User, team: Team, task: Task, evaluation: TaskRate):
        """
        Частично обновляет оценку.

        Аргументы:
            data: Данные для частичного обновления оценки.
            user: Пользователь, выполняющий обновление.
            team: Команда, в контексте которой обновляется оценка.
            task: Задача, к которой относится оценка.
            evaluation: Оценка, которую нужно обновить.

        Возвращает:
            TaskRate: Обновленная оценка. Если изменений нет, возвращает
                переданную evaluation без обращения к репозиторию.

        Исключения:
            AuthorizationError: Если пользователь не MANAGER/MEMBER, не состоит
                в команде или задача не принадлежит команде (см. _ensure_access).

        Требования:
            Пользователь должен быть MANAGER или MEMBER.
            Пользователь должен состоять в команде team.
            task должен принадлежать team.

        Побочные эффекты:
            При наличии изменений обновляет запись в репозитории.
        """
        
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")
        if user.role not in (RoleEnum.MANAGER):
            raise AuthorizationError(message="You are not allowed to do that.")
        if task.team_id != team.id:
            raise AuthorizationError(message="You are not allowed to do that.")
        if evaluation.task_id != task.id:
            raise AuthorizationError(message="You are not allowed to do that.")
        
        changes = data.model_dump(exclude_unset=True)

        if not changes:
            return evaluation

        changed_evaluation = await self.evaluation_repo.update(evaluation.id, changes)
        await self.session.commit()
        return changed_evaluation

    
    async def delete(self, user: User, team: Team, task: Task, evaluation: TaskRate):
        """
        Удаляет оценку.

        Аргументы:
            user: Пользователь, выполняющий удаление.
            team: Команда, в контексте которой удаляется оценка.
            task: Задача, к которой относится оценка.
            evaluation: Оценка, которую нужно удалить.

        Возвращает:
            OperationSuccess: Результат успешной операции.

        Исключения:
            AuthorizationError: Если пользователь не MANAGER/MEMBER, не состоит
                в команде или задача не принадлежит команде (см. _ensure_access).

        Требования:
            Пользователь должен быть MANAGER или MEMBER.
            Пользователь должен состоять в команде team.
            task должен принадлежать team.

        Побочные эффекты:
            Удаляет запись из репозитория.
        """
        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")
        if user.role not in (RoleEnum.MANAGER):
            raise AuthorizationError(message="You are not allowed to do that.")
        if task.team_id != team.id:
            raise AuthorizationError(message="You are not allowed to do that.")
        if evaluation.task_id != task.id:
            raise AuthorizationError(message="You are not allowed to do that.")
        
        await self.evaluation_repo.delete(evaluation)
        await self.session.commit()
        return OperationSuccess()