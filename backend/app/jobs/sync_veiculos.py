"""APScheduler: sync de veículos e trocas de óleo. Mock no MVP."""
import logging

log = logging.getLogger("manutencao.scheduler")


def sync_veiculos_e_trocas() -> dict:
    """Job 02:00 UTC — sync com Patrimonial + Troca-Óleo. Real: TODO[ADR-contratos-APIs-externas]."""
    log.info("sync_veiculos_e_trocas: mock (MVP) — seed já populou as tabelas")
    return {"veiculos_sincronizados": 0, "trocas_oleo_sincronizadas": 0}
