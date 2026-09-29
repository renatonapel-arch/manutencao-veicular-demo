"""Engine + Session + Base SQLAlchemy — padrão async (idêntico ao Clavis).

Aceita `DATABASE_URL` em qualquer formato:
- postgresql://user:pass@host/db          → convertida para asyncpg
- postgresql+asyncpg://user:pass@host/db  → usada direta
- postgresql+psycopg2://...               → convertida para asyncpg

O driver sync (psycopg2) fica disponível como fallback exclusivamente para
o Alembic (ver env.py) — todo runtime é 100% async.
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Awaitable, Callable, TypeVar

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

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


T = TypeVar("T")


def run_async_job(fn: Callable[[AsyncSession], Awaitable[T]]) -> T:
    """Roda `fn(db)` num event loop PRÓPRIO, com engine descartável (NullPool).

    Jobs do APScheduler rodam em thread própria, fora do loop do uvicorn onde o
    `engine` global foi criado. Reusar aquele engine via asyncio.run() deixa
    conexões asyncpg presas a um loop que morre no fim do job: o pool nunca as
    fecha, o Postgres chega em max_connections e o módulo inteiro cai
    (#0220 — 100/100 conexões, login 500 pra todo mundo).

    Engine próprio + NullPool + dispose no finally = nada sobrevive ao job.
    """
    async def _run() -> T:
        eng = create_async_engine(DATABASE_URL_ASYNC, poolclass=NullPool, future=True)
        try:
            async with async_sessionmaker(
                bind=eng, class_=AsyncSession, expire_on_commit=False,
            )() as db:
                return await fn(db)
        finally:
            await eng.dispose()

    return asyncio.run(_run())
