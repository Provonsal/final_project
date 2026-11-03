# conftest.py
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Поправьте пути импортов под свой проект
from app.models import RoleEnum
from app.routers.api.v1.auth import router as auth_router
from app.routers.api.v1.tasks import router as tasks_router
from app.routers.api.v1.teams import router as teams_router
from app.routers.api.v1.calendar import router as calendar_router
from app.dependencies import get_auth_service, get_calendar_service, get_comment_service, get_current_user, get_evaluation_service, get_meeting_service, get_task_service, get_team_service, get_user_service


@pytest.fixture
def mock_auth_service() -> MagicMock:
    svc = MagicMock()
    svc.login = AsyncMock()
    return svc


@pytest.fixture
def mock_user_service() -> MagicMock:
    svc = MagicMock()
    svc.register = AsyncMock()
    return svc




# ---------- общие фабрики ----------

def make_user(role: RoleEnum = RoleEnum.MEMBER, user_id=None) -> MagicMock:
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.role = role
    return u


def make_task(team_id=None) -> MagicMock:
    t = MagicMock()
    t.team_id = team_id or uuid.uuid4()
    return t

@pytest.fixture
def mock_comment_service() -> MagicMock:
    svc = MagicMock()
    svc.create_comment = AsyncMock()
    svc.get_comments = AsyncMock()
    svc.update = AsyncMock()
    svc.delete = AsyncMock()
    return svc


@pytest.fixture
def mock_evaluation_service() -> MagicMock:
    svc = MagicMock()
    svc.create_evaluation = AsyncMock()
    svc.get_evaluation = AsyncMock()
    svc.update = AsyncMock()
    return svc


@pytest.fixture
def mock_task_service() -> MagicMock:
    svc = MagicMock()
    svc.get_task = AsyncMock(return_value=make_task())
    svc.create_task = AsyncMock()
    svc.get_all_tasks = AsyncMock()
    svc.update_task = AsyncMock()
    svc.delete_task = AsyncMock()
    return svc


@pytest.fixture
def mock_team_service() -> MagicMock:
    svc = MagicMock()
    svc.join_team = AsyncMock()
    svc.get_team_users = AsyncMock()
    svc.belong_to_team = AsyncMock(return_value=True)
    return svc


@pytest.fixture
def mock_meeting_service() -> MagicMock:
    svc = MagicMock()
    svc.create_meeting = AsyncMock()
    svc.get_meetings = AsyncMock()
    svc.get_meeting = AsyncMock()
    svc.update = AsyncMock()
    svc.delete = AsyncMock()
    return svc

@pytest.fixture
def mock_calendar_service() -> MagicMock:
    svc = MagicMock()
    svc.get_meetings = AsyncMock(return_value=[])
    return svc

# ---------- «коробка» для текущего юзера ----------

@pytest.fixture
def current_user_box() -> dict:
    """По умолчанию — MEMBER, чтобы большинство тестов проходили check_user_identity."""
    return {"user": make_user(RoleEnum.MEMBER)}


# ---------- приложение и клиент ----------

@pytest.fixture
def app(
    mock_auth_service, mock_user_service,
    mock_comment_service, mock_evaluation_service,
    mock_task_service, mock_team_service, mock_meeting_service,
    mock_calendar_service,
    current_user_box,
) -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(tasks_router)
    app.include_router(teams_router)
    app.include_router(calendar_router) 

    app.dependency_overrides[get_auth_service]         = lambda: mock_auth_service
    app.dependency_overrides[get_user_service]         = lambda: mock_user_service
    app.dependency_overrides[get_comment_service]      = lambda: mock_comment_service
    app.dependency_overrides[get_evaluation_service]   = lambda: mock_evaluation_service
    app.dependency_overrides[get_task_service]         = lambda: mock_task_service
    app.dependency_overrides[get_team_service]         = lambda: mock_team_service
    app.dependency_overrides[get_meeting_service]      = lambda: mock_meeting_service
    app.dependency_overrides[get_current_user]         = lambda: current_user_box["user"]
    app.dependency_overrides[get_calendar_service]     = lambda: mock_calendar_service
    
    return app



@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c