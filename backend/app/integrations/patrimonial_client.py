"""Cliente HTTP real do Cadastro Veicular (frota.demos.napel.com.br).

Sincroniza VeiculoSnapshot com a fonte de verdade externa.
Antes era mock — agora é HTTP real conforme ADR-contratos-APIs-externas.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import List

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import VeiculoSnapshot

log = logging.getLogger("manutencao.frota")


def _hash_to_int(hex_id: str) -> int:
    """UUID hex (32 chars) → Integer 32-bit pra veiculo_patrimonial_id.

    Usa 7 chars hex (max 16^7 = 268M) pra caber em INT4 do Postgres (max 2.1B).
    Colisão em 15 veículos: praticamente zero (probabilidade ~1 em 18M).
    """
    return int(hex_id[:7], 16)


def _detecta_tipo(modelo: str) -> str:
    m = (modelo or "").upper()
    if any(k in m for k in ["CG ", "CG-", "MOTO", "BIZ", "FAN", "BROS"]):
        return "moto"
    if any(k in m for k in ["EMPILHADEIRA", "HYSTER", "CLARK"]):
        return "empilhadeira"
    return "carro"


def _map_filial(filial_remota: int | None) -> int:
    if filial_remota == 100:
        return 1
    if filial_remota == 700:
        return 2
    if filial_remota == 900:
        return 3
    return 1


def fetch_veiculos_da_frota() -> List[dict]:
    """GET https://frota.demos.napel.com.br/api/v1/fleet/vehicles"""
    url = f"{settings.FROTA_BASE_URL.rstrip('/')}/api/v1/fleet/vehicles"
    headers = {"Authorization": f"Bearer {settings.FROTA_TOKEN}"}
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url, headers=headers)
            r.raise_for_status()
            data = r.json()
        veiculos = data.get("vehicles", []) if isinstance(data, dict) else data
        log.info("Frota: %d veículos retornados", len(veiculos))
        return veiculos
    except httpx.HTTPError as e:
        log.exception("Falha buscar Frota: %s", e)
        return []


def sync_veiculos(db: Session) -> dict:
    """Upsert de veículos da Frota → VeiculoSnapshot por frota_external_id."""
    remotos = fetch_veiculos_da_frota()
    criados = atualizados = 0

    for v in remotos:
        ext_id = v.get("id")
        placa = (v.get("placa") or "").upper()
        if not ext_id or not placa:
            continue

        existente = db.query(VeiculoSnapshot).filter(
            VeiculoSnapshot.frota_external_id == ext_id
        ).first()

        crlv = None
        if v.get("vencimento_crlv"):
            try:
                crlv = date.fromisoformat(v["vencimento_crlv"])
            except Exception:
                pass

        campos = {
            "frota_external_id": ext_id,
            "veiculo_patrimonial_id": _hash_to_int(ext_id),
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

    db.commit()
    log.info("Sync Frota: %d criados, %d atualizados de %d remotos", criados, atualizados, len(remotos))
    return {"criados": criados, "atualizados": atualizados, "total_remoto": len(remotos)}


# Compat
def fetch_veiculos_patrimonial(filial_id: int) -> List[dict]:
    return fetch_veiculos_da_frota()


def fetch_veiculo_by_placa(placa: str) -> dict | None:
    for v in fetch_veiculos_da_frota():
        if (v.get("placa") or "").upper() == placa.upper():
            return v
    return None
