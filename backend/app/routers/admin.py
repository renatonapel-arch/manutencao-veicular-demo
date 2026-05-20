"""Endpoints admin — reset de dados operacionais para começar testes do zero."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_role
from ..models import (AlertaHistory, AnexosOs, AuditoriaOs, IdempotencyKey,
                      OrdemServico, OsItemLinha, PreventivaGerada,
                      TrocaOleoCache, User)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reset-operacional")
def reset_dados_operacionais(
    user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
):
    """Apaga TODOS os dados operacionais (OS, anexos, auditoria, alertas, cache).

    Mantém: usuários (auth), veículos (cache Patrimonial), oficinas (catálogo padronizado),
    planos preventivos (configuração base).

    Reversível: re-roda o seed via reboot do container OU continua usando vazio.
    """
    apagados = {}

    apagados["anexos_os"] = db.query(AnexosOs).delete(synchronize_session=False)
    apagados["os_item_linha"] = db.query(OsItemLinha).delete(synchronize_session=False)
    apagados["auditoria_os"] = db.query(AuditoriaOs).delete(synchronize_session=False)
    apagados["alert_history"] = db.query(AlertaHistory).delete(synchronize_session=False)
    apagados["idempotency_keys"] = db.query(IdempotencyKey).delete(synchronize_session=False)
    apagados["preventiva_gerada"] = db.query(PreventivaGerada).delete(synchronize_session=False)
    apagados["troca_oleo_cache"] = db.query(TrocaOleoCache).delete(synchronize_session=False)
    apagados["os_manutencao"] = db.query(OrdemServico).delete(synchronize_session=False)

    db.commit()

    return {
        "ok": True,
        "operacao": "reset-operacional",
        "apagados": apagados,
        "mantidos": [
            "users (autenticação)",
            "veiculo_snapshot (cache Patrimonial)",
            "oficina_padronizada (catálogo)",
            "plano_preventiva (configuração)",
        ],
        "executado_por": user.email,
    }


@router.get("/contagens")
def contagens(user: User = Depends(require_role(["admin"])), db: Session = Depends(get_db)):
    """Snapshot de quantos registros existem em cada tabela."""
    return {
        "users":              db.query(User).count(),
        "veiculo_snapshot":   db.query(text("count(*) FROM veiculo_snapshot")).scalar() or 0,
        "oficina_padronizada": db.query(text("count(*) FROM oficina_padronizada")).scalar() or 0,
        "plano_preventiva":   db.query(text("count(*) FROM plano_preventiva")).scalar() or 0,
        "os_manutencao":      db.query(OrdemServico).count(),
        "os_item_linha":      db.query(OsItemLinha).count(),
        "anexos_os":          db.query(AnexosOs).count(),
        "alert_history":      db.query(AlertaHistory).count(),
        "troca_oleo_cache":   db.query(TrocaOleoCache).count(),
        "auditoria_os":       db.query(AuditoriaOs).count(),
        "preventiva_gerada":  db.query(PreventivaGerada).count(),
        "idempotency_keys":   db.query(IdempotencyKey).count(),
    }
