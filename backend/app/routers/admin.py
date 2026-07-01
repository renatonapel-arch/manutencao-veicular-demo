"""Endpoints admin — reset + sync com apps Frota e Troca de Óleo (async)."""
from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import require_role
from ..integrations.oleo_client import sync_trocas_oleo
from ..integrations.patrimonial_client import sync_veiculos
from ..models import (
    AlertaHistory, AnexosOs, AuditoriaOs, IdempotencyKey, OficinaPadronizada,
    OrdemServico, OsItemLinha, PlanoPreventiva, PreventivaGerada,
    TrocaOleoCache, User, VeiculoSnapshot,
)

router = APIRouter(prefix="/admin", tags=["admin"])


async def _delete_all(db: AsyncSession, model) -> int:
    result = await db.execute(delete(model))
    return int(result.rowcount or 0)


async def _count(db: AsyncSession, model) -> int:
    stmt = select(func.count()).select_from(model)
    return int((await db.execute(stmt)).scalar_one())


@router.post("/reset-operacional")
async def reset_dados_operacionais(
    user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Apaga TODOS os dados operacionais. Mantém users, veículos, oficinas, planos."""
    apagados = {
        "anexos_os":       await _delete_all(db, AnexosOs),
        "os_item_linha":   await _delete_all(db, OsItemLinha),
        "auditoria_os":    await _delete_all(db, AuditoriaOs),
        "alert_history":   await _delete_all(db, AlertaHistory),
        "idempotency_keys":await _delete_all(db, IdempotencyKey),
        "preventiva_gerada":await _delete_all(db, PreventivaGerada),
        "troca_oleo_cache":await _delete_all(db, TrocaOleoCache),
        "os_manutencao":   await _delete_all(db, OrdemServico),
    }
    await db.commit()
    return {
        "ok": True, "operacao": "reset-operacional", "apagados": apagados,
        "mantidos": ["users", "veiculo_snapshot", "oficina_padronizada", "plano_preventiva"],
        "executado_por": user.email,
    }


@router.post("/reset-planos")
async def reset_planos(
    user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    apagados = {
        "preventiva_gerada": await _delete_all(db, PreventivaGerada),
        "plano_preventiva":  await _delete_all(db, PlanoPreventiva),
    }
    await db.commit()
    return {
        "ok": True, "operacao": "reset-planos",
        "apagados": apagados, "executado_por": user.email,
    }


@router.get("/contagens")
async def contagens(
    user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    return {
        "users":               await _count(db, User),
        "veiculo_snapshot":    await _count(db, VeiculoSnapshot),
        "oficina_padronizada": await _count(db, OficinaPadronizada),
        "plano_preventiva":    await _count(db, PlanoPreventiva),
        "os_manutencao":       await _count(db, OrdemServico),
        "os_item_linha":       await _count(db, OsItemLinha),
        "anexos_os":           await _count(db, AnexosOs),
        "alert_history":       await _count(db, AlertaHistory),
        "troca_oleo_cache":    await _count(db, TrocaOleoCache),
        "auditoria_os":        await _count(db, AuditoriaOs),
        "preventiva_gerada":   await _count(db, PreventivaGerada),
        "idempotency_keys":    await _count(db, IdempotencyKey),
    }


# ============================================================
# Integração real
# ============================================================

@router.post("/sync-frota")
async def trigger_sync_frota(
    user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await sync_veiculos(db)
    return {"ok": True, "operacao": "sync-frota", **result}


@router.post("/sync-oleo")
async def trigger_sync_oleo(
    user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    result = await sync_trocas_oleo(db)
    return {"ok": True, "operacao": "sync-oleo", **result}


@router.post("/sync-all")
async def trigger_sync_all(
    user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    frota = await sync_veiculos(db)
    oleo = await sync_trocas_oleo(db)
    return {"ok": True, "operacao": "sync-all", "frota": frota, "oleo": oleo}


@router.post("/import-pipefy")
async def trigger_import_pipefy(
    dry_run: bool = False,
    user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Dispara import histórico do pipe 304827831 (Custos - Manutenção Veiculos).

    Idempotente via UNIQUE(pipefy_card_id). Roda em background — endpoint retorna
    imediatamente com PID. Log completo em stdout do container.
    """
    import asyncio
    import subprocess
    import sys as _sys
    from pathlib import Path

    script = Path(__file__).resolve().parent.parent.parent / "scripts" / "import_pipefy.py"
    if not script.exists():  # fallback layout repo (backend/ como subpasta)
        script = Path(__file__).resolve().parent.parent.parent.parent / "backend" / "scripts" / "import_pipefy.py"
    if not script.exists():
        return {"ok": False, "erro": "script não encontrado"}
    args = [_sys.executable, str(script)]
    if dry_run:
        args.append("--dry-run")
    # Fire-and-forget com log em arquivo (PIPE sem leitor trava/perde output)
    logf = open("/tmp/import_pipefy.log", "ab")
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=logf, stderr=subprocess.STDOUT,
    )
    return {
        "ok": True, "pid": proc.pid, "dry_run": dry_run,
        "script": str(script),
        "detail": "rodando em background; GET /admin/script-log",
    }


@router.post("/seed-membros")
async def trigger_seed_membros(
    dry_run: bool = False,
    user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Popula MembroManutencao a partir dos 37 funcionários do Sólides."""
    import asyncio
    import subprocess
    import sys as _sys
    from pathlib import Path

    script = Path(__file__).resolve().parent.parent.parent / "scripts" / "seed_membros.py"
    if not script.exists():
        script = Path(__file__).resolve().parent.parent.parent.parent / "backend" / "scripts" / "seed_membros.py"
    if not script.exists():
        return {"ok": False, "erro": "script não encontrado"}
    args = [_sys.executable, str(script)]
    if dry_run:
        args.append("--dry-run")
    logf = open("/tmp/seed_membros.log", "ab")
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=logf, stderr=subprocess.STDOUT,
    )
    return {"ok": True, "pid": proc.pid, "dry_run": dry_run}


@router.get("/script-log")
async def script_log(
    qual: str = "import",
    user: User = Depends(require_role(["admin"])),
):
    """Lê os últimos 8KB do log do script (import|seed)."""
    from pathlib import Path as _P
    path = _P("/tmp/import_pipefy.log" if qual == "import" else "/tmp/seed_membros.log")
    if not path.exists():
        return {"ok": False, "erro": "log inexistente"}
    data = path.read_bytes()[-8192:]
    return {"ok": True, "log": data.decode("utf-8", errors="replace")}


@router.post("/reset-tudo-e-sync")
async def reset_e_sync(
    user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    apagados = {
        "anexos_os":         await _delete_all(db, AnexosOs),
        "os_item_linha":     await _delete_all(db, OsItemLinha),
        "auditoria_os":      await _delete_all(db, AuditoriaOs),
        "alert_history":     await _delete_all(db, AlertaHistory),
        "idempotency_keys":  await _delete_all(db, IdempotencyKey),
        "preventiva_gerada": await _delete_all(db, PreventivaGerada),
        "troca_oleo_cache":  await _delete_all(db, TrocaOleoCache),
        "os_manutencao":     await _delete_all(db, OrdemServico),
        "plano_preventiva":  await _delete_all(db, PlanoPreventiva),
        "veiculo_snapshot":  await _delete_all(db, VeiculoSnapshot),
    }
    await db.commit()
    frota = await sync_veiculos(db)
    oleo = await sync_trocas_oleo(db)
    return {
        "ok": True, "operacao": "reset-tudo-e-sync",
        "apagados": apagados, "frota": frota, "oleo": oleo,
    }
