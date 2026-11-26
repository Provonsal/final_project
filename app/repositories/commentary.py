from datetime import UTC, datetime, timedelta
from typing import Sequence
from uuid import uuid4
import uuid

from sqlalchemy import select


from app.models.RoleEnum import RoleEnum
from app.models.models import Comment
from app.repositories.crud_protocol import BaseRepo
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession


class CommentRepo(BaseRepo[Comment]):
    """
    Репозиторий для управления комментариями к задачам.

    Provides CRUD operations for comments on tasks.
    """

    model = Comment

    async def get_comments_by_task(self, task_id: uuid.UUID) -> Sequence[Comment]:
        """
        Получить все комментарии для задачи.

        Args:
            task_id: Идентификатор задачи

        Returns:
            list[Comment]: Список комментариев к задаче
        """
        return (
            await self.session.scalars(
                select(
                    self.model
                ).where(
                    self.model.task_id == task_id
                )
            )
        ).all()


