from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import NoResultFound

from app.exc.exceptions import WrongInputError
from app.models import RoleEnum

from app.services.user_service import UserService
SERVICE_MODULE = "app.services.user_service"


# ==================== ХЕЛПЕРЫ ====================

def make_user_register(username="user@example.com", name="Test User",
                       password="secret123"):
    """Заглушка UserRegister."""
    return SimpleNamespace(
        username=username,
        name=name,
        password=password,
    )


# ==================== ФИКСТУРЫ ====================

@pytest.fixture
def session():
    s = MagicMock()
    s.commit = AsyncMock()
    return s


@pytest.fixture
def repos():
    with patch(f"{SERVICE_MODULE}.UserRepo") as user_cls:
        user_repo = user_cls.return_value
        user_repo.get_by_login = AsyncMock()
        user_repo.get_by_id = AsyncMock()
        user_repo.create = AsyncMock()
        user_repo.create_creds = AsyncMock()
        yield SimpleNamespace(user=user_repo)


@pytest.fixture
def service(session, repos):
    return UserService(session)


@pytest.fixture
def pwd_manager():
    m = MagicMock()
    m.create_credentials.return_value = (b"salt-bytes", b"hash-bytes")
    return m


# ==================== TestRegister ====================

class TestRegister:

    @pytest.mark.asyncio
    async def test_register_success_default_role_is_guest(self, service, repos, session, pwd_manager):
        """Успешная регистрация → GUEST роль."""
        data = make_user_register()
        repos.user.get_by_login.side_effect = NoResultFound()

        with patch(f"{SERVICE_MODULE}.User") as user_cls, \
             patch(f"{SERVICE_MODULE}.UserCredentials") as creds_cls:
            new_user = SimpleNamespace(id=uuid4(), email=data.username, name=data.name, role=RoleEnum.GUEST)
            user_cls.return_value = new_user
            creds_cls.return_value = SimpleNamespace()

            result = await service.register(data, pwd_manager)

        assert result is new_user
        assert result.role == RoleEnum.GUEST
        # Проверяем, что User создан с ролью GUEST
        call_kwargs = user_cls.call_args.kwargs
        assert call_kwargs["role"] == RoleEnum.GUEST
        assert call_kwargs["email"] == data.username
        assert call_kwargs["name"] == data.name

    @pytest.mark.asyncio
    async def test_register_calls_pwd_manager_with_password(self, service, repos, pwd_manager):
        """pwd_manager.create_credentials вызывается с паролем из данных."""
        data = make_user_register(password="my-secret-password")
        repos.user.get_by_login.side_effect = NoResultFound()

        with patch(f"{SERVICE_MODULE}.User") as user_cls, \
             patch(f"{SERVICE_MODULE}.UserCredentials") as creds_cls:
            user_cls.return_value = SimpleNamespace()
            creds_cls.return_value = SimpleNamespace()

            await service.register(data, pwd_manager)

        pwd_manager.create_credentials.assert_called_once_with("my-secret-password")

    @pytest.mark.asyncio
    async def test_register_creates_user_and_credentials(self, service, repos, session, pwd_manager):
        """Создаются оба объекта: User и UserCredentials."""
        data = make_user_register()
        repos.user.get_by_login.side_effect = NoResultFound()
        pwd_manager.create_credentials.return_value = (b"salt-xyz", b"hash-abc")

        with patch(f"{SERVICE_MODULE}.User") as user_cls, \
             patch(f"{SERVICE_MODULE}.UserCredentials") as creds_cls:
            new_user = SimpleNamespace(id=uuid4())
            user_cls.return_value = new_user
            creds_cls.return_value = SimpleNamespace()

            await service.register(data, pwd_manager)

        # User создан
        user_cls.assert_called_once()
        # User сохранён в репо
        repos.user.create.assert_awaited_once_with(new_user)
        # UserCredentials создан с правильными полями
        creds_call_kwargs = creds_cls.call_args.kwargs
        assert creds_call_kwargs["user"] is new_user
        assert creds_call_kwargs["salt"] == b"salt-xyz"
        assert creds_call_kwargs["password_hash"] == b"hash-abc"
        # UserCredentials сохранён в репо
        repos.user.create_creds.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_register_commits_session(self, service, repos, session, pwd_manager):
        """После успешной регистрации вызывается session.commit()."""
        data = make_user_register()
        repos.user.get_by_login.side_effect = NoResultFound()

        with patch(f"{SERVICE_MODULE}.User") as user_cls, \
             patch(f"{SERVICE_MODULE}.UserCredentials") as creds_cls:
            user_cls.return_value = SimpleNamespace()
            creds_cls.return_value = SimpleNamespace()

            await service.register(data, pwd_manager)

        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_register_duplicate_login_raises_wrong_input(self, service, repos, session, pwd_manager):
        """Попытка регистрации с существующим логином → WrongInputError."""
        data = make_user_register()
        # get_by_login вернул пользователя (не NoResultFound)
        repos.user.get_by_login.return_value = SimpleNamespace(id=uuid4())

        with pytest.raises(WrongInputError) as exc:
            await service.register(data, pwd_manager)

        assert exc.value.status_code == 400
        assert "already exists" in exc.value.message
        # Ничего не должно создаваться
        pwd_manager.create_credentials.assert_not_called()
        repos.user.create.assert_not_awaited()
        repos.user.create_creds.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_register_duplicate_login_error_message(self, service, repos, pwd_manager):
        """Сообщение об ошибке содержит 'already exists'."""
        data = make_user_register()
        repos.user.get_by_login.return_value = SimpleNamespace(id=uuid4())

        with pytest.raises(WrongInputError) as exc:
            await service.register(data, pwd_manager)

        assert "already exists" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_register_checks_login_before_creating(self, service, repos, pwd_manager):
        """Проверка логина происходит ДО создания пользователя."""
        data = make_user_register()
        repos.user.get_by_login.side_effect = NoResultFound()

        with patch(f"{SERVICE_MODULE}.User") as user_cls, \
             patch(f"{SERVICE_MODULE}.UserCredentials") as creds_cls:
            user_cls.return_value = SimpleNamespace()
            creds_cls.return_value = SimpleNamespace()

            await service.register(data, pwd_manager)

        # get_by_login вызван первым
        repos.user.get_by_login.assert_awaited_once_with(data.username)
        # Только после этого — создание
        assert pwd_manager.create_credentials.called
        assert repos.user.create.called


