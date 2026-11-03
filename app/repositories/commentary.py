from datetime import UTC, datetime, timedelta
from uuid import uuid4
import uuid

from sqlalchemy import select


from app.models.RoleEnum import RoleEnum
from app.models.models import Comment
from app.repositories.crud_protocol import BaseRepo
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession



class CommentRepo(BaseRepo[Comment]):

    model=Comment

    async def get_comments_by_task(
        self,
        task_id: uuid.UUID
    ):
        return (
            await self.session.scalars(
                select(
                    self.model
                ).where(
                    self.model.task_id == task_id
                )
            )
        )


