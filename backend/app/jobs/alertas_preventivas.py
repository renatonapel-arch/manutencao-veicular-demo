"""APScheduler: gera OS preventivas automaticamente + (placeholder) alerta OS atrasada.

gerar_preventivas() saiu do mock (#0164 / task_848a9f35): agora itera os planos
preventivos ativos × veículos e abre 1 OS `preventiva_automatica` quando o veículo
atinge o intervalo de km OU de dias do plano.

REGRA DE ÂNCORA (documentada de propósito — foi a decisão de design):
- A "última vez que este plano foi feito neste veículo" vem da última linha em
  `preventiva_gerada` para o par (veículo, plano): `km_referencia` + `data_geracao`.
- PRIMEIRA VEZ que o job vê um par (veículo, plano) sem histórico: grava uma
  linha-âncora (baseline) com `os_id=NULL` e `km_referencia=km_atual` e NÃO abre OS.
  Isso evita uma enxurrada de OS no primeiro dia sobre uma frota antiga cujo
  histórico de manutenção o sistema não conhece. A contagem começa daqui.
- Vencimento por km: `km_atual >= km_referencia + km_intervalo` (precisa km_atual > 0).
- Vencimento por dias: `hoje >= data_geracao + (dias_intervalo - antecedencia_dias)`.
- Dedup: no máximo 1 linha por (veículo, plano, ano_mes) — constraint do banco.

Enquanto o Patrimônio não puser o km real no ar (hoje km_atual=0 em vários),
a regra por km simplesmente não dispara — de propósito, não é bug. A regra por
dias funciona independente do km.
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import SessionLocal
from ..models import (
    OrdemServico, PlanoPreventiva, PreventivaGerada, VeiculoSnapshot,
)

log = logging.getLogger("manutencao.scheduler")

# Mapa item do plano → categoria de OS (mesma lista fixa do pipe/checklist).
_CATEGORIA_KEYWORDS = {
    "óleo": "Motor", "oleo": "Motor", "motor": "Motor", "correia": "Motor",
    "pneu": "Pneu", "roda": "Pneu",
    "freio": "Pastilha / Lona", "pastilha": "Pastilha / Lona", "lona": "Pastilha / Lona",
    "relação": "Relação", "relacao": "Relação", "corrente": "Relação",
    "lâmpada": "Lâmpadas", "lampada": "Lâmpadas", "farol": "Lâmpadas",
    "elétr": "Elétrica", "eletr": "Elétrica",
    "bateria": "Bateria",
    "embreagem": "Embreagem",
}


def _categorizar(item: str) -> str:
    low = (item or "").lower()
    for kw, cat in _CATEGORIA_KEYWORDS.items():
        if kw in low:
            return cat
    return "Outros"


async def _gerar_preventivas_async(db: AsyncSession, hoje: datetime | None = None) -> dict:
    hoje = hoje or datetime.utcnow()
    ano_mes = hoje.strftime("%Y-%m")

    veiculos = list((await db.execute(
        select(VeiculoSnapshot).where(VeiculoSnapshot.ativo.is_(True))
    )).scalars().all())
    planos = list((await db.execute(
        select(PlanoPreventiva).where(PlanoPreventiva.ativo.is_(True))
    )).scalars().all())

    # Indexa planos por modelo normalizado.
    planos_por_modelo: dict[str, list[PlanoPreventiva]] = {}
    for p in planos:
        planos_por_modelo.setdefault((p.modelo_veiculo or "").strip().lower(), []).append(p)

    geradas = baselines = skipped = 0

    for v in veiculos:
        for p in planos_por_modelo.get((v.modelo or "").strip().lower(), []):
            # Dedup do mês: 1 linha por (veiculo, plano, ano_mes).
            ja_no_mes = (await db.execute(
                select(PreventivaGerada.id).where(
                    PreventivaGerada.veiculo_id == v.id,
                    PreventivaGerada.plano_id == p.id,
                    PreventivaGerada.ano_mes == ano_mes,
                )
            )).first()
            if ja_no_mes:
                skipped += 1
                continue

            # Última âncora do par (veiculo, plano): a linha mais recente.
            ultima = (await db.execute(
                select(PreventivaGerada)
                .where(
                    PreventivaGerada.veiculo_id == v.id,
                    PreventivaGerada.plano_id == p.id,
                )
                .order_by(PreventivaGerada.data_geracao.desc())
                .limit(1)
            )).scalars().first()

            # Primeira vez que vemos o par → grava baseline e não abre OS.
            if ultima is None:
                db.add(PreventivaGerada(
                    veiculo_id=v.id, plano_id=p.id, os_id=None,
                    ano_mes=ano_mes, km_referencia=v.km_atual or 0,
                ))
                baselines += 1
                continue

            venceu = False
            if p.km_intervalo and (v.km_atual or 0) > 0 and ultima.km_referencia is not None:
                if (v.km_atual or 0) >= ultima.km_referencia + p.km_intervalo:
                    venceu = True
            if not venceu and p.dias_intervalo and ultima.data_geracao is not None:
                anteced = p.antecedencia_dias or 0
                ref = ultima.data_geracao
                if ref.tzinfo is not None:
                    ref = ref.replace(tzinfo=None)
                if hoje >= ref + timedelta(days=p.dias_intervalo - anteced):
                    venceu = True

            if not venceu:
                skipped += 1
                continue

            # Vencido → abre OS preventiva + registra a nova âncora.
            os_ = OrdemServico(
                request_id=uuid.uuid4(),
                veiculo_id=v.id,
                filial_id=v.filial_id,
                aberto_por_user_id=1,  # sistema (admin seed) — job automático
                tipo_os="preventiva_automatica",
                tipo_destino="oficina_terceirizada",
                km_veiculo=v.km_atual or 0,
                km_api_snapshot=v.km_atual or 0,
                descricao_problema=f"[Preventiva automática] {p.item}",
                categoria=_categorizar(p.item),
                status="aberta",
                data_abertura=hoje,
                valor_total=Decimal("0"),
                desconto_ajuste=Decimal("0"),
                economia_napel_total=Decimal("0"),
            )
            db.add(os_)
            await db.flush()
            db.add(PreventivaGerada(
                veiculo_id=v.id, plano_id=p.id, os_id=os_.id,
                ano_mes=ano_mes, km_referencia=v.km_atual or 0,
            ))
            geradas += 1

            try:
                from ..integrations.evolution_whatsapp import notify_os_transition
                await notify_os_transition(db, os_, "aberta")
            except Exception as exc:  # noqa: BLE001
                log.warning("Notify preventiva->OS falhou (veic %s): %s", v.placa, exc)

    await db.commit()
    return {"geradas": geradas, "baselines": baselines, "skipped": skipped}


def gerar_preventivas() -> dict:
    """Job diário — abre OS preventivas vencidas. Wrapper sync do scheduler."""
    async def _run():
        async with SessionLocal() as db:
            return await _gerar_preventivas_async(db)
    try:
        result = asyncio.run(_run())
        log.info("gerar_preventivas: %s", result)
        return result
    except Exception as e:  # noqa: BLE001
        log.warning("gerar_preventivas falhou (tenta amanhã): %s", e)
        return {"geradas": 0, "baselines": 0, "skipped": 0, "erro": str(e)}


def alertas_os_atrasada() -> dict:
    """Job 08:15 UTC — alerta OS abertas >5 dias. Ainda mock (fora do escopo #0164)."""
    log.info("Job alertas_os_atrasada: mock (MVP)")
    return {"alertas_disparados": 0}


def start_scheduler() -> None:
    if os.environ.get("DISABLE_SCHEDULER", "false").lower() in ("1", "true", "yes"):
        log.info("Scheduler desligado (DISABLE_SCHEDULER=true)")
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except Exception as e:  # noqa: BLE001
        log.warning("APScheduler indisponível: %s", e)
        return

    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(gerar_preventivas, trigger=CronTrigger(hour=8, minute=0), id="preventivas")
    sched.add_job(alertas_os_atrasada, trigger=CronTrigger(hour=8, minute=15), id="atrasadas")
    sched.start()
    log.info("Scheduler iniciado: preventivas 08:00 UTC, atrasadas 08:15 UTC")
