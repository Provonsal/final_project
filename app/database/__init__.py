from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends

from app.models import Base
from utils.config import DatabaseConfig

db_config = DatabaseConfig()

URL_DATABASE = db_config.url

engine = create_async_engine(URL_DATABASE, echo=False)

async_session_maker = async_sessionmaker(
    engine,
    #class_=AsyncSession,
    expire_on_commit=False
)

# async def init_models():
    
#     async with engine.begin() as conn:
#         #await conn.run_sync(Base.metadata.drop_all)
#         await conn.run_sync(Base.metadata.create_all)


async def get_session():
    
    async with async_session_maker() as session:
        yield session