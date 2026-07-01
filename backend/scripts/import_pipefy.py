#!/usr/bin/env python3
"""Import histórico do pipe Custos - Manutenção Veiculos (Pipefy → OrdemServico).

Uso:
    python import_pipefy.py --dry-run       # gera CSV pra revisão, não grava
    python import_pipefy.py                 # grava no banco (idempotente via pipefy_card_id)

Requer env vars:
    PIPEFY_TOKEN      (token da API do Pipefy)
    DATABASE_URL      (Postgres do módulo Manutenção)

Regras (v3, ver plano v4-opção-b):
- 257 cards do pipe 304827831 (Custos - Manutenção Veiculos)
- Idempotência: UNIQUE(pipefy_card_id) + ON CONFLICT DO NOTHING
- Encoding: NFC normalization em todos os campos (evita bug "Manutenção")
- ACOMPANHANDO → status="encerrada" (regra do Renato)
- Solicitada/Checklist → status="aberta"
- Finalizada → status="encerrada"
- Categoria: valor do campo Tipo (Motor/Pneu/... 10 valores)
- Descrição livre do Pipefy: OrdemServico.descricao_itens_original (texto original preservado)
                             + OsItemLinha único "Peças/serviços conforme descrição" (valor=total)

Log estruturado em stdout + resumo final. Se falhar, WhatsApp pro Renato.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
import sys
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

# Adiciona backend/ ao PYTHONPATH pra importar app
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    OrdemServico, OsItemLinha, VeiculoSnapshot,
)

log = logging.getLogger("import_pipefy")

PIPE_ID = 304827831  # Custos - Manutenção Veiculos
CATEGORIAS_VALIDAS = {
    "Motor", "Pneu", "Pastilha / Lona", "Relação", "Lâmpadas",
    "Elétrica", "Bateria", "Empilhadeira", "Embreagem", "Outros",
}


def _nfc(s: str | None) -> str | None:
    """Normaliza para NFC (evita bug 'Manutenção' com caracteres decompostos)."""
    if not s:
        return None
    return unicodedata.normalize("NFC", str(s)).strip() or None


def _fld_value(card: dict, prefix: str) -> str | None:
    """Extrai valor do campo cujo nome COMEÇA com prefix (tolera variações)."""
    p = prefix.lower()
    for f in card.get("fields", []):
        if f.get("name", "").lower().startswith(p):
            v = f.get("value")
            if v and isinstance(v, str) and v.startswith("[") and v.endswith("]"):
                try:
                    arr = json.loads(v)
                    return _nfc(arr[0]) if arr else None
                except json.JSONDecodeError:
                    return _nfc(v)
            return _nfc(v)
    return None


def _parse_brl(s: str | None) -> Decimal:
    if not s:
        return Decimal("0")
    txt = str(s).replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".").strip()
    try:
        return Decimal(txt)
    except InvalidOperation:
        return Decimal("0")


def _parse_date(s: str | None) -> Optional[datetime]:
    if not s:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(s).split("T")[0], fmt)
        except ValueError:
            continue
    return None


def _parse_km(s: str | None) -> int:
    if not s:
        return 0
    txt = str(s).replace(".", "").replace(",", ".").strip()
    try:
        return int(float(txt))
    except (ValueError, TypeError):
        return 0


def _map_status(fase: str) -> str:
    m = {
        "Finalizada": "encerrada",
        "ACOMPANHANDO": "encerrada",  # regra do Renato
        "Solicitada/Checklist": "aberta",
    }
    return m.get(fase, "encerrada")


def _map_categoria(tipo_pipefy: str | None) -> str | None:
    if not tipo_pipefy:
        return "Outros"
    tipo_norm = _nfc(tipo_pipefy).strip()
    if tipo_norm in CATEGORIAS_VALIDAS:
        return tipo_norm
    # Correções de encoding (pipefy às vezes traz Ã em vez de ç)
    for cat in CATEGORIAS_VALIDAS:
        if cat.lower() == tipo_norm.lower():
            return cat
    return "Outros"


async def fetch_pipefy_cards(token: str) -> list[dict]:
    """GraphQL paginado — busca todas as 257 cards."""
    query_template = """
    query($cursor: String) {
      cards(pipe_id: %d, first: 50, after: $cursor) {
        edges { node {
          id title current_phase { name } createdAt updated_at
          fields { name value }
        } }
        pageInfo { hasNextPage endCursor }
      }
    }
    """ % PIPE_ID

    all_cards = []
    cursor = None
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            payload = {"query": query_template.replace("$cursor", "$cursor")}
            variables = {"cursor": cursor} if cursor else {}
            r = await client.post(
                "https://api.pipefy.com/graphql",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"query": query_template, "variables": variables},
            )
            r.raise_for_status()
            data = r.json().get("data", {}).get("cards", {})
            edges = data.get("edges", [])
            all_cards.extend(e["node"] for e in edges)
            log.info("Pipefy: %d cards carregados", len(all_cards))
            info = data.get("pageInfo", {})
            if not info.get("hasNextPage"):
                break
            cursor = info.get("endCursor")
    return all_cards


def transform_card(card: dict, veiculo_map: dict[str, int]) -> dict | None:
    """Mapeia card Pipefy → dict pronto pra virar OrdemServico.

    Retorna None se campos essenciais faltarem (placa desconhecida etc.).
    """
    placa = _fld_value(card, "Veiculo")
    if not placa:
        return None
    placa = placa.upper().strip()

    veiculo_id = veiculo_map.get(placa)
    if not veiculo_id:
        log.warning("Card %s: placa %s não encontrada no VeiculoSnapshot", card["id"], placa)
        return None

    fase = card.get("current_phase", {}).get("name", "Finalizada")
    status = _map_status(fase)
    data = _parse_date(_fld_value(card, "Data Manuten"))
    if not data:
        # Sem data → usa createdAt do card
        try:
            data = datetime.fromisoformat(card["createdAt"].replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, KeyError):
            data = datetime.utcnow()

    valor_total = _parse_brl(_fld_value(card, "Total Manuten"))
    km = _parse_km(_fld_value(card, "Km Manuten"))
    oficina_livre = _fld_value(card, "Oficina") or "—"
    funcionario = _fld_value(card, "Funcionario")
    modelo = _fld_value(card, "Modelo")
    categoria = _map_categoria(_fld_value(card, "Tipo"))
    desc_original = _fld_value(card, "Qtdes") or ""

    return {
        "pipefy_card_id": str(card["id"]),
        "veiculo_id": veiculo_id,
        "veiculo_modelo_snapshot": modelo,
        "placa": placa,
        "status": status,
        "categoria": categoria,
        "tipo_os": "corretiva_manual",
        "tipo_destino": "oficina_terceirizada",
        "data_abertura": data,
        "data_encerramento": data if status == "encerrada" else None,
        "km_veiculo": km,
        "oficina_nome_livre": oficina_livre,
        "valor_total": valor_total,
        "descricao_problema": f"Importado do Pipefy · {categoria or 'Manutenção'}",
        "descricao_itens_original": desc_original,
        "funcionario_relator_txt": funcionario,
    }


async def build_veiculo_map(db: AsyncSession) -> dict[str, int]:
    """Mapa placa → veiculo_snapshot.id."""
    stmt = select(VeiculoSnapshot.placa, VeiculoSnapshot.id)
    rows = (await db.execute(stmt)).all()
    return {(p or "").upper().strip(): vid for p, vid in rows}


async def import_cards(cards: list[dict], dry_run: bool) -> dict:
    async with SessionLocal() as db:
        veiculo_map = await build_veiculo_map(db)
        if not veiculo_map:
            log.error("VeiculoSnapshot vazio. Rode /admin/sync-frota antes do import.")
            return {"ok": False, "erro": "sem veículos"}

        transformados = []
        pulados_placa = 0
        for card in cards:
            t = transform_card(card, veiculo_map)
            if t is None:
                pulados_placa += 1
                continue
            transformados.append(t)

        log.info("Transformação: %d OK, %d puladas (placa desconhecida)",
                 len(transformados), pulados_placa)

        # Admin user genérico p/ aberto_por_user_id (Hudson id=1 do seed mínimo)
        aberto_por = 1

        if dry_run:
            out_path = Path(__file__).parent / f"import_pipefy_preview_{datetime.now():%Y%m%d_%H%M%S}.csv"
            with out_path.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "pipefy_card_id", "placa", "categoria", "status",
                    "data_abertura", "km_veiculo", "valor_total",
                    "oficina_nome_livre", "descricao_itens_original",
                ])
                w.writeheader()
                for t in transformados:
                    w.writerow({
                        "pipefy_card_id": t["pipefy_card_id"],
                        "placa": t["placa"], "categoria": t["categoria"],
                        "status": t["status"],
                        "data_abertura": t["data_abertura"].isoformat(),
                        "km_veiculo": t["km_veiculo"],
                        "valor_total": t["valor_total"],
                        "oficina_nome_livre": t["oficina_nome_livre"],
                        "descricao_itens_original": (t["descricao_itens_original"] or "")[:200],
                    })
            log.info("Dry-run: CSV salvo em %s", out_path)
            return {
                "ok": True, "dry_run": True,
                "total_cards": len(cards),
                "transformados": len(transformados),
                "pulados_placa": pulados_placa,
                "csv": str(out_path),
            }

        # ---- INSERT com ON CONFLICT DO NOTHING (idempotência) ----
        inseridos = 0
        pulados_dedup = 0
        for t in transformados:
            # Verifica se já existe (dedup por pipefy_card_id)
            stmt_check = select(OrdemServico.id).where(
                OrdemServico.pipefy_card_id == t["pipefy_card_id"]
            )
            existente = (await db.execute(stmt_check)).scalar_one_or_none()
            if existente:
                pulados_dedup += 1
                continue

            os = OrdemServico(
                pipefy_card_id=t["pipefy_card_id"],
                veiculo_id=t["veiculo_id"],
                filial_id=1,  # TODO: pegar do veículo
                tipo_os=t["tipo_os"],
                status=t["status"],
                categoria=t["categoria"],
                tipo_destino=t["tipo_destino"],
                data_abertura=t["data_abertura"],
                data_encerramento=t["data_encerramento"],
                km_veiculo=t["km_veiculo"],
                valor_total=t["valor_total"],
                descricao_problema=t["descricao_problema"],
                descricao_itens_original=t["descricao_itens_original"],
                aberto_por_user_id=aberto_por,
                # motivo_aprovacao = None (auto quando encerrada e valor < teto seria aplicado, mas legado importado fica None)
            )
            db.add(os)
            await db.flush()

            # Item único preservando texto original
            if t["valor_total"] > 0:
                db.add(OsItemLinha(
                    os_id=os.id, tipo_item="servico",
                    descricao="Peças/serviços conforme descrição (importado do Pipefy)",
                    quantidade=Decimal("1"),
                    valor_unitario=t["valor_total"], subtotal=t["valor_total"],
                    garantia_dias=0,
                ))
            inseridos += 1

        await db.commit()
        log.info("Import concluído: %d inseridos, %d pulados dedup, %d pulados placa",
                 inseridos, pulados_dedup, pulados_placa)

        return {
            "ok": True, "dry_run": False,
            "total_cards": len(cards),
            "transformados": len(transformados),
            "inseridos": inseridos,
            "pulados_dedup": pulados_dedup,
            "pulados_placa": pulados_placa,
        }


async def main_async(dry_run: bool):
    token = os.getenv("PIPEFY_TOKEN")
    if not token:
        log.error("PIPEFY_TOKEN ausente no env")
        sys.exit(1)

    log.info("Fetching cards do pipe %d…", PIPE_ID)
    cards = await fetch_pipefy_cards(token)
    log.info("Total: %d cards", len(cards))

    result = await import_cards(cards, dry_run=dry_run)
    log.info("Result: %s", json.dumps(result, default=str, indent=2, ensure_ascii=False))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Gera CSV, não grava no banco")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        result = asyncio.run(main_async(dry_run=args.dry_run))
        sys.exit(0 if result.get("ok") else 1)
    except Exception as exc:  # noqa: BLE001
        log.exception("Import falhou: %s", exc)
        # Notifica Renato via WhatsApp (evolution)
        try:
            _notify_failure(str(exc))
        except Exception:
            pass
        sys.exit(2)


def _notify_failure(err: str) -> None:
    """Envia WhatsApp pro Renato em caso de falha crítica."""
    url = os.getenv("EVOLUTION_API_URL")
    tok = os.getenv("EVOLUTION_API_TOKEN")
    inst = os.getenv("EVOLUTION_INSTANCE")
    num = os.getenv("RENATO_WHATSAPP")
    if not all([url, tok, inst, num]):
        return
    import httpx as _h
    _h.post(
        f"{url}/message/sendText/{inst}",
        headers={"apikey": tok, "Content-Type": "application/json"},
        json={"number": num, "text": f"⚠️ import_pipefy.py falhou:\n\n{err[:300]}"},
        timeout=10.0,
    )


if __name__ == "__main__":
    main()
