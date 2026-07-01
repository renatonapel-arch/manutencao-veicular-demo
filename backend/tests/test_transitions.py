"""Testes das 9 transições — 9 válidas + 11 inválidas.

Executa direto no service (sem HTTP), pra isolar máquina de estados
da autorização e do transporte.
"""
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app import service
from tests.conftest import make_os


# ============================================================
# 9 TRANSIÇÕES VÁLIDAS
# ============================================================

@pytest.mark.parametrize("de,para", [
    ("rascunho", "aberta"),
    ("aberta", "em_triagem"),
    ("em_triagem", "aguardando_orcamento"),
    ("aguardando_orcamento", "aguardando_aprovacao"),
    ("aguardando_aprovacao", "em_execucao"),           # aprovar
    ("aguardando_aprovacao", "aguardando_orcamento"),  # pedir 2º
    ("em_execucao", "aguardando_peca"),
    ("aguardando_peca", "em_execucao"),
    ("em_execucao", "encerrada"),
])
async def test_transicao_valida(db, admin_user, veiculo, de, para):
    os = await make_os(db, admin_user, veiculo, status=de)
    result = await service.transicionar(db, os.id, para, admin_user)
    assert result.status == para
    if para == "encerrada":
        assert result.data_encerramento is not None


# ============================================================
# 11 TRANSIÇÕES INVÁLIDAS
# ============================================================

@pytest.mark.parametrize("de,para", [
    ("rascunho", "em_execucao"),          # pula 4 estados
    ("aberta", "aguardando_orcamento"),   # pula em_triagem
    ("aberta", "encerrada"),              # pula tudo
    ("em_triagem", "em_execucao"),        # pula aguardando_*
    ("aguardando_orcamento", "em_execucao"),  # pula aprovação
    ("em_execucao", "aguardando_orcamento"),  # não pode retroceder
    ("em_execucao", "aberta"),                # retrocesso proibido
    ("encerrada", "aberta"),              # terminal
    ("encerrada", "em_execucao"),         # terminal
    ("cancelada", "em_execucao"),         # terminal
    ("cancelada", "aberta"),              # terminal
])
async def test_transicao_invalida(db, admin_user, veiculo, de, para):
    os = await make_os(db, admin_user, veiculo, status=de)
    with pytest.raises(HTTPException) as exc:
        await service.transicionar(db, os.id, para, admin_user)
    assert exc.value.status_code == 400
    assert "inválida" in exc.value.detail.lower()


# ============================================================
# TERMINAIS: encerrada e cancelada não têm saída
# ============================================================

async def test_encerrada_e_cancelada_sao_terminais(db, admin_user, veiculo):
    assert service.TRANSICOES_VALIDAS["encerrada"] == set()
    assert service.TRANSICOES_VALIDAS["cancelada"] == set()


# ============================================================
# CANCELAR PRECISA DE MOTIVO
# ============================================================

async def test_cancelar_sem_motivo_falha(db, admin_user, veiculo):
    os = await make_os(db, admin_user, veiculo, status="aberta")
    with pytest.raises(HTTPException) as exc:
        await service.transicionar(db, os.id, "cancelada", admin_user, motivo=None)
    assert exc.value.status_code == 400
    assert "motivo" in exc.value.detail.lower()


async def test_cancelar_com_motivo_ok(db, admin_user, veiculo):
    os = await make_os(db, admin_user, veiculo, status="aberta")
    result = await service.transicionar(
        db, os.id, "cancelada", admin_user, motivo="teste"
    )
    assert result.status == "cancelada"
    assert result.motivo_reprovacao == "teste"


# ============================================================
# CANCELAR DE QUALQUER ESTADO ATIVO É PERMITIDO
# ============================================================

@pytest.mark.parametrize("de", [
    "rascunho", "aberta", "em_triagem",
    "aguardando_orcamento", "aguardando_aprovacao",
    "em_execucao", "aguardando_peca",
])
async def test_cancelar_de_qualquer_estado_ativo(db, admin_user, veiculo, de):
    os = await make_os(db, admin_user, veiculo, status=de)
    result = await service.transicionar(
        db, os.id, "cancelada", admin_user, motivo="teste"
    )
    assert result.status == "cancelada"
