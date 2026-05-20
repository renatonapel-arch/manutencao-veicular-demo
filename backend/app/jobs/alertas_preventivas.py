"""APScheduler: gera OS preventivas + dispara alertas. Mock no MVP."""
import logging
import os
from datetime import datetime

from ..config import settings

log = logging.getLogger("manutencao.scheduler")


def gerar_preventivas() -> dict:
    """Job 08:00 UTC — itera planos e cria OS preventiva quando km/data atinge intervalo."""
    log.info("Job gerar_preventivas: mock (MVP)")
    return {"geradas": 0, "skipped": 0, "alertas_disparados": 0}


def alertas_os_atrasada() -> dict:
    """Job 08:15 UTC — alerta OS abertas >5 dias."""
    log.info("Job alertas_os_atrasada: mock (MVP)")
    return {"alertas_disparados": 0}


def start_scheduler() -> None:
    if os.environ.get("DISABLE_SCHEDULER", "false").lower() in ("1", "true", "yes"):
        log.info("Scheduler desligado (DISABLE_SCHEDULER=true)")
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except Exception as e:
        log.warning("APScheduler indisponível: %s", e)
        return

    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(gerar_preventivas, trigger=CronTrigger(hour=8, minute=0), id="preventivas")
    sched.add_job(alertas_os_atrasada, trigger=CronTrigger(hour=8, minute=15), id="atrasadas")
    sched.start()
    log.info("Scheduler iniciado: preventivas 08:00 UTC, atrasadas 08:15 UTC")
