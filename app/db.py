from collections.abc import AsyncIterator

from sqlalchemy import inspect, text
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


# create_all не меняет существующие таблицы, поэтому новые колонки добавляем руками.
# После перехода на Alembic этот список удаляется.
_ADDED_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "users": [
        ("energy", "INTEGER NOT NULL DEFAULT 0"),
        ("energy_at", "TIMESTAMP WITH TIME ZONE"),
        ("season_points", "INTEGER NOT NULL DEFAULT 0"),
    ],
}


def _add_missing_columns(sync_conn) -> None:
    inspector = inspect(sync_conn)
    tables = set(inspector.get_table_names())
    for table, columns in _ADDED_COLUMNS.items():
        if table not in tables:
            continue
        existing = {column["name"] for column in inspector.get_columns(table)}
        for name, ddl in columns:
            if name in existing:
                continue
            sync_conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


async def init_db() -> None:
    # shortcut: create_all вместо Alembic, схема догоняется через _add_missing_columns
    from app import models  # noqa: F401  регистрация таблиц

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)
