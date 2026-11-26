from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import NoResultFound

from app.exc.exceptions import WrongInputError, AuthorizationError
from app.models import RoleEnum
from app.schemas.refresh_token import RefreshTokenSchema
from app.schemas.response_token import ResponseToken

from app.services.auth import AuthService
SERVICE_MODULE = "app.services.auth"


# ==================== ХЕЛПЕРЫ ====================

def make_user(role: RoleEnum = RoleEnum.MEMBER, is_active: bool = True):
    """Лёгкая заглушка User без БД (duck typing вместо ORM)."""
    return SimpleNamespace(
        id=uuid4(),
        email="user@example.com",
        name="Test User",
        role=role,
        is_active=is_active,
        user_credentials=SimpleNamespace(
            salt=b"0123456789abcdef",
            password_hash=b"h" * 32,
        ),
    )


def make_form_data(username="user@example.com", password="password123"):
    """Заглушка OAuth2PasswordRequestForm — сервису нужны только .username/.password"""
    return SimpleNamespace(username=username, password=password)


def future_ts(days=7) -> int:
    return int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp())


def past_ts(days=1) -> int:
    return int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())


# ==================== ФИКСТУРЫ ====================

@pytest.fixture
def session():
    """Мок AsyncSession — нужен только .commit()"""
    s = MagicMock()
    s.commit = AsyncMock()
    return s


@pytest.fixture
def repos():
    """Подменяем классы репозиториев ВНУТРИ модуля сервиса."""
    with patch(f"{SERVICE_MODULE}.UserRepo") as user_cls, \
         patch(f"{SERVICE_MODULE}.RefreshTokenRepo") as refresh_cls:

        user_repo = user_cls.return_value
        user_repo.get_by_login = AsyncMock()
        user_repo.get_by_id = AsyncMock()
        user_repo.are_user_in_any_group = AsyncMock(return_value=False)
        user_repo.change_role = AsyncMock()

        refresh_repo = refresh_cls.return_value
        refresh_repo.create = AsyncMock()
        refresh_repo.update = AsyncMock()
        refresh_repo.get_by_hash = AsyncMock()
        refresh_repo.update_revoke_all_else_for_user = AsyncMock()
        refresh_repo.update_revoke_all_family = AsyncMock()

        yield SimpleNamespace(user=user_repo, refresh=refresh_repo)


@pytest.fixture
def service(session, repos):
    """AuthService с замоканными репозиториями."""
    return AuthService(session)


@pytest.fixture
def user():
    return make_user()


@pytest.fixture
def pwd_manager():
    m = MagicMock()
    m.verify_password.return_value = True
    return m


@pytest.fixture
def tkn_manager():
    m = MagicMock()
    m.create_access_token.return_value = "access.token"
    m.create_refresh_token.return_value = "refresh.token"
    m.hash_token.side_effect = lambda token: f"hash::{token}"
    m.decode_token.return_value = {
        "tid": str(uuid4()),
        "sub": str(uuid4()),
        "type": "refresh",
        "exp": future_ts(),
    }
    return m


@pytest.fixture
def refresh_payload(user):
    """Валидный payload входящего refresh-токена."""
    return {
        "sub": str(user.id),
        "type": "refresh",
        "tid": str(uuid4()),
        "exp": future_ts(),
    }


@pytest.fixture
def db_token():
    """Запись refresh-токена в БД."""
    return SimpleNamespace(
        id=uuid4(),
        revoked=False,
        family_id=uuid4(),
        user_id=uuid4(),
    )


# ==================== LOGIN ====================

