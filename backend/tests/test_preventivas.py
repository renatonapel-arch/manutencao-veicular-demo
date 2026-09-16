"""Engine de preventivas (gerar_preventivas) — 4 caminhos.

Cobre a regra de âncora documentada em jobs/alertas_preventivas.py:
baseline na 1a vez (sem enxurrada), vencimento por km, por dias, e dedup mensal.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from app import models
from app.jobs.alertas_preventivas import _gerar_preventivas_async
from app.models import OrdemServico, PlanoPreventiva, PreventivaGerada, VeiculoSnapshot


@pytest.fixture(autouse=True)
def _no_notify(monkeypatch):
    async def _noop(*a, **k):
        return None
    monkeypatch.setattr("app.integrations.evolution_whatsapp.notify_os_transition", _noop)


async def _seed(db):
    db.add(models.User(id=1, email="sys@x", role="admin", nome="Sys", senha_hash="x"))
    db.add(VeiculoSnapshot(
        id=1, veiculo_patrimonial_id=1, frota_external_id="e1", placa="AAA1A11",
        modelo="CG 160 FAN", tipo="moto", km_atual=10000, filial_id=1, ativo=True,
    ))
    db.add(PlanoPreventiva(id=1, modelo_veiculo="CG 160 FAN", item="Troca de óleo",
                           km_intervalo=1000, dias_intervalo=None, antecedencia_dias=0, ativo=True))
    db.add(PlanoPreventiva(id=2, modelo_veiculo="CG 160 FAN", item="Revisão elétrica",
                           km_intervalo=None, dias_intervalo=30, antecedencia_dias=7, ativo=True))
    await db.commit()


async def test_primeira_vez_so_baseline_sem_os(db):
    await _seed(db)
    r = await _gerar_preventivas_async(db, hoje=datetime(2026, 9, 16, 12))
    assert r["geradas"] == 0        # nada de enxurrada no 1o dia
    assert r["baselines"] == 2      # 1 âncora por plano
    n_os = (await db.execute(select(func.count()).select_from(OrdemServico))).scalar_one()
    assert n_os == 0
    anc = (await db.execute(
        select(PreventivaGerada).where(PreventivaGerada.plano_id == 1)
    )).scalars().first()
    assert anc.km_referencia == 10000 and anc.os_id is None


async def test_dedup_mesmo_mes(db):
    await _seed(db)
    await _gerar_preventivas_async(db, hoje=datetime(2026, 9, 16, 12))
    r2 = await _gerar_preventivas_async(db, hoje=datetime(2026, 9, 20, 12))
    assert r2["geradas"] == 0 and r2["baselines"] == 0  # mês já ocupado


async def test_vence_por_km(db):
    await _seed(db)
    await _gerar_preventivas_async(db, hoje=datetime(2026, 9, 16, 12))
    v = await db.get(VeiculoSnapshot, 1)
    v.km_atual = 11200  # rodou 1200 > intervalo 1000
    await db.commit()
    r = await _gerar_preventivas_async(db, hoje=datetime(2026, 10, 16, 12))
    assert r["geradas"] >= 1
    os_oleo = (await db.execute(
        select(OrdemServico).where(OrdemServico.categoria == "Motor")
    )).scalars().all()
    assert len(os_oleo) == 1
    assert os_oleo[0].tipo_os == "preventiva_automatica"
    assert os_oleo[0].status == "aberta"
    # nova âncora = km da geração
    nova = (await db.execute(
        select(PreventivaGerada).where(
            PreventivaGerada.plano_id == 1, PreventivaGerada.os_id.isnot(None)
        )
    )).scalars().first()
    assert nova.km_referencia == 11200


async def test_nao_vence_por_km_abaixo_do_intervalo(db):
    await _seed(db)
    await _gerar_preventivas_async(db, hoje=datetime(2026, 9, 16, 12))
    v = await db.get(VeiculoSnapshot, 1)
    v.km_atual = 10500  # rodou só 500 < 1000
    await db.commit()
    r = await _gerar_preventivas_async(db, hoje=datetime(2026, 10, 16, 12))
    os_oleo = (await db.execute(
        select(OrdemServico).where(OrdemServico.categoria == "Motor")
    )).scalars().all()
    assert len(os_oleo) == 0  # não venceu por km


async def test_vence_por_dias(db):
    await _seed(db)
    await _gerar_preventivas_async(db, hoje=datetime(2026, 9, 16, 12))
    # plano2: 30 dias, antecedência 7 => vence a partir de 2026-10-09
    r = await _gerar_preventivas_async(db, hoje=datetime(2026, 10, 16, 12))
    os_eletr = (await db.execute(
        select(OrdemServico).where(OrdemServico.categoria == "Elétrica")
    )).scalars().all()
    assert len(os_eletr) == 1
    assert os_eletr[0].tipo_os == "preventiva_automatica"


async def test_km_zero_nao_dispara_por_km(db):
    """Com km_atual=0 (Patrimônio ainda não corrigiu), a regra por km não vence."""
    await _seed(db)
    v = await db.get(VeiculoSnapshot, 1)
    v.km_atual = 0
    await db.commit()
    await _gerar_preventivas_async(db, hoje=datetime(2026, 9, 16, 12))
    v = await db.get(VeiculoSnapshot, 1)
    v.km_atual = 0
    await db.commit()
    await _gerar_preventivas_async(db, hoje=datetime(2026, 10, 16, 12))
    os_oleo = (await db.execute(
        select(OrdemServico).where(OrdemServico.categoria == "Motor")
    )).scalars().all()
    assert len(os_oleo) == 0  # km=0 nunca dispara a regra por km
