



import uuid

from sqlalchemy import select

from app.models.models import TaskRate
from app.repositories.crud_protocol import BaseRepo



class EvaluationRepo(BaseRepo[TaskRate]):

    model=TaskRate

    async def get_evaluation_for_task(
        self,
        task_id: uuid.UUID
    ):
        return (await self.session.scalars
            (
                select(
                    self.model
                ).where(
                    self.model.task_id == task_id
                )
            )
        ).one()