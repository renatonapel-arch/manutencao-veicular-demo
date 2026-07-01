"""Cliente HTTP async do app Troca de Óleo (troca-oleo.napel.com.br).

Padrão de auth: X-Sync-Secret (assim como caixa_interno do Clavis usa).
Cache local com TTL curto (30s por veículo, 5min para oficinas).
"""
from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import TrocaOleoCache, VeiculoSnapshot

log = logging.getLogger("manutencao.oleo")

_OFIC_CACHE: dict[str, Any] = {"data": None, "ts": 0.0}
_OLEO_CACHE: dict[int, tuple[float, list[dict]]] = {}
_TTL_OFIC = 300  # 5 min
_TTL_OLEO = 30   # 30 s


async def _get_oleo(path: str, params: Optional[dict] = None) -> Optional[dict]:
    """Baixo nível: GET async no Troca-Óleo com X-Sync-Secret."""
    url_base = getattr(settings, "TROCA_OLEO_URL", None) or getattr(settings, "OLEO_BASE_URL", None)
    secret = getattr(settings, "TROCA_OLEO_SYNC_SECRET", None)
    if not url_base or not secret:
        log.warning("TROCA_OLEO_URL/SECRET não configurados")
        return None
    url = f"{url_base.rstrip('/')}{path}"
    headers = {"X-Sync-Secret": secret, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.get(url, params=params, headers=headers)
        if r.status_code != 200:
            log.warning("Troca-Óleo HTTP %s em %s", r.status_code, path)
            return None
        return r.json()
    except Exception as exc:
        log.warning("Troca-Óleo falhou em %s: %s", path, exc)
        return None


async def listar_oficinas() -> list[dict]:
    """GET /oficinas/list — catálogo padronizado compartilhado.

    Payload esperado: {oficinas: [{nome, nome_normalizado, cnpj?, cidade?, uf?, ...}]}
    Se troca-óleo ainda não expõe (endpoint em construção), retorna cache antigo.
    """
    now = time.time()
    if _OFIC_CACHE["data"] and (now - _OFIC_CACHE["ts"]) < _TTL_OFIC:
        return _OFIC_CACHE["data"]

    data = await _get_oleo("/oficinas/list")
    oficinas = (data or {}).get("oficinas", [])
    if oficinas:
        _OFIC_CACHE["data"] = oficinas
        _OFIC_CACHE["ts"] = now
    return oficinas or (_OFIC_CACHE["data"] or [])


async def fetch_oil_changes() -> list[dict]:
    """GET /admin/oil-changes — lista global de trocas."""
    data = await _get_oleo("/admin/oil-changes")
    if isinstance(data, list):
        return data
    return (data or {}).get("changes", []) or []


async def fetch_oil_changes_by_vehicle(vehicle_id: int) -> list[dict]:
    """Cache 30s por veículo (v3 fix: era comentado mas não implementado)."""
    now = time.time()
    if vehicle_id in _OLEO_CACHE:
        ts, cached = _OLEO_CACHE[vehicle_id]
        if now - ts < _TTL_OLEO:
            return cached
    data = await _get_oleo(f"/oil-changes/by-vehicle/{vehicle_id}")
    trocas = data if isinstance(data, list) else ((data or {}).get("changes", []))
    _OLEO_CACHE[vehicle_id] = (now, trocas)
    return trocas or []


async def fetch_odometer_logs() -> list[dict]:
    """GET /admin/odometer-logs — km registrado pelo motorista."""
    data = await _get_oleo("/admin/odometer-logs")
    if isinstance(data, list):
        return data
    return (data or {}).get("logs", []) or []


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


async def sync_trocas_oleo(db: AsyncSession) -> dict:
    """Sincroniza trocas + atualiza km_atual via odometer-logs."""
    trocas_remotas = await fetch_oil_changes()
    logs_remotos = await fetch_odometer_logs()
    trocas_criadas = 0
    km_atualizado = 0

    # 1) Insere trocas novas no cache (dedup por hash)
    for t in trocas_remotas:
        vehicle_id = t.get("vehicle_id")
        if not vehicle_id:
            continue
        data_troca = _parse_iso(t.get("data_troca") or t.get("created_at"))
        if not data_troca:
            continue
        dedup = hashlib.sha256(
            f"oleo-{vehicle_id}-{data_troca.isoformat()}-{t.get('km_troca','')}".encode()
        ).hexdigest()[:32]

        stmt = select(TrocaOleoCache).where(TrocaOleoCache.dedup_hash == dedup)
        if (await db.execute(stmt)).scalar_one_or_none():
            continue

        stmt_v = select(VeiculoSnapshot).where(
            VeiculoSnapshot.frota_external_id == str(vehicle_id)
        )
        veic = (await db.execute(stmt_v)).scalar_one_or_none()
        if not veic:
            continue

        db.add(TrocaOleoCache(
            veiculo_id=veic.id, placa=veic.placa,
            data_troca=data_troca, km=t.get("km_troca"),
            oficina_nome=t.get("oficina_nome"),
            produto=t.get("observacao") or "Troca de óleo",
            litros=None, valor=t.get("valor"),
            dedup_hash=dedup,
        ))
        trocas_criadas += 1

    # 2) Atualiza km_atual com a leitura mais recente por veículo
    km_por_veiculo: dict[str, tuple[int, datetime]] = {}
    for log_item in logs_remotos:
        vid = log_item.get("vehicle_id")
        km = log_item.get("km_declarada")
        dt = _parse_iso(log_item.get("created_at"))
        if not (vid and km and dt):
            continue
        cur = km_por_veiculo.get(vid)
        if not cur or dt > cur[1]:
            km_por_veiculo[vid] = (km, dt)

    for vid, (km, dt) in km_por_veiculo.items():
        stmt_v = select(VeiculoSnapshot).where(
            VeiculoSnapshot.frota_external_id == str(vid)
        )
        veic = (await db.execute(stmt_v)).scalar_one_or_none()
        if veic and km > (veic.km_atual or 0):
            veic.km_atual = km
            veic.data_sincronismo = datetime.utcnow()
            km_atualizado += 1

    await db.commit()
    log.info("Sync Óleo: %d trocas, %d km atualizados", trocas_criadas, km_atualizado)
    return {
        "trocas_criadas": trocas_criadas,
        "km_atualizado": km_atualizado,
        "total_remoto_trocas": len(trocas_remotas),
        "total_remoto_logs": len(logs_remotos),
    }
