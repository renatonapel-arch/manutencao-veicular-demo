"""Teste de idempotência do import Pipefy.

Simula rodar o script 2x sem duplicar OS. UNIQUE(pipefy_card_id) + dedup no script.
"""
from decimal import Decimal

import pytest
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.models import OrdemServico


async def test_pipefy_card_id_e_unique(db, admin_user, veiculo):
    """Constraint UNIQUE(pipefy_card_id) impede duplicidade no banco."""
    os1 = OrdemServico(
        pipefy_card_id="12345",
        veiculo_id=veiculo.id, filial_id=veiculo.filial_id,
        tipo_os="corretiva_manual", status="encerrada",
        tipo_destino="oficina_terceirizada",
        km_veiculo=100, valor_total=Decimal("100"),
        aberto_por_user_id=admin_user.id,
    )
    db.add(os1)
    await db.commit()

    # Tentativa de inserir OUTRA com o mesmo pipefy_card_id deve falhar
    os2 = OrdemServico(
        pipefy_card_id="12345",  # mesmo!
        veiculo_id=veiculo.id, filial_id=veiculo.filial_id,
        tipo_os="corretiva_manual", status="encerrada",
        tipo_destino="oficina_terceirizada",
        km_veiculo=200, valor_total=Decimal("200"),
        aberto_por_user_id=admin_user.id,
    )
    db.add(os2)
    with pytest.raises(IntegrityError):
        await db.commit()


async def test_pipefy_card_id_null_e_permitido(db, admin_user, veiculo):
    """OS criadas manualmente (não vem do Pipefy) têm pipefy_card_id=NULL.

    Múltiplas OS com NULL devem coexistir (SQL padrão: NULL != NULL).
    """
    os1 = OrdemServico(
        pipefy_card_id=None,
        veiculo_id=veiculo.id, filial_id=veiculo.filial_id,
        tipo_os="corretiva_manual", status="aberta",
        tipo_destino="oficina_terceirizada",
        km_veiculo=100, valor_total=Decimal("0"),
        aberto_por_user_id=admin_user.id,
    )
    db.add(os1)
    await db.commit()

    os2 = OrdemServico(
        pipefy_card_id=None,
        veiculo_id=veiculo.id, filial_id=veiculo.filial_id,
        tipo_os="corretiva_manual", status="aberta",
        tipo_destino="oficina_terceirizada",
        km_veiculo=200, valor_total=Decimal("0"),
        aberto_por_user_id=admin_user.id,
    )
    db.add(os2)
    await db.commit()  # Não deve dar erro

    total = (await db.execute(
        select(func.count()).select_from(OrdemServico)
    )).scalar_one()
    assert total == 2
