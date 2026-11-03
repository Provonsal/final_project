import datetime
from uuid import UUID, uuid4
import uuid

from sqlalchemy import select, update


from app.repositories.crud_protocol import BaseRepo
from app.models import RefreshToken
from sqlalchemy.ext.asyncio import AsyncSession

from utils.token_manager import TKNManager


class RefreshTokenRepo(BaseRepo[RefreshToken]):

    model = RefreshToken

    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_hash(self, hash: str):
        return (await self.session.scalars(select(RefreshToken).where(RefreshToken.token_hash == TKNManager.hash_token(hash)))).one()

    async def update_revoke_all_else_for_user(self, user_id: uuid.UUID):
        await self.session.execute(update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True))
    
    async def update_revoke_all_family(self, family: UUID):
        await self.session.execute(update(RefreshToken).where(RefreshToken.family_id == family).values(revoked=True))