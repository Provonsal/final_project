import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from app.models.RoleEnum import RoleEnum
from app.models.models import User, UserCredentials

from app.repositories.refresh_token import RefreshTokenRepo
from app.repositories.user import UserRepo

from app.schemas.user_me import UserMeResponse
from app.schemas.user_register import UserRegister
from app.schemas.user_response import UserResponse

from utils.password_manager import PWDManager


class UserService:
    """Бизнес-логика для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepo(session)

    async def register(self, user: UserRegister):
        try:
            await self.user_repo.get_by_login(user.username)
            raise HTTPException(status_code=400, detail="User with this email already exists")
        except NoResultFound:
            pass

        role = RoleEnum.GUEST if user.role is None else user.role

        salt, hash_pwd = PWDManager.create_credentials(user.password)
                
        new_user = User(
            email=user.username,
            name=user.name,
            role=role
        )

        new_user_creds = UserCredentials(
            user=new_user,
            salt=salt,
            password_hash=hash_pwd
        )

        await self.user_repo.create(new_user)
        await self.user_repo.create_creds(new_user_creds)
        await self.session.commit()

        return UserResponse(
            login=user.username,
            message="Регистрация успешна",
            role=role.value
        )
        

    async def me(self, current_user: User):
        
        return UserMeResponse(id=current_user.id,username=current_user.email, role=current_user.role.value)

    async def get_user(self, user_id: UUID):
        return await self.user_repo.get_by_id(user_id)
        

    async def get_users(self, skip: int = 0, limit: int = 100):
        ...