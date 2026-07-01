"""Fixtures pytest — SQLite async (aiosqlite) para isolar dos requisitos do PG.

Adapta:
- JSONB → JSON (SQLite não tem JSONB)
- CheckConstraint continua funcionando no SQLite
- UUID(as_uuid=True) → String(36) genérico no SQLite

Uso:
    pytest -v                                 # roda tudo
    pytest tests/test_transitions.py          # só transições
    pytest -k "aprovacao and 500" -v          # só 1 caso
"""
from __future__ import annotations

import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import AsyncGenerator

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["FROTA_TOKEN"] = "test"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest_asyncio
from sqlalchemy import Column, JSON as _JSON
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---- Substitui JSONB por JSON antes de importar models ----
import sqlalchemy.dialects.postgresql as _pg
_pg.JSONB = _JSON  # fake JSONB → JSON para SQLite


from app import models  # noqa: E402
from app.database import Base  # noqa: E402


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db(db_engine) -> AsyncGenerator[AsyncSession, None]:
    Session = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as s:
        yield s


# ---------- Fixtures de dados ----------

@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> models.User:
    u = models.User(
        email="admin@napel.local", role="admin", filial_id=None,
        nome="Admin", senha_hash="hash", ativo=True,
    )
    db.add(u)
    await db.flush()
    m = models.MembroManutencao(
        user_id=u.id, filial_id=0, papel="admin", ativo=True,
    )
    db.add(m)
    await db.commit()
    return u


@pytest_asyncio.fixture
async def responsavel_user(db: AsyncSession) -> models.User:
    u = models.User(
        email="resp@napel.local", role="operador", filial_id=1,
        nome="Responsável Filial", senha_hash="hash", ativo=True,
    )
    db.add(u)
    await db.flush()
    m = models.MembroManutencao(
        user_id=u.id, filial_id=1, papel="filial_responsavel",
        funcionario_id=200, ativo=True,
    )
    db.add(m)
    await db.commit()
    return u


@pytest_asyncio.fixture
async def motorista_user(db: AsyncSession) -> models.User:
    u = models.User(
        email="mot@napel.local", role="operador", filial_id=1,
        nome="Motorista", senha_hash="hash", ativo=True,
    )
    db.add(u)
    await db.flush()
    m = models.MembroManutencao(
        user_id=u.id, filial_id=1, papel="motorista",
        funcionario_id=300, ativo=True,
    )
    db.add(m)
    await db.commit()
    return u


@pytest_asyncio.fixture
async def mecanico_user(db: AsyncSession) -> models.User:
    u = models.User(
        email="mec@napel.local", role="operador", filial_id=1,
        nome="Mecânico Interno", senha_hash="hash", ativo=True,
    )
    db.add(u)
    await db.flush()
    m = models.MembroManutencao(
        user_id=u.id, filial_id=1, papel="mecanico_interno",
        funcionario_id=400, ativo=True,
    )
    db.add(m)
    await db.commit()
    return u


@pytest_asyncio.fixture
async def veiculo(db: AsyncSession) -> models.VeiculoSnapshot:
    v = models.VeiculoSnapshot(
        veiculo_patrimonial_id=1001, placa="TST1A23",
        modelo="Test Model", tipo="carro", filial_id=1, km_atual=10000,
        ativo=True,
    )
    db.add(v)
    await db.commit()
    return v


# ---------- Helper para criar OS em qualquer estado ----------

async def make_os(
    db: AsyncSession, admin: models.User, veiculo: models.VeiculoSnapshot,
    status: str = "rascunho", valor_total: Decimal = Decimal("0"),
    tipo_destino: str = "oficina_terceirizada",
    funcionario_relator_id: int | None = None,
) -> models.OrdemServico:
    os = models.OrdemServico(
        veiculo_id=veiculo.id, filial_id=veiculo.filial_id,
        tipo_os="corretiva_manual", status=status,
        tipo_destino=tipo_destino,
        km_veiculo=veiculo.km_atual,
        valor_total=valor_total,
        aberto_por_user_id=admin.id,
        funcionario_relator_id=funcionario_relator_id,
    )
    db.add(os)
    await db.commit()
    await db.refresh(os)
    return os
