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
    """Cria tabelas (fallback) + migra schema v2→v3 in place. Idempotente."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Tabelas verificadas via metadata.create_all")
    await _migrate_v3_schema()


# SQL de migração v2→v3 — todos idempotentes (IF EXISTS / IF NOT EXISTS).
# Converte SQLEnum→varchar preservando dados, renomeia created_by,
# adiciona colunas novas e remapeia status antigos pros 9 novos.
_MIGRATIONS_V3 = [
    # 0) view referencia colunas de os_manutencao → PG bloqueia ALTER TYPE.
    #    Derruba antes; recriada no último statement.
    "DROP VIEW IF EXISTS manutencao_garantia_ativa",
    # 1) enum PG → varchar (preserva valores)
    "ALTER TABLE os_manutencao ALTER COLUMN status TYPE varchar(24) USING status::text",
    "ALTER TABLE os_manutencao ALTER COLUMN tipo_os TYPE varchar(24) USING tipo_os::text",
    "ALTER TABLE anexos_os ALTER COLUMN tipo TYPE varchar(24) USING tipo::text",
    "ALTER TABLE os_item_linha ALTER COLUMN tipo_item TYPE varchar(16) USING tipo_item::text",
    "DROP TYPE IF EXISTS status_os_enum",
    "DROP TYPE IF EXISTS tipo_os_enum",
    "DROP TYPE IF EXISTS tipo_anexo_enum",
    "DROP TYPE IF EXISTS tipo_item_enum",
    # 2) remapeia status antigos → novos (v2 tinha 7 estados; v3 tem 9)
    "UPDATE os_manutencao SET status='aguardando_orcamento' WHERE status='aguardando_anexos'",
    "UPDATE os_manutencao SET status='em_execucao' WHERE status='pronta_execucao'",
    # 3) renomeia created_by → aberto_por_user_id (se ainda tem o nome antigo)
    """DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='os_manutencao' AND column_name='created_by') THEN
            ALTER TABLE os_manutencao RENAME COLUMN created_by TO aberto_por_user_id;
        END IF;
    END $$""",
    # 4) colunas novas v3 (todas nullable → seguro em tabela populada)
    "ALTER TABLE os_manutencao ADD COLUMN IF NOT EXISTS categoria varchar(20)",
    "ALTER TABLE os_manutencao ADD COLUMN IF NOT EXISTS urgencia varchar(20)",
    "ALTER TABLE os_manutencao ADD COLUMN IF NOT EXISTS tipo_destino varchar(24) NOT NULL DEFAULT 'oficina_terceirizada'",
    "ALTER TABLE os_manutencao ADD COLUMN IF NOT EXISTS motivo_aprovacao varchar(16)",
    "ALTER TABLE os_manutencao ADD COLUMN IF NOT EXISTS motivo_reprovacao text",
    "ALTER TABLE auditoria_os ALTER COLUMN operacao TYPE varchar(80)",
    "ALTER TABLE os_manutencao ADD COLUMN IF NOT EXISTS descricao_itens_original text",
    "ALTER TABLE os_manutencao ADD COLUMN IF NOT EXISTS pipefy_card_id varchar(20)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_os_pipefy_card_id ON os_manutencao(pipefy_card_id)",
    "ALTER TABLE os_manutencao ADD COLUMN IF NOT EXISTS aprovado_por_user_id integer REFERENCES users(id)",
    "ALTER TABLE os_manutencao ADD COLUMN IF NOT EXISTS aprovado_em timestamptz",
    "ALTER TABLE os_manutencao ADD COLUMN IF NOT EXISTS reaberta_de_os_id integer REFERENCES os_manutencao(id)",
    "ALTER TABLE os_manutencao ADD COLUMN IF NOT EXISTS funcionario_relator_id integer",
    "ALTER TABLE anexos_os ADD COLUMN IF NOT EXISTS posicao_pneu varchar(24)",
    "ALTER TABLE oficina_padronizada ADD COLUMN IF NOT EXISTS nome_normalizado varchar(120)",
    "CREATE INDEX IF NOT EXISTS ix_oficina_nome_normalizado ON oficina_padronizada(nome_normalizado)",
    "ALTER TABLE os_manutencao ADD COLUMN IF NOT EXISTS deleted_at timestamptz",
    "CREATE INDEX IF NOT EXISTS ix_os_deleted_at ON os_manutencao(deleted_at)",
    # 5) view de garantia ativa
    """CREATE OR REPLACE VIEW manutencao_garantia_ativa AS
        SELECT i.id AS item_id, o.id AS os_id, o.veiculo_id, o.oficina_id,
               i.descricao, i.garantia_dias,
               o.data_encerramento::date AS emitida_em,
               (o.data_encerramento::date + i.garantia_dias * INTERVAL '1 day')::date AS expira_em
        FROM os_item_linha i
        JOIN os_manutencao o ON o.id = i.os_id
        WHERE o.status = 'encerrada' AND o.deleted_at IS NULL
          AND i.garantia_dias > 0
          AND (o.data_encerramento + i.garantia_dias * INTERVAL '1 day') > NOW()""",
]


async def _migrate_v3_schema() -> None:
    """Aplica migrações v3 uma a uma; falha isolada não derruba o boot.

    Cada statement em transação própria — em PG, um erro aborta a transação
    inteira, então não dá pra agrupar statements idempotentes num begin() só.
    """
    from sqlalchemy import text as sql_text
    if engine.dialect.name != "postgresql":
        return  # SQLite (testes) não suporta esses DDLs
    for sql in _MIGRATIONS_V3:
        try:
            async with engine.begin() as conn:
                await conn.execute(sql_text(sql))
        except Exception as e:  # noqa: BLE001
            log.warning("migrate v3 skip (%s…): %s", sql[:60], str(e)[:120])


async def seed_all_async() -> None:
    """Garante users + membros mínimos para cada papel do RBAC.

    Ideia: você loga como qualquer papel pra testar o fluxo E2E (aprovador,
    responsável, mecânico interno, motorista), sem depender do provisionamento
    real do Clavis ainda.
    """
    async with SessionLocal() as db:
        senha = hash_password("password123")
        seeds = [
            # (email, nome, role, filial_id, papel_manutencao, telefone)
            ("hudson@napel.local",     "Hudson · Admin",           "admin",     None, "admin",              "+5544999413366"),
            ("cesar@napel.local",      "Cesar · Aprovador",        "aprovador", None, "admin",              "+5544999413366"),
            ("responsavel@napel.local","Responsável · Maringá",    "usuario",   2,    "filial_responsavel", "+5544999413366"),
            ("mecanico@napel.local",   "Mecânico · Bancada",       "usuario",   2,    "mecanico_interno",   "+5544999413366"),
            ("motorista@napel.local",  "Motorista · Frota",        "usuario",   2,    "motorista",          "+5544999413366"),
        ]

        # cria ou completa
        for email, nome, role, filial_id, papel, tel in seeds:
            r = await db.execute(select(User).where(User.email == email))
            u = r.scalar_one_or_none()
            if not u:
                u = User(
                    email=email, nome=nome, role=role, filial_id=filial_id,
                    senha_hash=senha, telefone=tel, created_at=datetime.utcnow(),
                )
                db.add(u)
                await db.flush()
                log.info("Seed user criado: %s (papel=%s)", email, papel)
            # membro do módulo (filial 0 = todas quando aprovador/admin)
            filial_membro = filial_id if filial_id else 0
            rm = await db.execute(select(MembroManutencao).where(
                MembroManutencao.user_id == u.id
            ))
            m = rm.scalar_one_or_none()
            if not m:
                db.add(MembroManutencao(
                    user_id=u.id, filial_id=filial_membro, papel=papel,
                    funcionario_id=None, ativo=True,
                ))
        await db.commit()
        log.info("Seed RBAC completo: 5 users em 5 papéis distintos.")
