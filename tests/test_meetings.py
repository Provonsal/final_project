import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from app.models.models import MeetingInviteCode, MeetingUser, User, UserCredentials, Team, TeamUser, Meeting
from app.models.RoleEnum import RoleEnum
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
        max_per_team=15,
        owner=manager_user.id
    )
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    
    # Менеджер как участник
    db_session.add(TeamUser(
        team_id=team.id,
        user_id=manager_user.id,
    ))
    # Обычный участник
    db_session.add(TeamUser(
        team_id=team.id,
        user_id=member_user.id,
    ))
    await db_session.commit()
    return team


@pytest_asyncio.fixture
async def test_meeting(db_session: AsyncSession, test_team, manager_user):
    """Создаём тестовое совещание"""
    starts_at = datetime.now(timezone.utc) + timedelta(days=1)
    ends_at = starts_at + timedelta(hours=1)
    
    meeting = Meeting(
        starts_at=starts_at,
        ends_at=ends_at,
        related_team=test_team.id,
        creator=manager_user.id,
        max_members=15
    )


    db_session.add(meeting)
    await db_session.commit()
    await db_session.refresh(meeting)

    invite_code = MeetingInviteCode(
        creator=manager_user.id,
        meeting=meeting,
        body="1234567890"
    )

    db_session.add(invite_code)
    await db_session.commit()
    await db_session.refresh(invite_code)

    # Обычный участник
    db_session.add(MeetingUser(
        meeting_id=meeting.id,
        user_id=manager_user.id,
    ))
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


