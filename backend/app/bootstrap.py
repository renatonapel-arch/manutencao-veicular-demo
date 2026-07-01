"""Boot da demo — cria tabelas + aplica seeds essenciais (async).

Em produção, Alembic (`alembic upgrade head`) faz o schema.
Aqui só garantimos que:
1. Tabelas existem (fallback para dev/CI quando não roda Alembic)
2. Existe pelo menos 1 admin logável (senão nem consegue logar na demo)
3. Existe 1 membro admin do módulo (RBAC v3)

O seed grande (14 veículos, 200 OS históricas etc.) foi migrado para o
script `import_pipefy.py` da Fase C — dados reais em vez de sintéticos.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select

from .auth import hash_password
from .database import Base, SessionLocal, engine
from .models import MembroManutencao, User

log = logging.getLogger("manutencao.bootstrap")


async def init_database_async() -> None:
    """Cria tabelas (fallback). Idempotente."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Tabelas verificadas via metadata.create_all")


async def seed_all_async() -> None:
    """Garante 1 admin logável + 1 membro admin do módulo."""
    async with SessionLocal() as db:
        # Já tem user? Pula seed mínimo.
        stmt = select(User).limit(1)
        if (await db.execute(stmt)).scalar_one_or_none():
            log.info("Seed já aplicado, pulando.")
            return

        log.info("Aplicando seed mínimo (admin logável)...")
        senha = hash_password("password123")
        admin = User(
            id=1, email="hudson@napel.local", role="admin", filial_id=None,
            nome="Hudson · Admin", senha_hash=senha, telefone="+5544999413366",
            created_at=datetime.utcnow(),
        )
        db.add(admin)
        await db.flush()

        # Membro admin — filial 0 = "todas"
        membro = MembroManutencao(
            user_id=admin.id, filial_id=0, papel="admin",
            funcionario_id=None, ativo=True,
        )
        db.add(membro)
        await db.commit()
        log.info("Seed mínimo aplicado: %s + membro admin", admin.email)
