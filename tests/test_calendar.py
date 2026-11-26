import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from app.models.models import User, UserCredentials, Team, TeamUser, Task, Meeting, TaskRate
from app.models.RoleEnum import RoleEnum
from app.models.RateEnum import RateEnum
from app.models.TaskStatusEnum import TaskStatusEnum
from utils.password_manager import PWDManager
from utils.config import PWDConfig


NONEXISTENT_UUID = "00000000-0000-0000-0000-000000000000"


@pytest_asyncio.fixture
async def manager_user(db_session: AsyncSession):
    """Создаём тестового менеджера"""
    pwd_manager = PWDManager(PWDConfig())
    password = "managerpass123"
    
    salt = pwd_manager.generate_salt()
    password_hash = pwd_manager.hash_password(password, salt)
    
    user = User(
        email="manager@example.com",
        name="Manager User",
        role=RoleEnum.MANAGER,
        is_active=True,
        user_credentials=UserCredentials(
            salt=salt,
            password_hash=password_hash,
            algorithm="sha256"
        )
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def member_user(db_session: AsyncSession):
    """Создаём тестового обычного участника"""
    pwd_manager = PWDManager(PWDConfig())
    password = "memberpass123"
    
    salt = pwd_manager.generate_salt()
    password_hash = pwd_manager.hash_password(password, salt)
    
    user = User(
        email="member@example.com",
        name="Member User",
        role=RoleEnum.MEMBER,
        is_active=True,
        user_credentials=UserCredentials(
            salt=salt,
            password_hash=password_hash,
            algorithm="sha256"
        )
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_team(db_session: AsyncSession, manager_user, member_user):
    """Создаём тестовую команду с обоими участниками"""
    team = Team(
        name="Test Team",
        max_per_team=10,
        owner=manager_user.id
    )
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    
    db_session.add(TeamUser(
        team_id=team.id,
        user_id=manager_user.id,
    ))
    db_session.add(TeamUser(
        team_id=team.id,
        user_id=member_user.id,
    ))
    await db_session.commit()
    return team


@pytest_asyncio.fixture
async def test_task_in_range(db_session: AsyncSession, test_team, member_user):
    """Создаём задачу, due_date которой попадает в диапазон 'завтра — через неделю'"""
    due_date = datetime.now(timezone.utc) + timedelta(days=3)
    
    task = Task(
        title="Calendar Task",
        description="Task for calendar test",
        assignee=member_user.id,
        due_date=due_date,
        status=TaskStatusEnum.OPEN,
        team_id=test_team.id
    )
    
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def test_task_out_of_range(db_session: AsyncSession, test_team, member_user):
    """Создаём задачу, due_date которой НЕ попадает в диапазон (через месяц)"""
    due_date = datetime.now(timezone.utc) + timedelta(days=30)
    
    task = Task(
        title="Out of Range Task",
        description="Task outside calendar range",
        assignee=member_user.id,
        due_date=due_date,
        status=TaskStatusEnum.OPEN,
        team_id=test_team.id
    )
    
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def test_meeting_in_range(db_session: AsyncSession, test_team, manager_user):
    """Создаём совещание, которое попадает в диапазон 'завтра — через неделю'"""
    starts_at = datetime.now(timezone.utc) + timedelta(days=2)
    ends_at = starts_at + timedelta(hours=1)
    
    meeting = Meeting(
        starts_at=starts_at,
        ends_at=ends_at,
        related_team=test_team.id,
        creator=manager_user.id,
        max_members=10
    )
    db_session.add(meeting)
    await db_session.commit()
    await db_session.refresh(meeting)
    return meeting


@pytest_asyncio.fixture
async def manager_token(client: AsyncClient, manager_user):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": manager_user.email, "password": "managerpass123"}
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def member_token(client: AsyncClient, member_user):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": member_user.email, "password": "memberpass123"}
    )
    return response.json()["access_token"]


class TestCalendar:
    """Тесты для GET /api/v1/calendar/{team_id}"""
    
    @pytest.mark.asyncio
    async def test_calendar_success_default_range(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task_in_range,
        test_meeting_in_range,
    ):
        """Получение календаря с дефолтным диапазоном (сегодня → ∞)"""
        response = await client.get(
            f"/api/v1/calendar/{test_team.id}",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем структуру ответа
        assert "meetings" in data
        assert "tasks" in data
        assert isinstance(data["meetings"], list)
        assert isinstance(data["tasks"], list)
        
        # Должны быть наши тестовые данные
        task = next((t for t in data["tasks"] if str(t["id"]) == str(test_task_in_range.id)), None)
        assert task is not None
        assert task["title"] == "Calendar Task"
        assert task["evaluation"] is None  # calendar возвращает evaluation=None
        
        meeting = next((m for m in data["meetings"] if str(m["id"]) == str(test_meeting_in_range.id)), None)
        assert meeting is not None
        assert meeting["team_id"] == str(test_team.id)
    
    @pytest.mark.asyncio
    async def test_calendar_with_explicit_range(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task_in_range,
        test_task_out_of_range,
        test_meeting_in_range,
    ):
        """Получение календаря с явным диапазоном date_from / date_until"""
        date_from = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        date_until = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        
        response = await client.get(
            f"/api/v1/calendar/{test_team.id}",
            params={
                "date_from": date_from,
                "date_until": date_until,
            },
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Задача в диапазоне должна быть
        in_range_task = next((t for t in data["tasks"] if str(t["id"]) == str(test_task_in_range.id)), None)
        assert in_range_task is not None
        
        # Задача вне диапазона НЕ должна быть
        out_of_range_task = next((t for t in data["tasks"] if str(t["id"]) == str(test_task_out_of_range.id)), None)
        assert out_of_range_task is None
        
        # Совещание в диапазоне должно быть
        meeting = next((m for m in data["meetings"] if str(m["id"]) == str(test_meeting_in_range.id)), None)
        assert meeting is not None
    
    @pytest.mark.asyncio
    async def test_calendar_as_member(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task_in_range,
    ):
        """Обычный участник тоже может получать календарь своей команды"""
        response = await client.get(
            f"/api/v1/calendar/{test_team.id}",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "meetings" in data
        assert "tasks" in data
    
    @pytest.mark.asyncio
    async def test_calendar_empty(
        self,
        client: AsyncClient,
        manager_token,
        test_team,
    ):
        """Календарь для команды без задач и совещаний"""
        response = await client.get(
            f"/api/v1/calendar/{test_team.id}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["meetings"] == []
        assert data["tasks"] == []
    
    @pytest.mark.asyncio
    async def test_calendar_without_auth(self, client: AsyncClient, test_team):
        """Получение календаря без авторизации → 401"""
        response = await client.get(f"/api/v1/calendar/{test_team.id}")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_calendar_invalid_uuid(self, client: AsyncClient, manager_token):
        """Невалидный формат UUID → 422"""
        response = await client.get(
            "/api/v1/calendar/not-a-uuid",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_calendar_nonexistent_team(self, client: AsyncClient, manager_token):
        """Несуществующая команда → 404"""
        response = await client.get(
            f"/api/v1/calendar/{NONEXISTENT_UUID}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_calendar_invalid_date_format(
        self,
        client: AsyncClient,
        manager_token,
        test_team,
    ):
        """Невалидный формат даты → 422"""
        response = await client.get(
            f"/api/v1/calendar/{test_team.id}",
            params={"date_from": "not-a-date"},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_calendar_task_schema_fields(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task_in_range,
    ):
        """Проверяем, что задача в календаре имеет все ожидаемые поля"""
        response = await client.get(
            f"/api/v1/calendar/{test_team.id}",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        task = next((t for t in data["tasks"] if str(t["id"]) == str(test_task_in_range.id)), None)
        assert task is not None
        
        # Все поля из ResponseTaskSchema
        assert "id" in task
        assert "title" in task
        assert "description" in task
        assert "assignee_id" in task
        assert "due_date" in task
        assert "status" in task
        assert "team_id" in task
        assert "evaluation" in task
        assert task["evaluation"] is None  # calendar не возвращает оценку
    
    @pytest.mark.asyncio
    async def test_calendar_meeting_schema_fields(
        self,
        client: AsyncClient,
        manager_token,
        test_team,
        test_meeting_in_range,
    ):
        """Проверяем, что совещание в календаре имеет все ожидаемые поля"""
        response = await client.get(
            f"/api/v1/calendar/{test_team.id}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        meeting = next((m for m in data["meetings"] if str(m["id"]) == str(test_meeting_in_range.id)), None)
        assert meeting is not None
        
        # Все поля из ResponseMeetingSchema
        assert "id" in meeting
        assert "start_time" in meeting
        assert "end_time" in meeting
        assert "team_id" in meeting
        assert "creator" in meeting
        assert "max_members" in meeting