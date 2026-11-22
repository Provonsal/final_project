from uuid import uuid4
import uuid

from sqlalchemy import select


from app.models.RoleEnum import RoleEnum
from app.repositories.crud_protocol import BaseRepo
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class UserRepo(BaseRepo[User]):
    """
    Репозиторий для операций с пользователями.

    Предоставляет методы для получения пользователей, изменения ролей и проверки участия в группах.
    """

    model = User

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория пользователей.

        Args:
            session (AsyncSession): Асинхронная сессия базы данных
        """
        self.session = session

    async def get_by_login(self, login: str):
        """
        Получает пользователя по логину (email).

        Args:
            login (str): Email пользователя

        Returns:
            User: Найденный пользователь с загрузкой учетных данных

        Raises:
            NoResultFound: Если пользователь не найден

        Example:
            >>> repo = UserRepo(session)
            >>> user = await repo.get_by_login("user@example.com")
        """
        stmt = (
            select(self.model)
            .where(self.model.email == login)
            .options(selectinload(self.model.user_credentials))
        )
        return (await self.session.scalars(stmt)).one()

    async def get_users(self):
        """
        Получает список пользователей, не являющихся менеджерами.

        Returns:
            list[User]: Список всех пользователей, кроме менеджеров

        Example:
            >>> repo = UserRepo(session)
            >>> users = await repo.get_users()
        """
        return (
            await self.session.scalars(
                select(self.model).where(self.model.role != RoleEnum.MANAGER)
            )
        ).all()

    async def change_role(self, user_id: uuid.UUID, new_role: RoleEnum):
        """
        Изменяет роль пользователя.

        Args:
            user_id (uuid.UUID): Идентификатор пользователя
            new_role (RoleEnum): Новая роль пользователя

        Побочные эффекты:
            Обновляет роль пользователя в базе данных

        Example:
            >>> repo = UserRepo(session)
            >>> await repo.change_role(user_uuid, RoleEnum.MEMBER)
        """
        user = await self.get_by_id(user_id)
        user.role = new_role
        await self.session.flush()

    async def create_creds(self, user_creds_model_obj) -> None:
        """
        Создает учетные данные пользователя в базе данных.

        Args:
            user_creds_model_obj: Объект UserCredentials для создания

        Побочные эффекты:
            Добавляет объект в сессию и делает flush для генерации ID

        Example:
            >>> repo = UserRepo(session)
            >>> creds = UserCredentials(user_id=user_uuid, salt=salt, password_hash=hash)
            >>> await repo.create_creds(creds)
        """
        self.session.add(user_creds_model_obj)
        await self.session.flush()

    async def are_user_in_any_group(self, user_id: uuid.UUID) -> bool:
        """
        Проверяет, состоит ли пользователь в какой-либо команде.

        Args:
            user_id (uuid.UUID): Идентификатор пользователя

        Returns:
            bool: True, если пользователь состоит в хотя бы одной команде, иначе False

        Example:
            >>> repo = UserRepo(session)
            >>> is_member = await repo.are_user_in_any_group(user_uuid)
        """
        stmt = (
            select(self.model)
            .where(self.model.id == user_id)
            .options(selectinload(self.model.mtm_teams_users))
        )
        user = (await self.session.scalars(stmt)).one()
        return len(user.mtm_teams_users) > 0





