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
        user_id=manager_user.id
    ))
    db_session.add(TeamUser(
        team_id=team.id,
        user_id=member_user.id
    ))
    await db_session.commit()
    return team


@pytest_asyncio.fixture
async def task_without_evaluation(db_session: AsyncSession, test_team, member_user):
    """Создаём задачу БЕЗ оценки (для тестов создания оценки)"""
    due_date = datetime.now(timezone.utc) + timedelta(days=7)
    
    task = Task(
        title="Task Without Evaluation",
        description="This task has no evaluation yet",
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
async def test_task_with_evaluation(db_session: AsyncSession, test_team, manager_user, member_user):
    """Создаём задачу С оценкой (для тестов GET и PATCH)"""
    due_date = datetime.now(timezone.utc) + timedelta(days=7)
    
    task = Task(
        title="Task With Evaluation",
        description="This task already has an evaluation",
        assignee=member_user.id,
        due_date=due_date,
        status=TaskStatusEnum.DONE,
        team_id=test_team.id
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # Создаём оценку для задачи
    evaluation = TaskRate(
        task_id=task.id,
        rate=RateEnum.GOOD,  # или просто 3, если RateEnum — это int
        rater=manager_user.id
    )
    db_session.add(evaluation)
    await db_session.commit()
    await db_session.refresh(evaluation)
    
    # Возвращаем кортеж (task, evaluation)
    return task, evaluation


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


class TestCreateEvaluation:
    """Тесты для POST /api/v1/teams/{team_id}/tasks/{task_id}/evaluation"""
    
    @pytest.mark.asyncio
    async def test_create_evaluation_success(
        self, 
        client: AsyncClient, 
        manager_token, 
        test_team, 
        task_without_evaluation,
        manager_user
    ):
        """Успешное создание оценки менеджером"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/tasks/{task_without_evaluation.id}/evaluation",
            json={
                "task_id": str(task_without_evaluation.id),
                "rate": 4  # RateEnum: 0-5
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["rate"] == 4
        assert str(data["author"]) == str(manager_user.id)
        assert "display_text" in data
    
    @pytest.mark.asyncio
    async def test_create_evaluation_as_member_forbidden(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        task_without_evaluation
    ):
        """Обычный участник не может создать оценку"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/tasks/{task_without_evaluation.id}/evaluation",
            json={
                "task_id": str(task_without_evaluation.id),
                "rate": 3
            },
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code in [403, 400]
    
    @pytest.mark.asyncio
    async def test_create_evaluation_invalid_rate(
        self,
        client: AsyncClient,
        manager_token,
        test_team,
        task_without_evaluation
    ):
        """Создание оценки с невалидным rate (вне диапазона 0-5)"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/tasks/{task_without_evaluation.id}/evaluation",
            json={
                "task_id": str(task_without_evaluation.id),
                "rate": 99  # Невалидное значение
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_evaluation_missing_rate(
        self,
        client: AsyncClient,
        manager_token,
        test_team,
        task_without_evaluation
    ):
        """Создание оценки без обязательного поля rate"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/tasks/{task_without_evaluation.id}/evaluation",
            json={
                "task_id": str(task_without_evaluation.id)
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_evaluation_without_auth(
        self,
        client: AsyncClient,
        test_team,
        task_without_evaluation
    ):
        """Создание оценки без авторизации"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/tasks/{task_without_evaluation.id}/evaluation",
            json={
                "task_id": str(task_without_evaluation.id),
                "rate": 3
            }
        )
        
        assert response.status_code == 401


class TestReadEvaluation:
    """Тесты для GET /api/v1/teams/{team_id}/tasks/{task_id}/evaluation"""
    
    @pytest.mark.asyncio
    async def test_read_evaluation_success(
        self,
        client: AsyncClient,
        manager_token,
        test_team,
        test_task_with_evaluation,
        manager_user
    ):
        """Успешное получение оценки"""
        task, evaluation = test_task_with_evaluation
        
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/tasks/{task.id}/evaluation",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert str(data["id"]) == str(evaluation.id)
        assert data["rate"] == evaluation.rate.value if hasattr(evaluation.rate, 'value') else evaluation.rate
        assert str(data["author"]) == str(manager_user.id)
        assert "display_text" in data
    
    @pytest.mark.asyncio
    async def test_read_evaluation_as_member(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task_with_evaluation
    ):
        """Обычный участник тоже может получить оценку"""
        task, evaluation = test_task_with_evaluation
        
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/tasks/{task.id}/evaluation",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert str(data["id"]) == str(evaluation.id)
    
    @pytest.mark.asyncio
    async def test_read_evaluation_not_found(
        self,
        client: AsyncClient,
        manager_token,
        test_team,
        task_without_evaluation
    ):
        """Получение оценки для задачи, у которой нет оценки"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/tasks/{task_without_evaluation.id}/evaluation",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        # Ожидаем 404, так как EvaluationDep не найдёт оценку
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_read_evaluation_without_auth(
        self,
        client: AsyncClient,
        test_team,
        test_task_with_evaluation
    ):
        """Получение оценки без авторизации"""
        task, evaluation = test_task_with_evaluation
        
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/tasks/{task.id}/evaluation"
        )
        
        assert response.status_code == 401


class TestUpdateEvaluation:
    """Тесты для PATCH /api/v1/teams/{team_id}/tasks/{task_id}/evaluation/{evaluation_id}"""
    
    @pytest.mark.asyncio
    async def test_update_evaluation_success(
        self,
        client: AsyncClient,
        manager_token,
        test_team,
        test_task_with_evaluation
    ):
        """Успешное обновление оценки менеджером"""
        task, evaluation = test_task_with_evaluation
        
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/tasks/{task.id}/evaluation/{evaluation.id}",
            json={
                "rate": 5  # Меняем на максимальную оценку
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["rate"] == 5
        assert str(data["id"]) == str(evaluation.id)
    
    @pytest.mark.asyncio
    async def test_update_evaluation_as_member_forbidden(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task_with_evaluation
    ):
        """Обычный участник не может обновить оценку"""
        task, evaluation = test_task_with_evaluation
        
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/tasks/{task.id}/evaluation/{evaluation.id}",
            json={
                "rate": 1
            },
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code in [403, 400]
    
    @pytest.mark.asyncio
    async def test_update_evaluation_invalid_rate(
        self,
        client: AsyncClient,
        manager_token,
        test_team,
        test_task_with_evaluation
    ):
        """Обновление оценки с невалидным rate"""
        task, evaluation = test_task_with_evaluation
        
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/tasks/{task.id}/evaluation/{evaluation.id}",
            json={
                "rate": 100  # Невалидное значение
            },
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 422