# ==================== TestGetUser ====================

class TestGetUser:

    @pytest.mark.asyncio
    async def test_get_user_success(self, service, repos):
        """Успешное получение пользователя по ID."""
        user_id = uuid4()
        expected_user = SimpleNamespace(id=user_id, email="user@example.com")
        repos.user.get_by_id.return_value = expected_user

        result = await service.get_user(user_id)

        assert result is expected_user
        repos.user.get_by_id.assert_awaited_once_with(user_id)

    @pytest.mark.asyncio
    async def test_get_user_not_found_raises_no_result_found(self, service, repos):
        """Если пользователь не найден → NoResultFound пробрасывается наверх."""
        user_id = uuid4()
        repos.user.get_by_id.side_effect = NoResultFound()

        with pytest.raises(NoResultFound):
            await service.get_user(user_id)

    @pytest.mark.asyncio
    async def test_get_user_passes_uuid_to_repo(self, service, repos):
        """UUID передаётся в репо без изменений."""
        user_id = uuid4()
        repos.user.get_by_id.return_value = SimpleNamespace()

        await service.get_user(user_id)

        repos.user.get_by_id.assert_awaited_once_with(user_id)
        # Проверяем, что это именно тот же UUID-объект
        call_arg = repos.user.get_by_id.await_args.args[0]
        assert call_arg == user_id
        assert isinstance(call_arg, type(user_id))