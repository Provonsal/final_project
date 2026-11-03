from typing import Generic, Protocol, TypeVar
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base, BaseModel


ModelT = TypeVar("ModelT", bound=BaseModel)

class BaseRepo(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> ModelT:
        return (await self.session.scalars(
            select(self.model).where(self.model.id == id)
        )).one()

    async def update(self, id: UUID, data: dict) -> ModelT:
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**data)
            .returning(self.model)
        )
        return (await self.session.scalars(stmt)).one()

    async def create(self, model_obj: ModelT) -> None: 
            
        self.session.add(model_obj)
        await self.session.flush()
    
    async def delete(self, model_obj: ModelT) -> None:
        await self.session.delete(model_obj)