"""Cliente HTTP async do Cadastro Veicular (frota.demos.napel.com.br).

Sincroniza VeiculoSnapshot com a fonte de verdade externa.
Cache in-memory 5min pra reduzir latência e sobreviver a queda momentânea.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Any, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import VeiculoSnapshot

log = logging.getLogger("manutencao.frota")

_VEIC_CACHE: dict[str, Any] = {"data": None, "ts": 0.0}
_DOCS_CACHE: dict[str, tuple[float, list[dict]]] = {}
_TTL_VEIC = 300  # 5 min
_TTL_DOCS = 300


def _hash_to_int(hex_id: str) -> int:
    """UUID hex (32 chars) → Integer 32-bit pra veiculo_patrimonial_id.

    Usa 7 chars hex (max 16^7 = 268M) pra caber em INT4 do Postgres (max 2.1B).
    Colisão em 20 veículos: praticamente zero (probabilidade ~1 em 18M).
    """
    return int(hex_id[:7], 16)


def _detecta_tipo(modelo: str) -> str:
    m = (modelo or "").upper()
    if any(k in m for k in ["CG ", "CG-", "MOTO", "BIZ", "FAN", "BROS"]):
        return "moto"
    if any(k in m for k in ["EMPILHADEIRA", "HYSTER", "CLARK", "YALE"]):
        return "empilhadeira"
    return "carro"


def _map_filial(filial_remota: int | None) -> int:
    """Filiais Napel → IDs internos do módulo.

    Mapa unidireccional. Se a Frota trouxer outra filial, cai default 1.
    """
    m = {100: 1, 200: 2, 300: 3, 700: 4, 800: 5, 900: 6}
    return m.get(filial_remota or 0, 1)


async def _get_frota(path: str, params: Optional[dict] = None) -> Optional[dict]:
    """Baixo nível: GET async na Frota com Bearer + degradação graciosa."""
    if not settings.FROTA_BASE_URL or not settings.FROTA_TOKEN:
        log.warning("FROTA_BASE_URL/TOKEN não configurados")
        return None
    url = f"{settings.FROTA_BASE_URL.rstrip('/')}{path}"
    headers = {
        "Authorization": f"Bearer {settings.FROTA_TOKEN}",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.get(url, params=params, headers=headers)
        if r.status_code != 200:
            log.warning("Frota HTTP %s em %s", r.status_code, path)
            return None
        return r.json()
    except Exception as exc:
        log.warning("Frota falhou em %s: %s", path, exc)
        return None


async def fetch_veiculos_da_frota(filial_id: Optional[int] = None) -> List[dict]:
    """GET /api/v1/fleet/vehicles com cache 5 min.

    Payload: {vehicles: [{id, placa, modelo, marca, ano, filial_id,
                          km_atual, ativo, vencimento_crlv, ...}]}
    """
    now = time.time()
    # cache só p/ a chamada sem filial (lista completa)
    if (filial_id is None and _VEIC_CACHE["data"] is not None
            and (now - _VEIC_CACHE["ts"]) < _TTL_VEIC):
        return _VEIC_CACHE["data"]

    params: dict[str, Any] = {"ativo": "true"}
    if filial_id is not None:
        params["filial_id"] = filial_id

    data = await _get_frota("/api/v1/fleet/vehicles", params=params)
    veiculos = (data or {}).get("vehicles", []) if data else []

    if filial_id is None:
        _VEIC_CACHE["data"] = veiculos
        _VEIC_CACHE["ts"] = now
    log.info("Frota: %d veículos retornados", len(veiculos))
    return veiculos or (_VEIC_CACHE["data"] or [])


async def fetch_veiculo(vehicle_id: str) -> Optional[dict]:
    """GET /api/v1/fleet/vehicles/{id} — detalhe."""
    return await _get_frota(f"/api/v1/fleet/vehicles/{vehicle_id}")


async def fetch_documentos(vehicle_id: str) -> List[dict]:
    """GET /api/v1/fleet/vehicles/{id}/documents — CRLV, IPVA, DPVAT, Seguro.

    Cache 5 min por veículo.
    """
    now = time.time()
    key = str(vehicle_id)
    if key in _DOCS_CACHE:
        ts, cached = _DOCS_CACHE[key]
        if now - ts < _TTL_DOCS:
            return cached

    data = await _get_frota(f"/api/v1/fleet/vehicles/{vehicle_id}/documents")
    docs = data if isinstance(data, list) else ((data or {}).get("documents", []))
    _DOCS_CACHE[key] = (now, docs)
    return docs


async def sync_veiculos(db: AsyncSession) -> dict:
    """Upsert de veículos da Frota → VeiculoSnapshot por frota_external_id."""
    remotos = await fetch_veiculos_da_frota()
    criados = atualizados = 0

    for v in remotos:
        ext_id = v.get("id")
        placa = (v.get("placa") or "").upper()
        if not ext_id or not placa:
            continue

        stmt = select(VeiculoSnapshot).where(
            VeiculoSnapshot.frota_external_id == str(ext_id)
        )
        existente = (await db.execute(stmt)).scalar_one_or_none()

        crlv = None
        if v.get("vencimento_crlv"):
            try:
                crlv = date.fromisoformat(v["vencimento_crlv"])
            except Exception:
                pass

        campos = {
            "frota_external_id": str(ext_id),
            "veiculo_patrimonial_id": _hash_to_int(str(ext_id)),
            "placa": placa,
            "modelo": v.get("modelo") or "?",
            "marca": v.get("marca"),
            "tipo": _detecta_tipo(v.get("modelo") or ""),
            "ano": v.get("ano"),
            "km_atual": v.get("km_atual") or 0,
            "filial_id": _map_filial(v.get("filial_id")),
            "vencimento_crlv": crlv,
            "ativo": bool(v.get("ativo", True)),
            "data_sincronismo": datetime.utcnow(),
        }

        if existente:
            for k, val in campos.items():
                setattr(existente, k, val)
            atualizados += 1
        else:
            db.add(VeiculoSnapshot(**campos))
            criados += 1

    await db.commit()
    log.info("Sync Frota: %d criados, %d atualizados de %d remotos",
             criados, atualizados, len(remotos))
    return {"criados": criados, "atualizados": atualizados, "total_remoto": len(remotos)}


async def fetch_veiculo_by_placa(placa: str) -> Optional[dict]:
    for v in await fetch_veiculos_da_frota():
        if (v.get("placa") or "").upper() == placa.upper():
            return v
    return None
