
from functools import wraps
from inspect import signature
from typing import Any, Callable
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.exc.exceptions import AuthorizationError, WrongInputError
from app.models import RoleEnum
from app.models.models import Comment, Task, Team, User
from app.repositories.commentary import CommentRepo
from app.repositories.team import TeamRepo
from app.schemas.create_comment import CommentCreate
from app.schemas.update_comment import CommentUpdate
from app.schemas.success import OperationSuccess



class CommentService:
    """Бизнес-логика для работы с комментариями."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.comment_repo = CommentRepo(session)
        self.team_repo = TeamRepo(session)
      
    async def get_comments(self, task: Task, user: User, team: Team):
        """
        Возвращает все комментарии задачи.

        Аргументы:
            task: Задача, комментарии которой запрашиваются.
            user: Пользователь, выполняющий запрос.
            team: Команда, в контексте которой запрашиваются комментарии.

        Возвращает:
            list[Comment]: Комментарии указанной задачи.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если задача не относится к указанной команде.

        Требования:
            Пользователь должен состоять в команде team.
            Задача должна принадлежать команде team (task.team_id == team.id).
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")
        if task.team_id != team.id:
            raise WrongInputError("Task does not belong to the specified team.")
        

        return await self.comment_repo.get_comments_by_task(task.id)

    
    async def get_comment(self, comment: Comment, task: Task, user: User, team: Team):
        """
        Возвращает комментарий после проверок доступа.

        Аргументы:
            comment: Комментарий, который нужно получить.
            task: Задача, к которой должен относиться комментарий.
            user: Пользователь, выполняющий запрос.
            team: Команда, в контексте которой запрашивается комментарий.

        Возвращает:
            Comment: Переданный комментарий без изменений.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если задача не относится к указанной команде.
            AuthorizationError: Если комментарий не относится к указанной задаче.

        Требования:
            Пользователь должен состоять в команде team.
            Задача должна принадлежать команде team (task.team_id == team.id).
            Комментарий должен принадлежать задаче task (comment.task_id == task.id).
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")
        if task.team_id != team.id:
            raise WrongInputError("Task does not belong to the specified team.")
        if comment.task_id != task.id:
            raise WrongInputError("Comment does not belong to the specified task.")
        
        return comment

    async def create_comment(self, data: CommentCreate, user: User, task: Task, team: Team):
        """
        Создает комментарий к задаче.

        Аргументы:
            data: Данные для создания комментария (тело комментария).
            user: Пользователь, создающий комментарий.
            task: Задача, к которой добавляется комментарий.
            team: Команда, в контексте которой создается комментарий.

        Возвращает:
            Comment: Созданный комментарий.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если задача не относится к указанной команде.

        Требования:
            Пользователь должен состоять в команде team.
            Задача должна принадлежать команде team (task.team_id == team.id).

        Поведение:
            Автор комментария (user) и задача (task) проставляются из
            аргументов метода, а не из тела запроса.

        Побочные эффекты:
            Создает комментарий и выполняет commit сессии.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")
        if task.team_id != team.id:
            raise WrongInputError("Task does not belong to the specified team.")

        new_comment = Comment(**data.model_dump(), user=user, task=task)
        await self.comment_repo.create(new_comment)
        await self.session.commit()
        return new_comment

     
    async def update(self, data: CommentUpdate, comment: Comment, task: Task, user: User, team: Team):
        """
        Частично обновляет комментарий.

        Аргументы:
            data: Данные для частичного обновления комментария.
            comment: Комментарий, который нужно обновить.
            task: Задача, в контексте которой выполняется обновление.
            user: Пользователь, выполняющий обновление.
            team: Команда, в контексте которой выполняется обновление.

        Возвращает:
            Comment: Обновленный комментарий. Если изменений нет, возвращает
                переданный comment без обращения к репозиторию.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если задача не относится к указанной команде.
            AuthorizationError: Если комментарий не относится к указанной задаче.
            AuthorizationError: Если пользователь не является автором комментария.

        Требования:
            Пользователь должен состоять в команде team.
            Задача должна принадлежать команде team (task.team_id == team.id).
            Комментарий должен принадлежать задаче task (comment.task_id == task.id).
            Пользователь должен быть автором комментария (comment.author == user.id).
            Роль MANAGER не дает права редактировать чужие комментарии.

        Побочные эффекты:
            При наличии изменений обновляет комментарий и выполняет commit сессии.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")
        if task.team_id != team.id:
            raise WrongInputError("Task does not belong to the specified team.")
        if comment.task_id != task.id:
            raise WrongInputError("Comment does not belong to the specified task.")
        if comment.author != user.id:
            raise WrongInputError("You are not allowed to do that.")
        
        changes = data.model_dump(exclude_unset=True)

        if not changes:
            return comment

        updated_comment = await self.comment_repo.update(comment.id, changes)
        await self.session.commit()

        return updated_comment

    
    async def delete(self, comment: Comment, task: Task, user: User, team: Team):
        """
        Удаляет комментарий.

        Аргументы:
            comment: Комментарий, который нужно удалить.
            task: Задача, в контексте которой выполняется удаление.
            user: Пользователь, выполняющий удаление.
            team: Команда, в контексте которой выполняется удаление.

        Возвращает:
            OperationSuccess: Результат успешной операции.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если задача не относится к указанной команде.
            AuthorizationError: Если комментарий не относится к указанной задаче.
            AuthorizationError: Если пользователь не является автором комментария
                и не имеет роль MANAGER.

        Требования:
            Пользователь должен состоять в команде team.
            Задача должна принадлежать команде team (task.team_id == team.id).
            Комментарий должен принадлежать задаче task (comment.task_id == task.id).
            Удалить комментарий может его автор либо пользователь с ролью MANAGER
            (модерация).

        Побочные эффекты:
            Удаляет комментарий и выполняет commit сессии.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")
        if task.team_id != team.id:
            raise WrongInputError("Task does not belong to the specified team.")
        if comment.task_id != task.id:
            raise WrongInputError("Comment does not belong to the specified task.")
        if comment.author != user.id and user.role != RoleEnum.MANAGER:
            raise WrongInputError("You are not allowed to do that.")

        await self.comment_repo.delete(comment)
        await self.session.commit()
        return OperationSuccess()