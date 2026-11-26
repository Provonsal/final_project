import os

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

# ИМПОРТИРУЙ ПРАВИЛЬНЫЕ ПУТИ К СВОИМ ФАЙЛАМ:
from app.database import get_session, Base
from app.main import app  # или from app.main import app

IS_CI = os.getenv("CI") == "true"

@pytest_asyncio.fixture(scope="session")
async def postgres_container():
    """Запускаем PostgreSQL в контейнере ТОЛЬКО если мы не в CI"""
    if IS_CI:
        
        yield os.getenv("DATABASE_URL")
        return

    with PostgresContainer("postgres:17-alpine") as postgres:
        url = postgres.get_connection_url()
        async_url = url.replace("postgresql://", "postgresql+asyncpg://")
        yield async_url


@pytest_asyncio.fixture(scope="session")
async def engine(postgres_container):
    engine = create_async_engine(postgres_container, echo=False, pool_pre_ping=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# 3. Сессия БД (scope="function")
@pytest_asyncio.fixture(scope="function")
async def db_session(engine):
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()  # Гарантируем откат любых незакоммиченных изменений


# 4. HTTP Клиент (scope="function")
@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_session():
        yield db_session
    
    app.dependency_overrides[get_session] = override_get_session
    
    # Создаем клиент внутри function-scoped фикстуры, 
    # чтобы он использовал тот же event loop, что и тест
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()