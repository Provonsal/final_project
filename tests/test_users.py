import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User, UserCredentials
from app.models.RoleEnum import RoleEnum
from utils.password_manager import PWDManager
from utils.config import PWDConfig


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Создаём тестового пользователя"""
    pwd_manager = PWDManager(PWDConfig())
    password = "testpass123"
    
    salt = pwd_manager.generate_salt()
    password_hash = pwd_manager.hash_password(password, salt)
    
    user = User(
        email="testuser@example.com",
        name="Test User",
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
async def user_token(client: AsyncClient, test_user):
    """Получаем токен для пользователя"""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.email,
            "password": "testpass123"
        }
    )
    return response.json()["access_token"]


class TestGetMe:
    """Тесты для GET /api/v1/users/me"""
    
    @pytest.mark.asyncio
    async def test_get_me_success(self, client: AsyncClient, user_token, test_user):
        """Успешное получение информации о себе"""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем структуру ответа
        assert "id" in data
        assert "username" in data
        assert "role" in data
        
        # Проверяем значения
        assert str(data["id"]) == str(test_user.id)
        assert data["username"] == test_user.email
        assert data["role"] == test_user.role.value
    
    @pytest.mark.asyncio
    async def test_get_me_without_auth(self, client: AsyncClient):
        """Попытка доступа без авторизации → 401"""
        response = await client.get("/api/v1/users/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_me_with_invalid_token(self, client: AsyncClient):
        """Попытка доступа с невалидным токеном → 401"""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_me_with_malformed_token(self, client: AsyncClient):
        """Попытка доступа с неправильно сформированным токеном → 401"""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer not.a.jwt"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_me_response_schema(self, client: AsyncClient, user_token):
        """Проверяем, что ответ соответствует ожидаемой схеме"""
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Все поля из ResponseUserMe
        assert isinstance(data["id"], str)  # UUID как строка
        assert isinstance(data["username"], str)
        assert isinstance(data["role"], str)
        
        # role должен быть одним из допустимых значений
        assert data["role"] in ["guest", "auth", "manager", "member"]