class TestLogin:

    @pytest.mark.asyncio
    async def test_login_success_returns_tokens(self, service, repos, user, pwd_manager, tkn_manager, session):
        """Успешный логин возвращает ResponseToken с обоими токенами."""
        repos.user.get_by_login.return_value = user

        result = await service.login(make_form_data(), pwd_manager, tkn_manager)

        assert isinstance(result, ResponseToken)
        assert result.access_token == "access.token"
        assert result.refresh_token == "refresh.token"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_login_verifies_password_with_salt_and_hash(self, service, repos, user, pwd_manager, tkn_manager):
        """verify_password вызывается с паролем, солью и хешем из user_credentials."""
        repos.user.get_by_login.return_value = user

        await service.login(make_form_data(password="secret"), pwd_manager, tkn_manager)

        pwd_manager.verify_password.assert_called_once_with(
            "secret",
            user.user_credentials.salt,
            user.user_credentials.password_hash,
        )

    @pytest.mark.asyncio
    async def test_login_access_token_payload(self, service, repos, user, pwd_manager, tkn_manager):
        """В access-токен кладутся sub=str(user.id) и role=role.NAME (не .value!)."""
        repos.user.get_by_login.return_value = user

        await service.login(make_form_data(), pwd_manager, tkn_manager)

        tkn_manager.create_access_token.assert_called_once_with(
            data={"sub": str(user.id), "role": user.role.name}
        )

    @pytest.mark.asyncio
    async def test_login_revokes_previous_tokens_before_creating_new(self, service, repos, user, pwd_manager, tkn_manager):
        """Все старые refresh-токены отзываются, новый сохраняется."""
        repos.user.get_by_login.return_value = user

        await service.login(make_form_data(), pwd_manager, tkn_manager)

        repos.refresh.update_revoke_all_else_for_user.assert_awaited_once_with(user.id)
        repos.refresh.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_login_stores_hashed_token_not_raw(self, service, repos, user, pwd_manager, tkn_manager):
        """В БД сохраняется хеш токена, а не сам токен; id берётся из tid."""
        repos.user.get_by_login.return_value = user
        tid = str(uuid4())
        tkn_manager.decode_token.return_value = {"tid": tid, "exp": future_ts()}

        await service.login(make_form_data(), pwd_manager, tkn_manager)

        saved = repos.refresh.create.await_args.args[0]
        assert saved.id == tid
        assert saved.user_id == user.id
        assert saved.revoked is False
        assert saved.token_hash == "hash::refresh.token"
        assert saved.token_hash != "refresh.token"

    @pytest.mark.asyncio
    async def test_login_user_not_found_raises_wrong_input(self, service, repos, pwd_manager, tkn_manager, session):
        """NoResultFound из репо → WrongInputError, токены не создаются."""
        repos.user.get_by_login.side_effect = NoResultFound()

        with pytest.raises(WrongInputError) as exc:
            await service.login(make_form_data(), pwd_manager, tkn_manager)

        assert exc.value.status_code == 400
        assert exc.value.error_code == "BAD_REQUEST"
        tkn_manager.create_access_token.assert_not_called()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises_wrong_input(self, service, repos, user, pwd_manager, tkn_manager, session):
        """Неверный пароль → WrongInputError, токенов и коммита."""
        repos.user.get_by_login.return_value = user
        pwd_manager.verify_password.return_value = False

        with pytest.raises(WrongInputError):
            await service.login(make_form_data(password="wrong"), pwd_manager, tkn_manager)

        tkn_manager.create_access_token.assert_not_called()
        tkn_manager.create_refresh_token.assert_not_called()
        repos.refresh.create.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_login_same_error_message_for_unknown_user_and_bad_password(self, service, repos, user, pwd_manager, tkn_manager):
        """Безопасность: одинаковое сообщение — нельзя перебором узнать существующие email."""
        repos.user.get_by_login.side_effect = NoResultFound()
        with pytest.raises(WrongInputError) as exc_unknown:
            await service.login(make_form_data(), pwd_manager, tkn_manager)

        repos.user.get_by_login.side_effect = None
        repos.user.get_by_login.return_value = user
        pwd_manager.verify_password.return_value = False
        with pytest.raises(WrongInputError) as exc_bad_pwd:
            await service.login(make_form_data(), pwd_manager, tkn_manager)

        assert exc_unknown.value.message == exc_bad_pwd.value.message

    @pytest.mark.asyncio
    async def test_login_guest_without_team_promoted_to_auth(self, service, repos, pwd_manager, tkn_manager):
        """GUEST без команд → роль меняется на AUTH."""
        guest = make_user(role=RoleEnum.GUEST)
        repos.user.get_by_login.return_value = guest
        repos.user.are_user_in_any_group.return_value = False

        await service.login(make_form_data(), pwd_manager, tkn_manager)

        repos.user.change_role.assert_awaited_once_with(guest.id, RoleEnum.AUTH)

    @pytest.mark.asyncio
    async def test_login_guest_with_team_keeps_role(self, service, repos, pwd_manager, tkn_manager):
        """GUEST уже в команде → роль не меняется."""
        guest = make_user(role=RoleEnum.GUEST)
        repos.user.get_by_login.return_value = guest
        repos.user.are_user_in_any_group.return_value = True

        await service.login(make_form_data(), pwd_manager, tkn_manager)

        repos.user.change_role.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("role", [RoleEnum.MEMBER, RoleEnum.MANAGER, RoleEnum.AUTH])
    async def test_login_non_guest_role_untouched(self, service, repos, pwd_manager, tkn_manager, role):
        """Не-GUEST роли не трогаем и лишний запрос в БД не делаем."""
        u = make_user(role=role)
        repos.user.get_by_login.return_value = u

        await service.login(make_form_data(), pwd_manager, tkn_manager)

        repos.user.are_user_in_any_group.assert_not_awaited()
        repos.user.change_role.assert_not_awaited()


