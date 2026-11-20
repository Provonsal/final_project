from uuid import UUID


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from app.exc.exceptions import WrongInputError
from app.models.RoleEnum import RoleEnum
from app.models.models import User, UserCredentials

from app.repositories.user import UserRepo

from app.schemas.response_user_me import ResponseUserMe
from app.schemas.register_user import UserRegister
from app.schemas.response_register_user import ResponseUser

from utils.password_manager import PWDManager


class UserService:
    """Бизнес-логика для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepo(session)

    async def register(self, user: UserRegister, pwd_manager: PWDManager):
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

        salt, hash_pwd = pwd_manager.create_credentials(user.password)
                
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

        return new_user
        

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
        
