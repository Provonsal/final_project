from typing import Generic, Protocol, TypeVar
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base, BaseModel


ModelT = TypeVar("ModelT", bound=BaseModel)

class BaseRepo(Generic[ModelT]):
    """
    Базовый репозиторий для выполнения CRUD операций.

    Содержит общие методы для работы с моделями данных:
    - Получение записи по ID
    - Обновление существующей записи
    - Создание новой записи
    - Удаление записи
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория.

        Args:
            session (AsyncSession): Асинхронная сессия базы данных
        """
        self.session = session

    async def get_by_id(self, id: UUID) -> ModelT:
        """
        Получает запись модели по ID.

        Args:
            id (uuid.UUID): Уникальный идентификатор записи

        Returns:
            ModelT: Найденная модель

        Raises:
            NoResultFound: Если запись не найдена

        Example:
            >>> repo = TaskRepo(session)
            >>> task = await repo.get_by_id(task_id)
        """
        return (await self.session.scalars(
            select(self.model).where(self.model.id == id)
        )).one()

    async def update(self, id: UUID, data: dict) -> ModelT:
        """
        Обновляет запись модели по ID.

        Args:
            id (uuid.UUID): Уникальный идентификатор записи
            data (dict): Словарь с обновляемыми полями

        Returns:
            ModelT: Обновленная модель

        Example:
            >>> repo = TaskRepo(session)
            >>> updated_task = await repo.update(task_id, {"status": "done"})
        """
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**data)
            .returning(self.model)
        )
        return (await self.session.scalars(stmt)).one()

    async def create(self, model_obj: ModelT) -> None:
        """
        Создает новую запись модели в базе данных.

        Args:
            model_obj (ModelT): Объект модели для создания

        Побочные эффекты:
            Добавляет объект в сессию и делает flush для генерации ID

        Example:
            >>> repo = TaskRepo(session)
            >>> task = Task(title="New task")
            >>> await repo.create(task)
        """
        self.session.add(model_obj)
        await self.session.flush()

    async def delete(self, model_obj: ModelT) -> None:
        """
        Удаляет запись модели из базы данных.

        Args:
            model_obj (ModelT): Объект модели для удаления

        Побочные эффекты:
            Удаляет объект из сессии

        Example:
            >>> repo = TaskRepo(session)
            >>> await repo.delete(task)
        """
        await self.session.delete(model_obj)