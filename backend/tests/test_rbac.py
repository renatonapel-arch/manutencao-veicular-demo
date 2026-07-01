"""Testes RBAC — 4 papéis × transições permitidas/proibidas.

Contrato:
- admin: TUDO em qualquer filial
- filial_responsavel: TUDO só na sua filial
- motorista: só abre suas próprias OS (rascunho → aberta)
- mecanico_interno: só em execução de OS destinada a ele
"""
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app import service
from tests.conftest import make_os


# ============================================================
# ADMIN — passa em qualquer coisa
# ============================================================

async def test_admin_aprovar(db, admin_user, veiculo):
    os = await make_os(
        db, admin_user, veiculo,
        status="aguardando_aprovacao", valor_total=Decimal("1000"),
    )
    result = await service.aprovar(db, os.id, admin_user)
    assert result.status == "em_execucao"


async def test_admin_encerra_de_qualquer_filial(db, admin_user, veiculo):
    # veiculo é filial 1, admin não tem membro pra filial 1 mas passa mesmo assim
    os = await make_os(db, admin_user, veiculo, status="em_execucao")
    result = await service.transicionar(db, os.id, "encerrada", admin_user)
    assert result.status == "encerrada"


# ============================================================
# FILIAL_RESPONSAVEL — só na própria filial
# ============================================================

async def test_responsavel_aprova_propria_filial(db, admin_user, responsavel_user, veiculo):
    os = await make_os(
        db, admin_user, veiculo,   # veiculo é filial 1
        status="aguardando_aprovacao", valor_total=Decimal("1000"),
    )
    result = await service.aprovar(db, os.id, responsavel_user)
    assert result.status == "em_execucao"


async def test_responsavel_bloqueado_em_outra_filial(db, admin_user, responsavel_user):
    """Responsável de filial 1 tenta aprovar OS da filial 2 → 403."""
    from app import models
    v2 = models.VeiculoSnapshot(
        veiculo_patrimonial_id=2002, placa="OTR9Z99",
        modelo="Outro", tipo="carro", filial_id=2, km_atual=50,
        ativo=True,
    )
    db.add(v2)
    await db.commit()
    os = await make_os(
        db, admin_user, v2,
        status="aguardando_aprovacao", valor_total=Decimal("1000"),
    )
    with pytest.raises(HTTPException) as exc:
        await service.aprovar(db, os.id, responsavel_user)
    assert exc.value.status_code == 403


# ============================================================
# MOTORISTA — só abre próprias OS
# ============================================================

async def test_motorista_abre_propria_os(db, admin_user, motorista_user, veiculo):
    # Motorista tem funcionario_id=300; OS precisa ter funcionario_relator_id=300
    os = await make_os(
        db, admin_user, veiculo,
        status="rascunho",
        funcionario_relator_id=300,
    )
    result = await service.transicionar(db, os.id, "aberta", motorista_user)
    assert result.status == "aberta"


async def test_motorista_bloqueado_em_os_de_outro(db, admin_user, motorista_user, veiculo):
    """Motorista tenta abrir OS que outro funcionário reportou → 403."""
    os = await make_os(
        db, admin_user, veiculo,
        status="rascunho",
        funcionario_relator_id=999,  # outro motorista
    )
    with pytest.raises(HTTPException) as exc:
        await service.transicionar(db, os.id, "aberta", motorista_user)
    assert exc.value.status_code == 403


async def test_motorista_nao_pode_aprovar(db, admin_user, motorista_user, veiculo):
    os = await make_os(
        db, admin_user, veiculo,
        status="aguardando_aprovacao", valor_total=Decimal("100"),
        funcionario_relator_id=300,
    )
    with pytest.raises(HTTPException) as exc:
        await service.aprovar(db, os.id, motorista_user)
    assert exc.value.status_code == 403


# ============================================================
# MECANICO_INTERNO — só transições operacionais em OS dele
# ============================================================

async def test_mecanico_encerra_os_interno(db, admin_user, mecanico_user, veiculo):
    os = await make_os(
        db, admin_user, veiculo,
        status="em_execucao", tipo_destino="mecanico_interno",
    )
    result = await service.transicionar(db, os.id, "encerrada", mecanico_user)
    assert result.status == "encerrada"


async def test_mecanico_bloqueado_em_os_terceirizada(db, admin_user, mecanico_user, veiculo):
    """OS destinada a oficina terceirizada → mecânico não pode operar."""
    os = await make_os(
        db, admin_user, veiculo,
        status="em_execucao", tipo_destino="oficina_terceirizada",
    )
    with pytest.raises(HTTPException) as exc:
        await service.transicionar(db, os.id, "encerrada", mecanico_user)
    assert exc.value.status_code == 403


async def test_mecanico_nao_pode_aprovar(db, admin_user, mecanico_user, veiculo):
    """Mecânico interno não pode aprovar — só admin/filial_responsavel."""
    os = await make_os(
        db, admin_user, veiculo,
        status="aguardando_aprovacao", valor_total=Decimal("100"),
        tipo_destino="mecanico_interno",
    )
    with pytest.raises(HTTPException) as exc:
        await service.aprovar(db, os.id, mecanico_user)
    assert exc.value.status_code == 403
