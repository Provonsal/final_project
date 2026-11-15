import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.dependencies import (
    get_auth_service,
    get_calendar_service,
    get_comment,
    get_comment_service,
    get_current_user,
    get_evaluation,
    get_evaluation_service,
    get_meeting,
    get_meeting_service,
    get_session,
    get_task,
    get_task_service,
    get_team,
    get_team_service,
    get_user_service,
)
from app.main import app
from app.models import RoleEnum


# ---------- Фабрики мок-объектов ----------

def make_user(role: RoleEnum = RoleEnum.MEMBER, **overrides) -> SimpleNamespace:
    data = {
        "id": uuid.uuid4(),
        "email": f"{role.value}-{uuid.uuid4().hex[:6]}@example.com",
        "name": role.value.capitalize(),
        "role": role,
        "is_active": True,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_team(**overrides) -> SimpleNamespace:
    data = {"id": uuid.uuid4(), "name": "Team", "max_per_team": 10, "owner": uuid.uuid4()}
    data.update(overrides)
    return SimpleNamespace(**data)


def make_task(**overrides) -> SimpleNamespace:
    data = {
        "id": uuid.uuid4(),
        "title": "Task",
        "description": "Desc",
        "assignee": uuid.uuid4(),
        "due_date": "2026-01-01T00:00:00Z",
        "status": 1,
        "team_id": uuid.uuid4(),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_comment(**overrides) -> SimpleNamespace:
    data = {"id": uuid.uuid4(), "text": "Hi", "task_id": uuid.uuid4(), "author": uuid.uuid4()}
    data.update(overrides)
    return SimpleNamespace(**data)


def make_evaluation(**overrides) -> SimpleNamespace:
    data = {"id": uuid.uuid4(), "rate": 3, "task_id": uuid.uuid4(), "rater": uuid.uuid4()}
    data.update(overrides)
    return SimpleNamespace(**data)


def make_meeting(**overrides) -> SimpleNamespace:
    data = {
        "id": uuid.uuid4(),
        "starts_at": "2026-01-01T10:00:00Z",
        "ends_at": "2026-01-01T11:00:00Z",
        "max_members": 5,
        "related_team": uuid.uuid4(),
        "creator": uuid.uuid4(),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


# ---------- Карты callables для overrides ----------

SERVICES_MAP = {
    "user": get_user_service,
    "auth": get_auth_service,
    "team": get_team_service,
    "task": get_task_service,
    "meeting": get_meeting_service,
    "calendar": get_calendar_service,
    "comment": get_comment_service,
    "evaluation": get_evaluation_service,
}

OBJECTS_MAP = {
    "team": get_team,
    "task": get_task,
    "comment": get_comment,
    "evaluation": get_evaluation,
    "meeting": get_meeting,
}


# ---------- Автоизоляция ----------

@pytest_asyncio.fixture(autouse=True)
async def _isolate_overrides():
    """Чистим overrides до/после теста и блокируем реальную БД.

    Если тест забудет замокать какой-то сервис, `get_session` бросит
    RuntimeError — тест явно упадёт, а не будет молча ходить в БД.
    """
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = AsyncMock(
        side_effect=RuntimeError("DB access not allowed in unit tests")
    )
    yield
    app.dependency_overrides.clear()


from httpx import ASGITransport, AsyncClient

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as c:
        yield c


# ---------- Хелперы override ----------

@pytest.fixture
def as_user():
    """Устанавливает текущего пользователя (подменяет get_current_user)."""
    def _set(user):
        app.dependency_overrides[get_current_user] = lambda: user
    return _set


@pytest.fixture
def service():
    """Возвращает (или создаёт) мок сервиса и подменяет зависимость."""
    _mocks: dict[str, AsyncMock] = {}

    def _set(name, mock=None):
        if name in _mocks and mock is None:
            return _mocks[name]
        mock = mock or AsyncMock()

        def _getter():
            return mock

        app.dependency_overrides[SERVICES_MAP[name]] = _getter
        _mocks[name] = mock
        return mock

    return _set


@pytest.fixture
def obj():
    _objs = {}

    def _set(name, value=None, *, error=None):
        if name in _objs and value is None and error is None:
            return _objs[name]
        getter = OBJECTS_MAP[name]
        if error is not None:
            async def _raises():
                raise error
            app.dependency_overrides[getter] = _raises
        else:
            def _getter():
                return value
            app.dependency_overrides[getter] = _getter
        _objs[name] = value
        return value

    return _set


# ---------- Готовые фикстуры ----------

@pytest.fixture
def guest():
    return make_user(RoleEnum.GUEST)


@pytest.fixture
def auth_user():
    return make_user(RoleEnum.AUTH)


@pytest.fixture
def member():
    return make_user(RoleEnum.MEMBER)


@pytest.fixture
def manager():
    return make_user(RoleEnum.MANAGER)


@pytest.fixture
def team_obj():
    return make_team()


@pytest.fixture
def task_obj():
    return make_task()


@pytest.fixture
def comment_obj():
    return make_comment()


@pytest.fixture
def evaluation_obj():
    return make_evaluation()


@pytest.fixture
def meeting_obj():
    return make_meeting()