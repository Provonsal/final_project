import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from app.models.models import User, UserCredentials, Team, TeamUser, Task, TaskRate
from app.models.RoleEnum import RoleEnum
from app.models.RateEnum import RateEnum
from app.models.TaskStatusEnum import TaskStatusEnum
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
async def test_team(db_session: AsyncSession, manager_user, member_user):
    """Создаём тестовую команду с участниками"""
    team = Team(
        name="Test Team",
        max_per_team=10,
        owner=manager_user.id
    )
    
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    
    # Добавляем менеджера как участника
    manager_member = TeamUser(
        team_id=team.id,
        user_id=manager_user.id
    )
    db_session.add(manager_member)
    
    # Добавляем обычного участника
    member_member = TeamUser(
        team_id=team.id,
        user_id=member_user.id
    )
    db_session.add(member_member)
    
    await db_session.commit()
    
    return team


@pytest_asyncio.fixture
async def test_task(db_session: AsyncSession, test_team, manager_user, member_user):
    """Создаём тестовую задачу"""
    due_date = datetime.now(timezone.utc) + timedelta(days=7)
    
    task = Task(
        title="Test Task",
        description="Test Description",
        assignee=member_user.id,
        due_date=due_date,
        status=TaskStatusEnum.OPEN,
        team_id=test_team.id
    )
    
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # Создаём оценку для задачи
    evaluation = TaskRate(
        task_id=task.id,
        rate=RateEnum.UNRATED,
        rater=manager_user.id
    )
    db_session.add(evaluation)
    await db_session.commit()
    await db_session.refresh(task)
    
    return task

@pytest_asyncio.fixture
async def test_processing_task(db_session: AsyncSession, test_team, manager_user, member_user):
    """Создаём запущенную в работу тестовую задачу"""
    due_date = datetime.now(timezone.utc) + timedelta(days=7)
    
    task = Task(
        title="Test Task",
        description="Test Description",
        assignee=member_user.id,
        due_date=due_date,
        status=TaskStatusEnum.IN_PROGRESS,
        team_id=test_team.id
    )
    
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # Создаём оценку для задачи
    evaluation = TaskRate(
        task_id=task.id,
        rate=RateEnum.UNRATED,
        rater=manager_user.id
    )
    db_session.add(evaluation)
    await db_session.commit()
    await db_session.refresh(task)
    
    return task

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


class TestCreateTask:
    """Тесты для POST /api/v1/teams/{team_id}/tasks"""
    
    @pytest.mark.asyncio
    async def test_create_task_success(self, client: AsyncClient, manager_token, test_team, member_user):
        """Успешное создание задачи менеджером"""
        due_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/tasks",
            json={
                "title": "New Task",
                "description": "Task description",
                "assignee": str(member_user.id),
                "due_date": due_date,
                "status": 1
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Task"
        assert data["description"] == "Task description"
        assert str(data["assignee_id"]) == str(member_user.id)
        assert "id" in data
        assert "evaluation" in data
    
    @pytest.mark.asyncio
    async def test_create_task_as_member_forbidden(self, client: AsyncClient, member_token, test_team, member_user):
        """Обычный участник не может создать задачу"""
        due_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/tasks",
            json={
                "title": "Unauthorized Task",
                "description": "Should fail",
                "assignee": str(member_user.id),
                "due_date": due_date
            },
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code in [403, 400]
    
    @pytest.mark.asyncio
    async def test_create_task_missing_fields(self, client: AsyncClient, manager_token, test_team):
        """Создание задачи без обязательных полей"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/tasks",
            json={
                "title": "Incomplete Task"
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 422


class TestReadTasks:
    """Тесты для GET /api/v1/teams/{team_id}/tasks"""
    
    @pytest.mark.asyncio
    async def test_read_tasks_success(self, client: AsyncClient, manager_token, test_team, test_task):
        """Получение списка задач"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/tasks",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        task = next((t for t in data if str(t["id"]) == str(test_task.id)), None)
        assert task is not None
        assert task["title"] == test_task.title
        assert "evaluation" in task
    
    @pytest.mark.asyncio
    async def test_read_tasks_as_member(self, client: AsyncClient, member_token, test_team, test_task):
        """Обычный участник может получать задачи"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/tasks",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestReadTask:
    """Тесты для GET /api/v1/teams/{team_id}/tasks/{task_id}"""
    
    @pytest.mark.asyncio
    async def test_read_task_success(self, client: AsyncClient, manager_token, test_team, test_task):
        """Получение информации о задаче"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert str(data["id"]) == str(test_task.id)
        assert data["title"] == test_task.title
        assert "evaluation" in data
        assert "comments" in data
    
    @pytest.mark.asyncio
    async def test_read_task_not_found(self, client: AsyncClient, manager_token, test_team):
        """Получение несуществующей задачи"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/tasks/{fake_uuid}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 404


class TestUpdateTask:
    """Тесты для PATCH /api/v1/teams/{team_id}/tasks/{task_id}"""
    
    @pytest.mark.asyncio
    async def test_update_task_success(self, client: AsyncClient, manager_token, test_team, test_task):
        """Успешное обновление задачи менеджером"""
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}",
            json={
                "title": "Updated Task Title",
                "description": "Updated description"
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Task Title"
        assert data["description"] == "Updated description"
    
    @pytest.mark.asyncio
    async def test_update_task_status(self, client: AsyncClient, manager_token, test_team, test_task):
        """Обновление статуса задачи"""
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}",
            json={
                "status": 2  # IN_PROGRESS
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == 2
    
    @pytest.mark.asyncio
    async def test_update_task_as_member_forbidden(self, client: AsyncClient, member_token, test_team, test_task):
        """Обычный участник не может обновить задачу"""
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}",
            json={
                "title": "Unauthorized Update"
            },
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code in [403, 400]


class TestStartTask:
    """Тесты для PATCH /api/v1/teams/{team_id}/tasks/{task_id}/start"""
    
    @pytest.mark.asyncio
    async def test_start_task_success(self, client: AsyncClient, member_token, test_team, test_task):
        """Успешное начало выполнения задачи"""
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/start",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == 2  # IN_PROGRESS


class TestEndTask:
    """Тесты для PATCH /api/v1/teams/{team_id}/tasks/{task_id}/end"""
    
    @pytest.mark.asyncio
    async def test_end_task_success(self, client: AsyncClient, member_token, test_team, test_processing_task):
        """Успешное завершение задачи"""
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/tasks/{test_processing_task.id}/end",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == 3  # DONE


class TestDeleteTask:
    """Тесты для DELETE /api/v1/teams/{team_id}/tasks/{task_id}"""
    
    @pytest.mark.asyncio
    async def test_delete_task_success(self, client: AsyncClient, manager_token, test_team, test_task):
        """Успешное удаление задачи менеджером"""
        response = await client.delete(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_delete_task_as_member_forbidden(self, client: AsyncClient, member_token, test_team, test_task):
        """Обычный участник не может удалить задачу"""
        response = await client.delete(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code in [403, 400]