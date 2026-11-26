import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from app.models.models import User, UserCredentials, Team, TeamUser, Task, Comment
from app.models.RoleEnum import RoleEnum
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
async def another_member_user(db_session: AsyncSession):
    """Создаём ещё одного участника (для тестов прав доступа)"""
    pwd_manager = PWDManager(PWDConfig())
    password = "anotherpass123"
    
    salt = pwd_manager.generate_salt()
    password_hash = pwd_manager.hash_password(password, salt)
    
    user = User(
        email="another@example.com",
        name="Another Member",
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
async def test_team(db_session: AsyncSession, manager_user, member_user, another_member_user):
    """Создаём тестовую команду с тремя участниками"""
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
    db_session.add(TeamUser(
        team_id=team.id,
        user_id=another_member_user.id
    ))
    await db_session.commit()
    return team


@pytest_asyncio.fixture
async def test_task(db_session: AsyncSession, test_team, member_user):
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
    return task


@pytest_asyncio.fixture
async def test_comment(db_session: AsyncSession, test_task, member_user):
    """Создаём тестовый комментарий от member_user"""
    comment = Comment(
        text="Test comment text",
        author=member_user.id,
        task_id=test_task.id
    )
    
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)
    return comment


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


@pytest_asyncio.fixture
async def another_member_token(client: AsyncClient, another_member_user):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": another_member_user.email, "password": "anotherpass123"}
    )
    return response.json()["access_token"]


class TestCreateComment:
    """Тесты для POST /api/v1/teams/{team_id}/tasks/{task_id}/comments"""
    
    @pytest.mark.asyncio
    async def test_create_comment_success(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task,
        member_user
    ):
        """Успешное создание комментария"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments",
            json={"text": "New comment from member"},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["text"] == "New comment from member"
        assert str(data["author"]) == str(member_user.id) if 'member_user' in dir() else True
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_create_comment_as_manager(
        self,
        client: AsyncClient,
        manager_token,
        test_team,
        test_task
    ):
        """Менеджер тоже может создавать комментарии"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments",
            json={"text": "Comment from manager"},
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Comment from manager"
    
    @pytest.mark.asyncio
    async def test_create_comment_missing_text(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task
    ):
        """Создание комментария без текста → 422"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments",
            json={},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_comment_without_auth(
        self,
        client: AsyncClient,
        test_team,
        test_task
    ):
        """Создание комментария без авторизации → 401"""
        response = await client.post(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments",
            json={"text": "Unauthorized comment"}
        )
        
        assert response.status_code == 401


class TestReadComments:
    """Тесты для GET /api/v1/teams/{team_id}/tasks/{task_id}/comments"""
    
    @pytest.mark.asyncio
    async def test_read_comments_success(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task,
        test_comment
    ):
        """Получение списка комментариев"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        comment = next((c for c in data if str(c["id"]) == str(test_comment.id)), None)
        assert comment is not None
        assert comment["text"] == test_comment.text
    
    @pytest.mark.asyncio
    async def test_read_comments_empty(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task
    ):
        """Получение комментариев для задачи без комментариев"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    @pytest.mark.asyncio
    async def test_read_comments_as_manager(
        self,
        client: AsyncClient,
        manager_token,
        test_team,
        test_task,
        test_comment
    ):
        """Менеджер тоже может получать комментарии"""
        response = await client.get(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestEditComment:
    """Тесты для PATCH /api/v1/teams/{team_id}/tasks/{task_id}/comments/{comment_id}"""
    
    @pytest.mark.asyncio
    async def test_edit_comment_success(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task,
        test_comment
    ):
        """Успешное редактирование своего комментария"""
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments/{test_comment.id}",
            json={"text": "Updated comment text"},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Updated comment text"
        assert str(data["id"]) == str(test_comment.id)
    
    @pytest.mark.asyncio
    async def test_edit_comment_not_author_forbidden(
        self,
        client: AsyncClient,
        another_member_token,
        test_team,
        test_task,
        test_comment
    ):
        """Нельзя редактировать чужой комментарий"""
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments/{test_comment.id}",
            json={"text": "Unauthorized edit"},
            headers={"Authorization": f"Bearer {another_member_token}"}
        )
        
        # Ожидаем 403 или 400 в зависимости от реализации
        assert response.status_code in [403, 400]
    
    @pytest.mark.asyncio
    async def test_edit_comment_not_found(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task
    ):
        """Редактирование несуществующего комментария → 404"""
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments/{NONEXISTENT_UUID}",
            json={"text": "Update nonexistent"},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_edit_comment_invalid_uuid(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task
    ):
        """Редактирование с невалидным UUID → 422"""
        response = await client.patch(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments/not-a-uuid",
            json={"text": "Invalid UUID"},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 422


class TestDeleteComment:
    """Тесты для DELETE /api/v1/teams/{team_id}/tasks/{task_id}/comments/{comment_id}"""
    
    @pytest.mark.asyncio
    async def test_delete_comment_success(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task,
        test_comment
    ):
        """Успешное удаление своего комментария"""
        response = await client.delete(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments/{test_comment.id}",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_delete_comment_not_author_forbidden(
        self,
        client: AsyncClient,
        another_member_token,
        test_team,
        test_task,
        test_comment
    ):
        """Нельзя удалить чужой комментарий"""
        response = await client.delete(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments/{test_comment.id}",
            headers={"Authorization": f"Bearer {another_member_token}"}
        )
        
        assert response.status_code in [403, 400]
    
    @pytest.mark.asyncio
    async def test_delete_comment_not_found(
        self,
        client: AsyncClient,
        member_token,
        test_team,
        test_task
    ):
        """Удаление несуществующего комментария → 404"""
        response = await client.delete(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments/{NONEXISTENT_UUID}",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_comment_without_auth(
        self,
        client: AsyncClient,
        test_team,
        test_task,
        test_comment
    ):
        """Удаление без авторизации → 401"""
        response = await client.delete(
            f"/api/v1/teams/{test_team.id}/tasks/{test_task.id}/comments/{test_comment.id}"
        )
        
        assert response.status_code == 401