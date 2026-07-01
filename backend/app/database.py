"""Engine + Session + Base SQLAlchemy — padrão async (idêntico ao Clavis).

Aceita `DATABASE_URL` em qualquer formato:
- postgresql://user:pass@host/db          → convertida para asyncpg
- postgresql+asyncpg://user:pass@host/db  → usada direta
- postgresql+psycopg2://...               → convertida para asyncpg

O driver sync (psycopg2) fica disponível como fallback exclusivamente para
o Alembic (ver env.py) — todo runtime é 100% async.
"""
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from .config import settings


def _to_async_url(url: str) -> str:
    """Garante driver asyncpg. Idempotente."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


DATABASE_URL_ASYNC = _to_async_url(settings.DATABASE_URL)

# SQLite não aceita pool_size/max_overflow — só engines Postgres/MySQL.
_is_sqlite = DATABASE_URL_ASYNC.startswith("sqlite")
_engine_kwargs: dict = {"future": True}
if not _is_sqlite:
    _engine_kwargs.update({
        "pool_size": 10, "max_overflow": 20,
        "pool_pre_ping": True, "pool_recycle": 3600,
    })

engine = create_async_engine(DATABASE_URL_ASYNC, **_engine_kwargs)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency FastAPI. Fecha a sessão automaticamente."""
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
