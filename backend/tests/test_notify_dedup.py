"""Prova o dedup de notificação por telefone (causa raiz da enxurrada da OS #508).

Cenário real: "liberar geral" criou muitos membros admin/filial_responsavel
SEM telefone. Cada um caía no fallback RENATO_WHATSAPP → o dono recebia N
cópias idênticas do mesmo evento. O dedup por número resolve.
"""
import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app import models
from app.integrations import evolution_whatsapp as ew
from app.models import AlertaHistory, MembroManutencao, OrdemServico, User, VeiculoSnapshot


async def _cenario(db, n_sem_telefone: int, com_telefone: list[str]):
    # veículo + OS aberta na filial 2
    db.add(VeiculoSnapshot(id=1, veiculo_patrimonial_id=1, frota_external_id="e1",
           placa="BEO7H12", modelo="STRADA", tipo="carro", km_atual=1000,
           filial_id=2, ativo=True))
    await db.flush()
    os_ = OrdemServico(
        request_id=uuid.uuid4(), veiculo_id=1, filial_id=2,
        aberto_por_user_id=1, tipo_os="corretiva_checklist",
        km_veiculo=1000, status="aberta", descricao_problema="[Checklist mensal] X",
    )
    db.add(os_)
    # N membros admin SEM telefone (global, filial 0)
    for i in range(n_sem_telefone):
        u = User(email=f"semtel{i}@x", role="admin", nome=f"Sem Tel {i}",
                 senha_hash="x", telefone=None)
        db.add(u); await db.flush()
        db.add(MembroManutencao(user_id=u.id, filial_id=0, papel="admin", ativo=True))
    # membros COM telefone
    for j, tel in enumerate(com_telefone):
        u = User(email=f"comtel{j}@x", role="operador", nome=f"Com Tel {j}",
                 senha_hash="x", telefone=tel)
        db.add(u); await db.flush()
        db.add(MembroManutencao(user_id=u.id, filial_id=2, papel="filial_responsavel", ativo=True))
    await db.commit()
    # Recarrega com veículo eager (render() acessa os.veiculo — igual o código real faz)
    os_ = (await db.execute(
        select(OrdemServico).options(selectinload(OrdemServico.veiculo))
        .where(OrdemServico.id == os_.id)
    )).scalars().first()
    return os_


async def test_dedup_colapsa_sem_telefone_no_fallback(db, monkeypatch):
    # força modo real (EVOLUTION_ENABLED=true) + captura envios sem HTTP
    monkeypatch.setattr(ew.settings, "EVOLUTION_ENABLED", True)
    monkeypatch.setattr(ew.settings, "RENATO_WHATSAPP", "5544999413366")
    enviados = []
    monkeypatch.setattr(ew, "_enviar_via_notifier",
                        lambda tel, msg, tag: (enviados.append(tel) or {"sent": True}))

    os_ = await _cenario(db, n_sem_telefone=11, com_telefone=["5544999990000"])
    r = await ew.notify_os_transition(db, os_, "aberta")

    # 11 sem telefone colapsam em 1 (fallback do dono) + 1 real = 2 envios, não 12
    assert len(enviados) == 2, f"esperava 2 envios, veio {len(enviados)}: {enviados}"
    assert enviados.count("5544999413366") == 1, "dono só pode receber 1"
    assert "5544999990000" in enviados
    assert r["sent"] == 2

    # AlertaHistory também deduplica: 2 linhas, não 12
    n = (await db.execute(
        select(func.count()).select_from(AlertaHistory).where(AlertaHistory.os_id == os_.id)
    )).scalar_one()
    assert n == 2


async def test_dedup_idempotente_um_por_numero(db, monkeypatch):
    """Mesmo com todos sem telefone, dono recebe exatamente 1."""
    monkeypatch.setattr(ew.settings, "EVOLUTION_ENABLED", True)
    monkeypatch.setattr(ew.settings, "RENATO_WHATSAPP", "5544999413366")
    enviados = []
    monkeypatch.setattr(ew, "_enviar_via_notifier",
                        lambda tel, msg, tag: (enviados.append(tel) or {"sent": True}))

    os_ = await _cenario(db, n_sem_telefone=25, com_telefone=[])
    await ew.notify_os_transition(db, os_, "aberta")
    assert enviados == ["5544999413366"], f"dono deveria receber exatamente 1, veio {enviados}"
