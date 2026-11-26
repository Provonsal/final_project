import datetime
from uuid import UUID, uuid4
import uuid

from sqlalchemy import select, update


from app.repositories.crud_protocol import BaseRepo
from app.models import RefreshToken
from sqlalchemy.ext.asyncio import AsyncSession

from utils.token_manager import TKNManager


class RefreshTokenRepo(BaseRepo[RefreshToken]):
    """
    Репозиторий для управления refresh-токенами.

    Provides methods for managing refresh tokens including revoking tokens.
    """

    model = RefreshToken

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория refresh-токенов.

        Args:
            session: Асинхронная сессия базы данных
        """
        self.session = session

    async def get_by_hash(self, hash: bytes) -> RefreshToken:
        return (await self.session.scalars(select(RefreshToken).where(RefreshToken.token_hash == hash))).one()

    async def update_revoke_all_else_for_user(self, user_id: uuid.UUID) -> None:
        """
        Отозвать все токены пользователя, кроме указанного.

        Args:
            user_id: Идентификатор пользователя
        """
        await self.session.execute(update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True))
    
    async def update_revoke_all_family(self, family: UUID) -> None:
        """
        Отозвать все токены в семействе.

        Args:
            family: Идентификатор семейства токенов
        """
        await self.session.execute(update(RefreshToken).where(RefreshToken.family_id == family).values(revoked=True))