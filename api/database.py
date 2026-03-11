"""SQLAlchemy async engine + session factory.

Supports both SQLite (aiosqlite) and PostgreSQL (asyncpg).
PostgreSQL uses connection pooling for production performance.
"""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from api.config import DATABASE_URL

_is_sqlite = DATABASE_URL.startswith("sqlite")

# PostgreSQL connection pooling settings
_engine_kwargs: dict = {"echo": False}
if not _is_sqlite:
    _engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,  # recycle connections every 30 min
        "pool_pre_ping": True,  # test connections before use
    })

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)


if _is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, connection_record):
        """Enable foreign-key enforcement for every SQLite connection."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency that yields an async DB session."""
    async with async_session() as session:
        yield session


async def init_db() -> None:
    """Create all tables (development convenience — use Alembic in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
