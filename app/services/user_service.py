import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from app.exc.exceptions import WrongInputError
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
        """
        Регистрирует нового пользователя.

        Аргументы:
            user: Данные для регистрации (username, name, password, role).

        Возвращает:
            UserResponse: Ответ с логином, сообщением об успешной регистрации
                и ролью созданного пользователя.

        Исключения:
            WrongInputError: Если пользователь с таким логином уже существует.

        Требования:
            Логин (user.username) должен быть уникальным.

        Поведение:
            Если роль не передана (user.role is None), назначается RoleEnum.GUEST.
            Для пароля генерируются соль и хеш через PWDManager.
            Создаются записи User и UserCredentials.

        Побочные эффекты:
            Создает пользователя и его учетные данные, выполняет commit сессии.
        """

        try:
            await self.user_repo.get_by_login(user.username)
            raise WrongInputError(message="User with this login already exists")
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
        """
        Возвращает профиль текущего пользователя.

        Аргументы:
            current_user: Аутентифицированный пользователь.

        Возвращает:
            UserMeResponse: Данные текущего пользователя (id, username, role).
        """
        
        return UserMeResponse(id=current_user.id,username=current_user.email, role=current_user.role.value)

    async def get_user(self, user_id: UUID):
        """
        Возвращает пользователя по его идентификатору.

        Аргументы:
            user_id: UUID пользователя.

        Возвращает:
            User: Найденный пользователь, полученный из UserRepo.get_by_id.

        Исключения:
            NoResultFound: Если пользователь с указанным ID не найден
                (пробрасывается из репозитория).
        """

        return await self.user_repo.get_by_id(user_id)
        
