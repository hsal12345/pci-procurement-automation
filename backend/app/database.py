from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Async engine for FastAPI endpoints
async_db_url = settings.get_effective_async_db_url()
is_sqlite = "sqlite" in async_db_url

engine_kwargs = {}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

async_engine = create_async_engine(
    async_db_url,
    echo=settings.DEBUG,
    future=True,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Sync engine for Alembic and migration scripts
sync_db_url = settings.get_effective_sync_db_url()
sync_kwargs = {}
if "sqlite" in sync_db_url:
    sync_kwargs["connect_args"] = {"check_same_thread": False}

sync_engine = create_engine(
    sync_db_url,
    echo=False,
    future=True,
    **sync_kwargs
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
