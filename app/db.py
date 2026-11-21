from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


def _async_url(url: str) -> str:
    # Railway отдаёт postgresql://..., а SQLAlchemy для async-движка нужен +asyncpg.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix):]
    return url


engine = create_async_engine(_async_url(settings.database_url), pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    # shortcut: create_all вместо Alembic; перед первым изменением схемы в проде добавить миграции
    from app import models  # noqa: F401  регистрация таблиц

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
