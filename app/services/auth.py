import datetime
from uuid import uuid4

from fastapi.security import OAuth2PasswordRequestForm


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from app.exc.exceptions import AuthorizationError, WrongInputError
from app.models import RoleEnum
from app.models.models import RefreshToken
from app.repositories.refresh_token import RefreshTokenRepo
from app.repositories.user import UserRepo
from app.schemas.refresh_token import RefreshTokenSchema
from app.schemas.response_token import ResponseToken
from app.schemas.update_refresh_token import UpdateRefreshToken
from utils.password_manager import PWDManager
from utils.token_manager import TKNManager



class AuthService:
    """Бизнес-логика для работы с аутентофикацией."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepo(session)
        self.refresh_repo = RefreshTokenRepo(session)

    async def login(self, form_data: OAuth2PasswordRequestForm, pwd_manager: PWDManager, tkn_manager: TKNManager):
        try:
            user = await self.user_repo.get_by_login(form_data.username)
        except NoResultFound:
            raise WrongInputError(message="Неверный email или пароль")

        is_correct_pwd = pwd_manager.verify_password(form_data.password, user.user_credentials.salt, user.user_credentials.password_hash)

        if is_correct_pwd:

            role = user.role

            access_token = tkn_manager.create_access_token(
                data={
                    "sub": str(user.id),
                    "role" : role.name
                },
            )
            
            refresh_token = tkn_manager.create_refresh_token(
                data={
                    "sub": str(user.id), 
                    "tid": str(uuid4())
                }
            )
            
            decoded_refresh_token = tkn_manager.decode_token(refresh_token)

            refresh_token_orm = RefreshToken(
                id = decoded_refresh_token.get("tid"),
                user_id = user.id,
                expire_date = decoded_refresh_token.get("exp"),
                revoked=False,
                token_hash = tkn_manager.hash_token(refresh_token),
            )

            await self.refresh_repo.update_revoke_all_else_for_user(user.id)
            await self.refresh_repo.create(refresh_token_orm)
            if role == RoleEnum.GUEST and (not await self.user_repo.are_user_in_any_group(user.id)):
                await self.user_repo.change_role(user.id, RoleEnum.AUTH)
            await self.session.commit()

            return ResponseToken(
                access_token=access_token,
                refresh_token=refresh_token
            )
        else:
            raise WrongInputError(message="Неверный email или пароль")

    async def refresh(self, refresh_data: RefreshTokenSchema, tkn_manager: TKNManager):
        try:
            payload = tkn_manager.decode_token(refresh_data.refresh_token)
            
            # Проверяем, что это refresh токен
            if payload.get("type") != "refresh":
                raise WrongInputError(
                    message="Invalid token type"
                )
            
            user_id = payload.get("sub")

            if user_id is None:
                raise WrongInputError(
                    message="Invalid token"
                )
            
            try:
                user = await self.user_repo.get_by_id(user_id)
            except:
                raise WrongInputError(
                    message="User not found"
                )

            if not user.is_active:
                raise WrongInputError(
                    message="User is not active"
                )
            
            expire_time = payload.get("exp")

            if expire_time is not None:
                if datetime.datetime.fromtimestamp(expire_time, datetime.UTC) < datetime.datetime.now(datetime.UTC):
                    raise AuthorizationError(
                        message="Token expired. Log in again please"
                    )
            else:
                raise WrongInputError(
                    message="Invalid token"
                )

            try:
                
                ref_db_token = await self.refresh_repo.get_by_hash(tkn_manager.hash_token(refresh_data.refresh_token))

            except:
                raise WrongInputError(
                    message="Invalid refresh token"
                )

            if ref_db_token.revoked:
                
                await self.refresh_repo.update_revoke_all_family(ref_db_token.family_id)

                raise AuthorizationError(
                    message="Revoked token. Log in again please."
                )

            role = user.role

            access_token = tkn_manager.create_access_token(data={"sub": str(user.id), "role" : role.name})
            refresh_token = tkn_manager.create_refresh_token(data={"sub": str(user.id), "tid": str(uuid4())})

            decoded_refresh_token = tkn_manager.decode_token(refresh_token)

            ref_db_token.revoked = True

            changes_schema = UpdateRefreshToken(
                revoked=True
            )

            changes = changes_schema.model_dump(exclude_unset=True)

            await self.refresh_repo.update(ref_db_token.id, changes)

            new_refresh_token_db = RefreshToken(
                id = decoded_refresh_token.get("tid"),
                user_id = user_id,
                created_at = datetime.datetime.now(datetime.UTC),
                expire_date = decoded_refresh_token.get("exp"),
                revoked=False,
                token_hash = tkn_manager.hash_token(refresh_token),
                family_id = ref_db_token.family_id
            )

            await self.refresh_repo.create(new_refresh_token_db)

            return ResponseToken(
                access_token=access_token,
                refresh_token=refresh_token
            )
            

        except Exception:
            raise WrongInputError(
                message="Invalid refresh token"
            )