"""Cliente HTTP real do app Troca de Óleo (troca-oleo.demos.napel.com.br).

Sincroniza TrocaOleoCache + atualiza km_atual dos veículos (porque o motorista
registra KM no app Troca de Óleo, é a fonte de verdade do hodômetro).
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import List, Optional

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import TrocaOleoCache, VeiculoSnapshot

log = logging.getLogger("manutencao.oleo")


def _login_oleo() -> Optional[httpx.Client]:
    """Loga via PIN admin e retorna client com cookie de sessão."""
    try:
        client = httpx.Client(timeout=10.0, follow_redirects=False)
        r = client.post(
            f"{settings.OLEO_BASE_URL.rstrip('/')}/api/v1/auth/login",
            json={"identifier": "hudson@napel.com.br", "pin": settings.OLEO_PIN},
        )
        r.raise_for_status()
        return client
    except httpx.HTTPError as e:
        log.exception("Falha login Troca de Óleo: %s", e)
        return None


def fetch_oil_changes() -> List[dict]:
    """GET /api/v1/admin/oil-changes (lista global de trocas)."""
    client = _login_oleo()
    if not client:
        return []
    try:
        r = client.get(f"{settings.OLEO_BASE_URL.rstrip('/')}/api/v1/admin/oil-changes")
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        log.warning("Falha fetch oil-changes: %s", e)
        return []
    finally:
        client.close()


def fetch_odometer_logs() -> List[dict]:
    """GET /api/v1/admin/odometer-logs (km registrados pelo motorista)."""
    client = _login_oleo()
    if not client:
        return []
    try:
        r = client.get(f"{settings.OLEO_BASE_URL.rstrip('/')}/api/v1/admin/odometer-logs")
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        log.warning("Falha fetch odometer-logs: %s", e)
        return []
    finally:
        client.close()


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def sync_trocas_oleo(db: Session) -> dict:
    """Sincroniza trocas de óleo + atualiza km_atual via odometer-logs."""
    trocas_remotas = fetch_oil_changes()
    logs_remotos = fetch_odometer_logs()
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
        if db.query(TrocaOleoCache).filter(TrocaOleoCache.dedup_hash == dedup).first():
            continue
        veic = db.query(VeiculoSnapshot).filter(
            VeiculoSnapshot.frota_external_id == vehicle_id
        ).first()
        if not veic:
            continue  # veículo desconhecido pelo Manutenção — pula
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
        veic = db.query(VeiculoSnapshot).filter(
            VeiculoSnapshot.frota_external_id == vid
        ).first()
        if veic and km > (veic.km_atual or 0):
            veic.km_atual = km
            veic.data_sincronismo = datetime.utcnow()
            km_atualizado += 1

    db.commit()
    log.info("Sync Óleo: %d trocas, %d km atualizados", trocas_criadas, km_atualizado)
    return {
        "trocas_criadas": trocas_criadas,
        "km_atualizado": km_atualizado,
        "total_remoto_trocas": len(trocas_remotas),
        "total_remoto_logs": len(logs_remotos),
    }


# Compat
def fetch_trocas_oleo_veiculo(veiculo_id: int) -> List[dict]:
    return []