# ==================== REFRESH ====================

class TestRefresh:

    @pytest.mark.asyncio
    async def test_refresh_success_rotates_tokens(self, service, repos, user, db_token, refresh_payload, tkn_manager, session):
        """Успешный refresh: старый токен отозван, новый создан в той же family, БД закоммичена."""
        repos.user.get_by_id.return_value = user
        repos.refresh.get_by_hash.return_value = db_token
        new_tid = str(uuid4())
        tkn_manager.decode_token.side_effect = [
            refresh_payload,
            {"tid": new_tid, "exp": future_ts()},
        ]

        result = await service.refresh(RefreshTokenSchema(refresh_token="old.token"), tkn_manager)

        assert isinstance(result, ResponseToken)
        assert result.access_token == "access.token"
        assert result.refresh_token == "refresh.token"

        # Искали именно по хешу входящего токена
        repos.refresh.get_by_hash.assert_awaited_once_with("hash::old.token")
        # Старый отозван через update
        repos.refresh.update.assert_awaited_once_with(db_token.id, {"revoked": True})
        # Новый сохранён в той же семье
        created = repos.refresh.create.await_args.args[0]
        assert created.id == new_tid
        assert created.family_id == db_token.family_id
        assert created.revoked is False
        assert created.token_hash == "hash::refresh.token"
        # Коммит вызван
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_refresh_new_access_token_contains_user_id_and_role(self, service, repos, user, db_token, refresh_payload, tkn_manager):
        """В новый access-токен попадает актуальная роль пользователя из БД."""
        user.role = RoleEnum.MANAGER
        repos.user.get_by_id.return_value = user
        repos.refresh.get_by_hash.return_value = db_token
        tkn_manager.decode_token.side_effect = [refresh_payload, {"tid": str(uuid4()), "exp": future_ts()}]

        await service.refresh(RefreshTokenSchema(refresh_token="old.token"), tkn_manager)

        tkn_manager.create_access_token.assert_called_once_with(
            data={"sub": str(user.id), "role": "MANAGER"}
        )

    @pytest.mark.asyncio
    async def test_refresh_wrong_token_type_rejected(self, service, repos, user, refresh_payload, tkn_manager):
        """Access-токен нельзя использовать как refresh."""
        refresh_payload["type"] = "access"
        tkn_manager.decode_token.return_value = refresh_payload
        repos.user.get_by_id.return_value = user

        with pytest.raises(WrongInputError) as exc:
            await service.refresh(RefreshTokenSchema(refresh_token="old.token"), tkn_manager)

        assert exc.value.status_code == 400
        assert exc.value.error_code == "BAD_REQUEST"
        repos.refresh.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_refresh_payload_without_sub_rejected(self, service, refresh_payload, tkn_manager, repos):
        """Нет sub → отказ, к БД за юзером не ходим."""
        refresh_payload.pop("sub")
        tkn_manager.decode_token.return_value = refresh_payload

        with pytest.raises(WrongInputError):
            await service.refresh(RefreshTokenSchema(refresh_token="old.token"), tkn_manager)

        repos.user.get_by_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_refresh_payload_without_exp_rejected(self, service, repos, user, refresh_payload, tkn_manager):
        """Нет exp → отказ."""
        refresh_payload.pop("exp")
        tkn_manager.decode_token.return_value = refresh_payload
        repos.user.get_by_id.return_value = user

        with pytest.raises(WrongInputError):
            await service.refresh(RefreshTokenSchema(refresh_token="old.token"), tkn_manager)

        repos.refresh.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_refresh_user_not_found_rejected(self, service, repos, refresh_payload, tkn_manager):
        """Юзер из токена не найден → отказ."""
        tkn_manager.decode_token.return_value = refresh_payload
        repos.user.get_by_id.side_effect = NoResultFound()

        with pytest.raises(WrongInputError) as exc:
            await service.refresh(RefreshTokenSchema(refresh_token="old.token"), tkn_manager)

        assert exc.value.status_code == 400
        assert "User not found" in exc.value.message

    @pytest.mark.asyncio
    async def test_refresh_inactive_user_rejected(self, service, repos, refresh_payload, tkn_manager):
        """Неактивный юзер не может обновить токен."""
        repos.user.get_by_id.return_value = make_user(is_active=False)
        tkn_manager.decode_token.return_value = refresh_payload

        with pytest.raises(WrongInputError) as exc:
            await service.refresh(RefreshTokenSchema(refresh_token="old.token"), tkn_manager)

        assert "not active" in exc.value.message.lower()
        repos.refresh.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_refresh_expired_token_raises_authorization_error(self, service, repos, user, refresh_payload, tkn_manager):
        """Истёкший refresh → AuthorizationError (403), а не WrongInputError."""
        refresh_payload["exp"] = past_ts()
        tkn_manager.decode_token.return_value = refresh_payload
        repos.user.get_by_id.return_value = user

        with pytest.raises(AuthorizationError) as exc:
            await service.refresh(RefreshTokenSchema(refresh_token="old.token"), tkn_manager)

        assert exc.value.status_code == 403
        assert exc.value.error_code == "FORBIDDEN"
        assert "expired" in exc.value.message.lower()
        repos.refresh.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_refresh_token_not_in_db_rejected(self, service, repos, user, refresh_payload, tkn_manager):
        """Токен валиден по подписи, но его нет в БД → отказ."""
        tkn_manager.decode_token.return_value = refresh_payload
        repos.user.get_by_id.return_value = user
        repos.refresh.get_by_hash.side_effect = NoResultFound()

        with pytest.raises(WrongInputError) as exc:
            await service.refresh(RefreshTokenSchema(refresh_token="old.token"), tkn_manager)

        assert exc.value.status_code == 400
        assert "Invalid refresh token" in exc.value.message

    @pytest.mark.asyncio
    async def test_refresh_revoked_token_kills_whole_family(self, service, repos, user, db_token, refresh_payload, tkn_manager):
        """Переиспользование отозванного токена → AuthorizationError + отзыв всей семьи (reuse detection)."""
        db_token.revoked = True
        tkn_manager.decode_token.return_value = refresh_payload
        repos.user.get_by_id.return_value = user
        repos.refresh.get_by_hash.return_value = db_token

        with pytest.raises(AuthorizationError) as exc:
            await service.refresh(RefreshTokenSchema(refresh_token="old.token"), tkn_manager)

        assert exc.value.status_code == 403
        assert exc.value.error_code == "FORBIDDEN"
        repos.refresh.update_revoke_all_family.assert_awaited_once_with(db_token.family_id)
        repos.refresh.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_refresh_decode_error_rejected(self, service, tkn_manager, repos):
        """Битая подпись / мусорный токен → отказ, а не 500."""
        tkn_manager.decode_token.side_effect = ValueError("bad token")

        with pytest.raises(Exception):
            await service.refresh(RefreshTokenSchema(refresh_token="garbage"), tkn_manager)

        repos.refresh.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_refresh_preserves_family_id_across_rotations(self, service, repos, user, db_token, refresh_payload, tkn_manager):
        """family_id сохраняется при ротации — это нужно для reuse-detection."""
        original_family = db_token.family_id
        repos.user.get_by_id.return_value = user
        repos.refresh.get_by_hash.return_value = db_token
        tkn_manager.decode_token.side_effect = [
            refresh_payload,
            {"tid": str(uuid4()), "exp": future_ts()},
        ]

        await service.refresh(RefreshTokenSchema(refresh_token="old.token"), tkn_manager)

        new_token = repos.refresh.create.await_args.args[0]
        assert new_token.family_id == original_family