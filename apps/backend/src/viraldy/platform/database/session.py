from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from viraldy.platform.config.settings import get_settings

settings = get_settings()

async_engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionFactory = async_sessionmaker(async_engine, expire_on_commit=False)

sync_engine = create_engine(settings.database_sync_url, pool_pre_ping=True)
SyncSessionFactory = sessionmaker(sync_engine, expire_on_commit=False)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def create_worker_session() -> Session:
    return SyncSessionFactory()
