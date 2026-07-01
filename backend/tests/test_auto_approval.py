"""Testes de auto-aprovação — fronteiras do teto R$ 500,00.

Regras:
- valor_total < R$ 500 → auto-aprova (status=em_execucao, motivo_aprovacao='auto')
- valor_total >= R$ 500 → aguardando_aprovacao (motivo_aprovacao=None)
- valor_total <= 0 → HTTPException 400 (bloqueio pra evitar aprovar OS vazia)
- aprovado_por_user_id SEMPRE None quando auto (v3: sem SYSTEM_USER_ID)
"""
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app import service
from tests.conftest import make_os


async def test_auto_aprovacao_499_99_auto(db, admin_user, veiculo):
    """R$ 499,99 → auto-aprova."""
    os = await make_os(
        db, admin_user, veiculo,
        status="aguardando_orcamento",
        valor_total=Decimal("499.99"),
    )
    result = await service.submeter_orcamento(db, os.id, admin_user)
    assert result.status == "em_execucao"
    assert result.motivo_aprovacao == "auto"
    assert result.aprovado_por_user_id is None
    assert result.aprovado_em is not None


async def test_auto_aprovacao_500_00_manual(db, admin_user, veiculo):
    """R$ 500,00 (== teto) → NÃO auto-aprova, vai pra aguardando_aprovacao."""
    os = await make_os(
        db, admin_user, veiculo,
        status="aguardando_orcamento",
        valor_total=Decimal("500.00"),
    )
    result = await service.submeter_orcamento(db, os.id, admin_user)
    assert result.status == "aguardando_aprovacao"
    assert result.motivo_aprovacao is None
    assert result.aprovado_por_user_id is None


async def test_auto_aprovacao_500_01_manual(db, admin_user, veiculo):
    """R$ 500,01 (> teto) → NÃO auto-aprova."""
    os = await make_os(
        db, admin_user, veiculo,
        status="aguardando_orcamento",
        valor_total=Decimal("500.01"),
    )
    result = await service.submeter_orcamento(db, os.id, admin_user)
    assert result.status == "aguardando_aprovacao"
    assert result.motivo_aprovacao is None


async def test_valor_zero_bloqueia(db, admin_user, veiculo):
    """OS sem itens (valor_total=0) → HTTPException 400."""
    os = await make_os(
        db, admin_user, veiculo,
        status="aguardando_orcamento",
        valor_total=Decimal("0"),
    )
    with pytest.raises(HTTPException) as exc:
        await service.submeter_orcamento(db, os.id, admin_user)
    assert exc.value.status_code == 400
    assert "item" in exc.value.detail.lower()


async def test_valor_negativo_bloqueia(db, admin_user, veiculo):
    """Valor negativo (inválido) → HTTPException 400."""
    os = await make_os(
        db, admin_user, veiculo,
        status="aguardando_orcamento",
        valor_total=Decimal("-100"),
    )
    with pytest.raises(HTTPException) as exc:
        await service.submeter_orcamento(db, os.id, admin_user)
    assert exc.value.status_code == 400


async def test_submeter_de_estado_errado_falha(db, admin_user, veiculo):
    """Só submete orçamento a partir de aguardando_orcamento."""
    os = await make_os(
        db, admin_user, veiculo,
        status="rascunho", valor_total=Decimal("100"),
    )
    with pytest.raises(HTTPException) as exc:
        await service.submeter_orcamento(db, os.id, admin_user)
    assert exc.value.status_code == 400


async def test_aprovar_manual_grava_user_id(db, admin_user, veiculo):
    """Aprovação manual grava aprovado_por_user_id = user do request."""
    os = await make_os(
        db, admin_user, veiculo,
        status="aguardando_aprovacao",
        valor_total=Decimal("1000"),
    )
    result = await service.aprovar(db, os.id, admin_user, observacoes="ok")
    assert result.status == "em_execucao"
    assert result.motivo_aprovacao == "manual"
    assert result.aprovado_por_user_id == admin_user.id
