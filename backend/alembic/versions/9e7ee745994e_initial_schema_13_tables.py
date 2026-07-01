"""initial schema (14 tables) — String+CheckConstraint, sem SQLEnum

Cria todo o schema do módulo Manutenção Veicular a partir dos models
declarados em app.models. Downgrade limpa todas as tabelas na ordem inversa
(respeitando FKs).

Revision ID: 9e7ee745994e
Revises:
Create Date: 2026-07-01
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "9e7ee745994e"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cria todas as tabelas + view manutencao_garantia_ativa.

    Usa metadata.create_all em vez de op.create_table hardcoded pra evitar
    divergência entre models.py e migration. Se algum diff aparecer no
    schema, é feito por migration nova, não retroativa.
    """
    from app.database import Base
    from app import models  # noqa: F401  força registro
    from sqlalchemy.dialects import postgresql

    bind = op.get_bind()
    inspector = inspect(bind)
    existing = set(inspector.get_table_names())

    tables = [
        t for t in Base.metadata.sorted_tables
        if t.name not in existing
    ]
    for t in tables:
        t.create(bind, checkfirst=True)

    # VIEW manutencao_garantia_ativa (itens em garantia ativa)
    op.execute("""
        CREATE OR REPLACE VIEW manutencao_garantia_ativa AS
        SELECT
            i.id AS item_id,
            o.id AS os_id,
            o.veiculo_id,
            o.oficina_id,
            i.descricao,
            i.garantia_dias,
            o.data_encerramento::date AS emitida_em,
            (o.data_encerramento::date
                + i.garantia_dias * INTERVAL '1 day')::date AS expira_em
        FROM os_item_linha i
        JOIN os_manutencao o ON o.id = i.os_id
        WHERE o.status = 'encerrada'
          AND o.deleted_at IS NULL
          AND i.garantia_dias > 0
          AND (o.data_encerramento
               + i.garantia_dias * INTERVAL '1 day') > NOW();
    """)


def downgrade() -> None:
    """Drop na ordem reversa das FKs."""
    from app.database import Base
    from app import models  # noqa: F401

    op.execute("DROP VIEW IF EXISTS manutencao_garantia_ativa CASCADE;")

    bind = op.get_bind()
    # Drop na ordem reversa (respeita FKs)
    for t in reversed(Base.metadata.sorted_tables):
        t.drop(bind, checkfirst=True)
