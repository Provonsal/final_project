import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import TeamInviteCode, User, UserCredentials, Team, TeamUser
from app.models.RoleEnum import RoleEnum
from utils.password_manager import PWDManager
from utils.config import PWDConfig


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
async def test_team(db_session: AsyncSession, manager_user):
    """Создаём тестовую команду"""
    team = Team(
        name="Test Team",
        max_per_team=10,
        owner=manager_user.id
    )

    invite_code = TeamInviteCode(
        creator=manager_user.id,
        body="1234",
        team=team
    )
    
    db_session.add(team)
    db_session.add(invite_code)
    await db_session.flush()
    await db_session.commit()
    await db_session.refresh(team)
    
    # Добавляем менеджера как участника
    member = TeamUser(
        team_id=team.id,
        user_id=manager_user.id
    )
    db_session.add(member)
    await db_session.commit()
    
    return team


@pytest_asyncio.fixture
async def manager_token(client: AsyncClient, manager_user):
    """Получаем токен для менеджера"""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": manager_user.email,
            "password": "managerpass123"
        }
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def member_token(client: AsyncClient, member_user):
    """Получаем токен для участника"""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": member_user.email,
            "password": "memberpass123"
        }
    )
    return response.json()["access_token"]


class TestCreateTeam:
    """Тесты для POST /api/v1/teams/"""
    
    @pytest.mark.asyncio
    async def test_create_team_success(self, client: AsyncClient, manager_token):
        """Успешное создание команды менеджером"""
        response = await client.post(
            "/api/v1/teams/",
            json={"name": "New Team"},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Team"
        assert "id" in data
        assert "owner_id" in data
        assert "max_members" in data
    
    @pytest.mark.asyncio
    async def test_create_team_as_member_forbidden(self, client: AsyncClient, member_token):
        """Обычный участник не может создать команду"""
        response = await client.post(
            "/api/v1/teams/",
            json={"name": "Unauthorized Team"},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code in [403, 400]
    
    @pytest.mark.asyncio
    async def test_create_team_without_auth(self, client: AsyncClient):
        """Создание команды без авторизации"""
        response = await client.post(
            "/api/v1/teams/",
            json={"name": "No Auth Team"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_team_missing_name(self, client: AsyncClient, manager_token):
        """Создание команды без имени"""
        response = await client.post(
            "/api/v1/teams/",
            json={},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 422


class TestGetTeams:
    """Тесты для GET /api/v1/teams/"""
    
    @pytest.mark.asyncio
    async def test_get_teams_success(self, client: AsyncClient, manager_token, test_team):
        """Получение списка команд"""
        response = await client.get(
            "/api/v1/teams/",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Отладка: посмотрим, что реально вернулось
        print("\n=== DEBUG: teams response ===")
        print(f"Ожидаемый team_id: {test_team.id} (type: {type(test_team.id)})")
        print(f"Получено команд: {len(data)}")
        for t in data:
            print(f"  - id={t['id']!r} (type: {type(t['id'])}), name={t['name']}")
        print("================================\n")
        
        assert len(data) >= 1
        
        # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: приводим оба ID к строке
        team = next((t for t in data if str(t["id"]) == str(test_team.id)), None)
        assert team is not None, f"Команда {test_team.id} не найдена в ответе"
        assert team["name"] == test_team.name
    
    @pytest.mark.asyncio
    async def test_get_teams_without_auth(self, client: AsyncClient):
        """Получение списка команд без авторизации"""
        response = await client.get("/api/v1/teams/")
        
        assert response.status_code == 401


class TestGetTeam:
    """Тесты для GET /api/v1/teams/{team_id}"""
    
    @pytest.mark.asyncio
    async def test_get_team_success(self, client: AsyncClient, manager_token, test_team):
        """Получение информации о команде"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_team.id)
        assert data["name"] == test_team.name
    
    @pytest.mark.asyncio
    async def test_get_team_not_found(self, client: AsyncClient, manager_token):
        """Получение несуществующей команды"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await client.get(
            f"/api/v1/teams/{fake_uuid}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 404


class TestUpdateTeam:
    """Тесты для PATCH /api/v1/teams/{team_id}"""
    
    @pytest.mark.asyncio
    async def test_update_team_success(self, client: AsyncClient, manager_token, test_team):
        """Успешное обновление команды менеджером"""
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}",
            json={"name": "Updated Team Name"},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Team Name"
    
    @pytest.mark.asyncio
    async def test_update_team_as_member_forbidden(self, client: AsyncClient, member_token, test_team):
        """Обычный участник не может обновить команду"""
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}",
            json={"name": "Unauthorized Update"},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code in [403, 400]


class TestDeleteTeam:
    """Тесты для DELETE /api/v1/teams/{team_id}"""
    
    @pytest.mark.asyncio
    async def test_delete_team_success(self, client: AsyncClient, manager_token, test_team):
        """Успешное удаление команды менеджером"""
        response = await client.delete(
            f"/api/v1/teams/{test_team.id}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_delete_team_as_member_forbidden(self, client: AsyncClient, member_token, test_team):
        """Обычный участник не может удалить команду"""
        response = await client.delete(
            f"/api/v1/teams/{test_team.id}",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code in [403, 400]


class TestGetInviteCode:
    """Тесты для POST /api/v1/teams/code"""
    
    @pytest.mark.asyncio
    async def test_get_invite_code_success(self, client: AsyncClient, manager_token, test_team):
        """Получение invite-кода менеджером"""
        response = await client.post(
            "/api/v1/teams/code",
            params={"team_id": str(test_team.id)},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert data["team_id"] == str(test_team.id)
        assert data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_get_invite_code_as_member_forbidden(self, client: AsyncClient, member_token, test_team):
        """Обычный участник не может получить invite-код"""
        response = await client.post(
            "/api/v1/teams/code",
            params={"team_id": str(test_team.id)},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 403


class TestJoinTeam:
    """Тесты для POST /api/v1/teams/join"""
    
    @pytest.mark.asyncio
    async def test_join_team_success(
        self, 
        client: AsyncClient, 
        member_token, 
        manager_token,
        test_team,
        db_session: AsyncSession
    ):
        """Успешное присоединение к команде по invite-коду"""
        # Сначала получаем invite-код
        code_response = await client.post(
            "/api/v1/teams/code",
            params={"team_id": test_team.id},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        invite_code = code_response.json()["code"]
        
        # Теперь присоединяемся
        response = await client.post(
            "/api/v1/teams/join",
            params={"invite_code": invite_code},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_join_team_invalid_code(self, client: AsyncClient, member_token):
        """Присоединение с невалидным invite-кодом"""
        response = await client.post(
            "/api/v1/teams/join",
            params={"invite_code": "INVALID_CODE"},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code in [400, 404]


class TestLeaveTeam:
    """Тесты для POST /api/v1/teams/{team_id}/leave"""
    
    @pytest.mark.asyncio
    async def test_leave_team_success(
        self,
        client: AsyncClient,
        member_token,
        manager_token,
        test_team,
        db_session: AsyncSession
    ):
        """Успешный выход из команды"""
        # Сначала присоединяем участника
        code_response = await client.post(
            "/api/v1/teams/code",
            params={"team_id": str(test_team.id)},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        invite_code = code_response.json()["code"]
        
        await client.post(
            "/api/v1/teams/join",
            params={"invite_code": invite_code},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        # Теперь выходим
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/leave",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200


class TestGetTeamMembers:
    """Тесты для GET /api/v1/teams/{team_id}/members"""
    
    @pytest.mark.asyncio
    async def test_get_team_members_success(
        self,
        client: AsyncClient,
        manager_token,
        test_team
    ):
        """Получение списка участников команды"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/members",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Проверяем, что менеджер есть в списке
        manager = next((m for m in data if m["email"] == "manager@example.com"), None)
        assert manager is not None
    
    @pytest.mark.asyncio
    async def test_get_team_members_without_auth(self, client: AsyncClient, test_team):
        """Получение участников без авторизации"""
        response = await client.get(f"/api/v1/teams/{test_team.id}/members")
        
        assert response.status_code == 401