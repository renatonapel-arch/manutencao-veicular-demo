"""APScheduler: sync automático de veículos (Frota/Patrimônio → Manutenção).

#0164: veículo novo (UCQ5D37) comprado pela Napel não aparecia no dropdown
de Nova OS. Causa raiz: o sync real (patrimonial_client.sync_veiculos) já
existia e funciona — mas só era chamado pelo botão manual admin
POST /admin/sync-frota. Sem alguém lembrar de clicar, veículo novo nunca
entrava. Este job substitui o mock anterior e roda sozinho de hora em hora,
chamando exatamente a mesma função do botão admin.
"""
import asyncio
import logging
import os

from ..database import SessionLocal
from ..integrations.patrimonial_client import sync_veiculos

log = logging.getLogger("manutencao.scheduler")


def sync_veiculos_job() -> None:
    """Job de hora em hora — mesmo sync_veiculos() do botão admin/sync-frota."""
    async def _run():
        async with SessionLocal() as db:
            return await sync_veiculos(db)

    try:
        result = asyncio.run(_run())
        log.info("Sync Frota automático: %s", result)
    except Exception as e:
        log.warning("Sync Frota automático falhou (tenta de novo na próxima hora): %s", e)


def start_scheduler() -> None:
    if os.environ.get("DISABLE_SCHEDULER", "false").lower() in ("1", "true", "yes"):
        log.info("Scheduler de sync (Frota) desligado (DISABLE_SCHEDULER=true)")
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except Exception as e:
        log.warning("APScheduler indisponível: %s", e)
        return

    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(sync_veiculos_job, trigger=CronTrigger(minute=0), id="sync-frota-veiculos")
    sched.start()
    log.info("Scheduler iniciado: sync Frota de hora em hora (minuto 0)")
