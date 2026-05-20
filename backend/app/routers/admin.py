"""Endpoints admin — reset + sync com apps Frota e Troca de Óleo."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_role
from ..integrations.oleo_client import sync_trocas_oleo
from ..integrations.patrimonial_client import sync_veiculos
from ..models import (AlertaHistory, AnexosOs, AuditoriaOs, IdempotencyKey,
                      OficinaPadronizada, OrdemServico, OsItemLinha,
                      PlanoPreventiva, PreventivaGerada, TrocaOleoCache,
                      User, VeiculoSnapshot)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reset-operacional")
def reset_dados_operacionais(
    user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    """Apaga TODOS os dados operacionais (OS, anexos, auditoria, alertas, cache).

    Mantém: usuários (auth), veículos (cache Patrimonial), oficinas (catálogo padronizado),
    planos preventivos (configuração base).
    """
    apagados = {
        "anexos_os":       db.query(AnexosOs).delete(synchronize_session=False),
        "os_item_linha":   db.query(OsItemLinha).delete(synchronize_session=False),
        "auditoria_os":    db.query(AuditoriaOs).delete(synchronize_session=False),
        "alert_history":   db.query(AlertaHistory).delete(synchronize_session=False),
        "idempotency_keys":db.query(IdempotencyKey).delete(synchronize_session=False),
        "preventiva_gerada":db.query(PreventivaGerada).delete(synchronize_session=False),
        "troca_oleo_cache":db.query(TrocaOleoCache).delete(synchronize_session=False),
        "os_manutencao":   db.query(OrdemServico).delete(synchronize_session=False),
    }
    db.commit()
    return {
        "ok": True, "operacao": "reset-operacional", "apagados": apagados,
        "mantidos": ["users", "veiculo_snapshot", "oficina_padronizada", "plano_preventiva"],
        "executado_por": user.email,
    }


@router.post("/reset-planos")
def reset_planos(
    user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    """Apaga TODOS os planos preventivos + preventivas geradas."""
    apagados = {
        "preventiva_gerada": db.query(PreventivaGerada).delete(synchronize_session=False),
        "plano_preventiva":  db.query(PlanoPreventiva).delete(synchronize_session=False),
    }
    db.commit()
    return {"ok": True, "operacao": "reset-planos", "apagados": apagados, "executado_por": user.email}


@router.get("/contagens")
def contagens(user: User = Depends(require_role(["admin"])), db: Session = Depends(get_db)):
    return {
        "users":               db.query(User).count(),
        "veiculo_snapshot":    db.query(VeiculoSnapshot).count(),
        "oficina_padronizada": db.query(OficinaPadronizada).count(),
        "plano_preventiva":    db.query(PlanoPreventiva).count(),
        "os_manutencao":       db.query(OrdemServico).count(),
        "os_item_linha":       db.query(OsItemLinha).count(),
        "anexos_os":           db.query(AnexosOs).count(),
        "alert_history":       db.query(AlertaHistory).count(),
        "troca_oleo_cache":    db.query(TrocaOleoCache).count(),
        "auditoria_os":        db.query(AuditoriaOs).count(),
        "preventiva_gerada":   db.query(PreventivaGerada).count(),
        "idempotency_keys":    db.query(IdempotencyKey).count(),
    }


# ============================================================
# Integração real — apps Frota e Troca de Óleo (Fase C)
# ============================================================

@router.post("/sync-frota")
def trigger_sync_frota(
    user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    """Pega veículos do Cadastro Veicular (frota.demos.napel.com.br) e upserta no Manutenção."""
    result = sync_veiculos(db)
    return {"ok": True, "operacao": "sync-frota", **result}


@router.post("/sync-oleo")
def trigger_sync_oleo(
    user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    """Pega trocas de óleo + odometer-logs do app Troca de Óleo.

    - Trocas viram entradas em troca_oleo_cache (aparecem na timeline)
    - KM mais recente de cada veículo atualiza VeiculoSnapshot.km_atual
    """
    result = sync_trocas_oleo(db)
    return {"ok": True, "operacao": "sync-oleo", **result}


@router.post("/sync-all")
def trigger_sync_all(
    user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    """Sync de tudo: primeiro Frota (precisa dos veiculos pra resolver foreign keys do óleo)."""
    frota = sync_veiculos(db)
    oleo = sync_trocas_oleo(db)
    return {"ok": True, "operacao": "sync-all", "frota": frota, "oleo": oleo}


@router.post("/reset-tudo-e-sync")
def reset_e_sync(
    user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    """Cenário do zero: apaga TUDO (incluindo veículos e oficinas) e refaz sync com apps externos.

    Mantém só: usuários (auth) + oficinas (catálogo). Re-importa veículos da Frota
    e trocas de óleo do app Troca de Óleo.
    """
    apagados = {
        "anexos_os":         db.query(AnexosOs).delete(synchronize_session=False),
        "os_item_linha":     db.query(OsItemLinha).delete(synchronize_session=False),
        "auditoria_os":      db.query(AuditoriaOs).delete(synchronize_session=False),
        "alert_history":     db.query(AlertaHistory).delete(synchronize_session=False),
        "idempotency_keys":  db.query(IdempotencyKey).delete(synchronize_session=False),
        "preventiva_gerada": db.query(PreventivaGerada).delete(synchronize_session=False),
        "troca_oleo_cache":  db.query(TrocaOleoCache).delete(synchronize_session=False),
        "os_manutencao":     db.query(OrdemServico).delete(synchronize_session=False),
        "plano_preventiva":  db.query(PlanoPreventiva).delete(synchronize_session=False),
        "veiculo_snapshot":  db.query(VeiculoSnapshot).delete(synchronize_session=False),
    }
    db.commit()
    frota = sync_veiculos(db)
    oleo = sync_trocas_oleo(db)
    return {"ok": True, "operacao": "reset-tudo-e-sync", "apagados": apagados, "frota": frota, "oleo": oleo}
