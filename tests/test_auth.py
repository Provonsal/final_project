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
    """Создаёт тестового пользователя с корректными UserCredentials"""
    pwd_manager = PWDManager(PWDConfig())
    password = "testpassword123"
    
    # --- АДАПТИРУЙ ПОД ТВОЙ PWDManager ---
    # Если у тебя есть метод вроде: salt, pwd_hash = pwd_manager.get_salt_and_hash(password)
    # используй его. Ниже приведена универсальная заглушка, которая точно подойдет под BYTEA:
    
    salt = pwd_manager.generate_salt()
    
    
    password_hash = pwd_manager.hash_password(password, salt)
    
    
    user = User(
        email="test@example.com",
        name="Test User",
        role=RoleEnum.MEMBER,
        is_active=True,
        # Благодаря cascade="all, delete-orphan" в модели User, 
        # добавление User автоматически добавит и сохранит UserCredentials
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


class TestRegister:
    """Тесты для POST /api/v1/auth/register"""
    
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Успешная регистрация нового пользователя"""
        # Внимание: твой роут использует UserRegister.as_form, 
        # поэтому httpx отправляет данные как form-data (параметр data=), а не json=
        response = await client.post(
            "/api/v1/auth/register",
            data={
                "username": "newuser@example.com",
                "name": "New User",
                "password": "securepassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["login"] == "newuser@example.com"
        assert data["message"] == "Регистрация успешна"
        assert "role" in data
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """Попытка регистрации с существующим email"""
        response = await client.post(
            "/api/v1/auth/register",
            data={
                "username": test_user.email,
                "name": "Duplicate User",
                "password": "password123"
            }
        )
        
        # Проверяем статус (твой обработчик возвращает 400 для WrongInputError)
        assert response.status_code == 400
        
        # Проверяем кастомный формат ошибки из handlers.py
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "BAD_REQUEST"
        assert "already exists" in data["error"]["message"].lower()


class TestLogin:
    """Тесты для POST /api/v1/auth/login"""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Успешный логин"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Логин с неверным паролем"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword"
            }
        )
        
        # Твой сервис бросает WrongInputError → 400
        assert response.status_code == 400
        
        # Проверяем кастомный формат из handlers.py
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "BAD_REQUEST"
        # Сообщение может быть разным — подставь то, что реально возвращает твой сервис
        assert "password" in data["error"]["message"].lower() or \
            "неверн" in data["error"]["message"].lower() or \
            "invalid" in data["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_login_missing_credentials(self, client: AsyncClient):
        """Логин без обязательных полей"""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "user@example.com"
                # отсутствует password
            }
        )
        
        assert response.status_code == 422  # Validation Error от FastAPI