"""Endpoints admin — reset de dados operacionais para começar testes do zero."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_role
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