class TestCreateMeeting:
    """Тесты для POST /api/v1/teams/{team_id}/meetings"""
    
    @pytest.mark.asyncio
    async def test_create_meeting_success(self, client: AsyncClient, manager_token, test_team, manager_user):
        """Успешное создание совещания менеджером"""
        starts_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        ends_at = (datetime.now(timezone.utc) + timedelta(days=1, hours=1)).isoformat()
        
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/meetings",
            json={
                "starts_at": starts_at,
                "ends_at": ends_at,
                "max_members": 15
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["team_id"] == str(test_team.id)
        assert data["creator"] == str(manager_user.id)
        assert data["max_members"] == 15
        assert "start_time" in data
        assert "end_time" in data
    
    @pytest.mark.asyncio
    async def test_create_meeting_default_max_members(self, client: AsyncClient, manager_token, test_team):
        """Создание совещания с дефолтным max_members"""
        starts_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        ends_at = (datetime.now(timezone.utc) + timedelta(days=1, hours=1)).isoformat()
        
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/meetings",
            json={
                "starts_at": starts_at,
                "ends_at": ends_at
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["max_members"] == 10  # default
    
    @pytest.mark.asyncio
    async def test_create_meeting_as_member_forbidden(self, client: AsyncClient, member_token, test_team):
        """Обычный участник не может создать совещание"""
        starts_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        ends_at = (datetime.now(timezone.utc) + timedelta(days=1, hours=1)).isoformat()
        
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/meetings",
            json={"starts_at": starts_at, "ends_at": ends_at},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code in [403, 400]
    
    @pytest.mark.asyncio
    async def test_create_meeting_without_auth(self, client: AsyncClient, test_team):
        """Создание совещания без авторизации"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/meetings",
            json={
                "starts_at": "2026-12-01T10:00:00Z",
                "ends_at": "2026-12-01T11:00:00Z"
            }
        )
        assert response.status_code == 401


class TestReadMeetings:
    """Тесты для GET /api/v1/teams/{team_id}/meetings"""
    
    @pytest.mark.asyncio
    async def test_read_meetings_success(self, client: AsyncClient, manager_token, test_team, test_meeting):
        """Получение списка совещаний"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/meetings",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        meeting = next((m for m in data if str(m["id"]) == str(test_meeting.id)), None)
        assert meeting is not None
        assert meeting["team_id"] == str(test_team.id)
    
    @pytest.mark.asyncio
    async def test_read_meetings_as_member(self, client: AsyncClient, member_token, test_team, test_meeting):
        """Обычный участник тоже может получать список"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/meetings",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        assert response.status_code == 200


class TestReadMeeting:
    """Тесты для GET /api/v1/teams/{team_id}/meetings/{meeting_id}"""
    
    @pytest.mark.asyncio
    async def test_read_meeting_success(self, client: AsyncClient, manager_token, test_team, test_meeting, manager_user):
        """Получение информации о совещании"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/meetings/{test_meeting.id}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert str(data["id"]) == str(test_meeting.id)
        assert data["team_id"] == str(test_team.id)
        assert data["creator"] == str(manager_user.id) if 'manager_user' in dir() else True
        assert "start_time" in data
        assert "end_time" in data
    
    @pytest.mark.asyncio
    async def test_read_meeting_not_found(self, client: AsyncClient, manager_token, test_team):
        """Получение несуществующего совещания"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/meetings/{NONEXISTENT_UUID}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_read_meeting_invalid_uuid(self, client: AsyncClient, manager_token, test_team):
        """Невалидный формат UUID → 422"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/meetings/not-a-uuid",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 422


class TestUpdateMeeting:
    """Тесты для PATCH /api/v1/teams/{team_id}/meetings/{meeting_id}"""
    
    @pytest.mark.asyncio
    async def test_update_meeting_success(self, client: AsyncClient, manager_token, test_team, test_meeting):
        """Успешное обновление совещания"""
        new_starts_at = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        new_ends_at = (datetime.now(timezone.utc) + timedelta(days=2, hours=2)).isoformat()
        
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/meetings/{test_meeting.id}",
            json={
                "starts_at": new_starts_at,
                "ends_at": new_ends_at,
                "max_members": 20
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["max_members"] == 20
    
    @pytest.mark.asyncio
    async def test_update_meeting_partial(self, client: AsyncClient, manager_token, test_team, test_meeting):
        """Частичное обновление (только max_members)"""
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/meetings/{test_meeting.id}",
            json={"max_members": 25},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["max_members"] == 25
    
    @pytest.mark.asyncio
    async def test_update_meeting_as_member_forbidden(self, client: AsyncClient, member_token, test_team, test_meeting):
        """Обычный участник не может обновить совещание"""
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/meetings/{test_meeting.id}",
            json={"max_members": 30},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        assert response.status_code in [403, 400]


class TestDeleteMeeting:
    """Тесты для DELETE /api/v1/teams/{team_id}/meetings/{meeting_id}"""
    
    @pytest.mark.asyncio
    async def test_delete_meeting_success(self, client: AsyncClient, manager_token, test_team, test_meeting):
        """Успешное удаление совещания"""
        response = await client.delete(
            f"/api/v1/teams/{test_team.id}/meetings/{test_meeting.id}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_delete_meeting_as_member_forbidden(self, client: AsyncClient, member_token, test_team, test_meeting):
        """Обычный участник не может удалить совещание"""
        response = await client.delete(
            f"/api/v1/teams/{test_team.id}/meetings/{test_meeting.id}",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        assert response.status_code in [403, 400]


class TestGetInviteCode:
    """Тесты для GET /api/v1/teams/{team_id}/meetings/{meeting_id}/invite_code"""
    
    @pytest.mark.asyncio
    async def test_get_invite_code_success(
        self, client: AsyncClient, manager_token, test_team, test_meeting
    ):
        """Получение invite-кода для совещания"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/meetings/{test_meeting.id}/invite_code",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert data["meeting_id"] == str(test_meeting.id)
        assert data["is_active"] is True


class TestCreateInviteCode:
    """Тесты для POST /api/v1/teams/{team_id}/meetings/{meeting_id}/invite_code"""
    
    @pytest.mark.asyncio
    async def test_create_invite_code_success(
        self, client: AsyncClient, manager_token, test_team, test_meeting
    ):
        """Создание invite-кода с ограниченным числом использований"""
        # uses передаётся В QUERY, не в body!
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/meetings/{test_meeting.id}/invite_code",
            params={"uses": 5},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_create_invite_code_unlimited(
        self, client: AsyncClient, manager_token, test_team, test_meeting
    ):
        """Создание invite-кода без ограничений"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/meetings/{test_meeting.id}/invite_code",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
    
    @pytest.mark.asyncio
    async def test_create_invite_code_as_member_forbidden(
        self, client: AsyncClient, member_token, test_team, test_meeting
    ):
        """Обычный участник не может создать invite-код"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/meetings/{test_meeting.id}/invite_code",
            params={"uses": 1},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        assert response.status_code in [403, 400]


class TestJoinMeeting:
    """Тесты для POST /api/v1/teams/{team_id}/meetings/join"""
    
    @pytest.mark.asyncio
    async def test_join_meeting_success(
        self,
        client: AsyncClient,
        member_token,
        manager_token,
        test_team,
        test_meeting,
    ):
        """Успешное присоединение по invite-коду"""
        # Получаем код
        code_response = await client.get(
            f"/api/v1/teams/{test_team.id}/meetings/{test_meeting.id}/invite_code",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        invite_code = code_response.json()["code"]
        
        # code передаётся В QUERY, не в body!
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/meetings/join",
            params={"code": invite_code},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_join_meeting_invalid_code(self, client: AsyncClient, member_token, test_team):
        """Присоединение с невалидным кодом"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/meetings/join",
            params={"code": "INVALID_CODE"},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        # Ожидаем ошибку (400/404 — зависит от реализации сервиса)
        assert response.status_code in [400, 404]
    
    @pytest.mark.asyncio
    async def test_join_meeting_missing_code(self, client: AsyncClient, member_token, test_team):
        """Присоединение без кода → 422 (обязательный query param)"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/meetings/join",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        assert response.status_code == 422


class TestLeaveMeeting:
    """Тесты для POST /api/v1/teams/{team_id}/meetings/{meeting_id}/leave"""
    
    @pytest.mark.asyncio
    async def test_leave_meeting_success(
        self,
        client: AsyncClient,
        member_token,
        manager_token,
        test_team,
        test_meeting,
    ):
        """Успешный выход из совещания"""
        # Сначала присоединяем участника
        code_response = await client.get(
            f"/api/v1/teams/{test_team.id}/meetings/{test_meeting.id}/invite_code",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        invite_code = code_response.json()["code"]
        
        await client.post(
            f"/api/v1/teams/{test_team.id}/meetings/join",
            params={"code": invite_code},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        # Теперь выходим
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/meetings/{test_meeting.id}/leave",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200