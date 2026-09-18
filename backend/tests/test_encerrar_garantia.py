"""Encerrar em garantia (#0177): gestor fecha OS sem custo/NF/foto, de qualquer
estado ativo. Marca encerrada_em_garantia, zera valor, exige motivo, só gestor."""
import uuid

import pytest
from sqlalchemy import select

from app import models
from app import service as svc
from app.models import OrdemServico, VeiculoSnapshot


async def _os(db, status="aguardando_orcamento", filial_id=1, valor="120.00"):
    db.add(VeiculoSnapshot(id=1, veiculo_patrimonial_id=1, frota_external_id="e1",
           placa="BEE2A87", modelo="CG 160 FAN", tipo="moto", km_atual=1000,
           filial_id=filial_id, ativo=True))
    await db.flush()
    o = OrdemServico(
        request_id=uuid.uuid4(), veiculo_id=1, filial_id=filial_id,
        aberto_por_user_id=1, tipo_os="corretiva_manual", km_veiculo=1000,
        status=status, descricao_problema="Moto fumando motor",
        valor_total=valor,
    )
    db.add(o)
    await db.commit()
    await db.refresh(o)
    return o


async def test_gestor_encerra_em_garantia_de_aguardando_orcamento(db, admin_user):
    o = await _os(db, status="aguardando_orcamento", valor="120.00")
    r = await svc.encerrar_em_garantia(db, o.id, admin_user, motivo="troca junta motor em garantia")
    assert r.status == "encerrada"
    assert r.encerrada_em_garantia is True
    assert r.valor_total == 0
    assert r.data_encerramento is not None
    assert r.garantia_observacoes == "troca junta motor em garantia"


async def test_encerra_garantia_sem_nf_foto_item(db, admin_user):
    # OS crua, sem anexos nem itens — tem que fechar mesmo assim
    o = await _os(db, status="em_execucao", valor="0.00")
    r = await svc.encerrar_em_garantia(db, o.id, admin_user, motivo="garantia")
    assert r.status == "encerrada" and r.encerrada_em_garantia is True


async def test_motivo_obrigatorio(db, admin_user):
    o = await _os(db)
    with pytest.raises(Exception) as ei:
        await svc.encerrar_em_garantia(db, o.id, admin_user, motivo="")
    assert "Motivo" in str(ei.value)


async def test_nao_gestor_recebe_403(db, motorista_user):
    o = await _os(db, filial_id=1)
    with pytest.raises(Exception) as ei:
        await svc.encerrar_em_garantia(db, o.id, motorista_user, motivo="garantia")
    assert "403" in str(ei.value) or "gestor" in str(ei.value).lower()


async def test_os_ja_finalizada_400(db, admin_user):
    o = await _os(db, status="encerrada")
    with pytest.raises(Exception) as ei:
        await svc.encerrar_em_garantia(db, o.id, admin_user, motivo="garantia")
    assert "finalizada" in str(ei.value).lower() or "400" in str(ei.value)


async def test_responsavel_filial_tambem_encerra(db, responsavel_user):
    o = await _os(db, filial_id=1)  # responsavel_user é filial_responsavel na filial 1
    r = await svc.encerrar_em_garantia(db, o.id, responsavel_user, motivo="garantia")
    assert r.status == "encerrada" and r.encerrada_em_garantia is True
