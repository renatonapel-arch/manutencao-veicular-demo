"""Checklist mensal (V2) do veículo.

Substitui o pipe "Custos - Checklist Veiculos" do Pipefy.

Fluxo:
1. Motorista/mecânico abre `/checklist/novo` no celular, escolhe veículo,
   preenche cada item (OK / PROBLEMA), anexa fotos obrigatórias de pneu,
   submete.
2. POST /checklist cria registro + gera 1 OS `corretiva_checklist` para
   cada item marcado como PROBLEMA (uma OS por item, herda filial/veículo).
3. WhatsApp automático dispara notif "Nova OS aberta" para o responsável
   da filial de cada OS gerada.
4. Cron mensal (fase B) alerta veículos há > 30 dias sem checklist.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..dependencies import check_filial_access, get_current_user
from ..integrations.evolution_whatsapp import notify_os_transition
from ..models import (
    AnexosChecklist, ChecklistVeiculo, OrdemServico, User, VeiculoSnapshot,
)

log = logging.getLogger("manutencao.checklist")
router = APIRouter(prefix="/checklist", tags=["checklist"])


# ---------- Itens padrão (bate 1:1 com o pipe do Pipefy) ----------

ITENS_MOTO = [
    "Nenhum vazamento aparente",
    "Nenhum fio desencapado",
    "Nenhuma luz de alerta acesa no painel",
    "Nenhuma lâmpada queimada",
    "Calibragem pneus OK",
    "Relação lubrificada",
    "Regulagem relação OK",
    "Nível fluido freio OK",
    "Regulagem freio dianteiro OK",
    "Regulagem freio traseiro OK",
]

ITENS_CARRO = [
    "Nenhum vazamento aparente",
    "Nenhum fio desencapado",
    "Nenhuma luz de alerta acesa no painel",
    "Nenhuma lâmpada queimada",
    "Calibragem pneus OK",
    "Nível óleo motor OK",
    "Nível água radiador OK",
    "Nível fluido freio OK",
    "Nível limpador para-brisa OK",
]

STATUS_ITEM = ("OK", "PROBLEMA", "NA")


# ---------- Schemas ----------

class ChecklistCreate(BaseModel):
    request_id: UUID
    veiculo_id: int
    km_veiculo: int = Field(ge=0, le=10_000_000)
    itens_status: dict  # {"Nenhum vazamento aparente": "OK", ...}
    observacao: Optional[str] = None
    funcionario_relator_id: Optional[int] = None


class ChecklistOut(BaseModel):
    id: int
    veiculo_id: int
    filial_id: int
    tipo_veiculo: str
    km_veiculo: int
    data_checklist: datetime
    itens_status: dict
    observacao: Optional[str] = None
    os_geradas: list = []
    veiculo_placa: Optional[str] = None
    veiculo_modelo: Optional[str] = None
    total_problemas: int = 0
    total_ok: int = 0
    model_config = ConfigDict(from_attributes=True)


class ItensRefResponse(BaseModel):
    moto: list[str]
    carro: list[str]


# ---------- Endpoints ----------

@router.get("/itens-referencia", response_model=ItensRefResponse)
async def itens_referencia():
    """Lista de itens padrão pro frontend renderizar o formulário."""
    return {"moto": ITENS_MOTO, "carro": ITENS_CARRO}


@router.post("", response_model=ChecklistOut, status_code=201)
async def criar_checklist(
    payload: ChecklistCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Idempotência — carrega com veiculo eager pra _to_out não fazer lazy-load
    existente = (await db.execute(
        select(ChecklistVeiculo)
        .options(selectinload(ChecklistVeiculo.veiculo))
        .where(ChecklistVeiculo.request_id == payload.request_id)
    )).scalar_one_or_none()
    if existente:
        return await _to_out(db, existente)

    veic = await db.get(VeiculoSnapshot, payload.veiculo_id)
    if not veic:
        raise HTTPException(404, "Veículo não encontrado")
    if not check_filial_access(user, veic.filial_id):
        raise HTTPException(403, "Cross-filial denied")

    tipo_veic = "moto" if (veic.tipo or "carro").lower().startswith("mot") else "carro"
    itens_ref = ITENS_MOTO if tipo_veic == "moto" else ITENS_CARRO

    # Normaliza: qualquer item não enviado vira "NA"; qualquer status inválido vira "NA"
    itens_norm = {}
    for item in itens_ref:
        val = str(payload.itens_status.get(item, "NA")).upper()
        if val not in STATUS_ITEM:
            val = "NA"
        itens_norm[item] = val

    ck = ChecklistVeiculo(
        request_id=payload.request_id,
        veiculo_id=veic.id,
        aberto_por_user_id=user.id,
        funcionario_relator_id=payload.funcionario_relator_id,
        filial_id=veic.filial_id,
        tipo_veiculo=tipo_veic,
        km_veiculo=payload.km_veiculo,
        itens_status=itens_norm,
        observacao=payload.observacao,
        os_geradas=[],
    )
    db.add(ck)
    await db.flush()

    # Gera 1 OS corretiva_checklist para cada item PROBLEMA
    ids_geradas = []
    for item, st in itens_norm.items():
        if st != "PROBLEMA":
            continue
        os_ = OrdemServico(
            request_id=uuid.uuid4(),
            veiculo_id=veic.id,
            filial_id=veic.filial_id,
            aberto_por_user_id=user.id,
            funcionario_relator_id=payload.funcionario_relator_id,
            tipo_os="corretiva_checklist",
            tipo_destino="oficina_terceirizada",
            km_veiculo=payload.km_veiculo,
            descricao_problema=f"[Checklist mensal] {item}",
            categoria=_categorizar(item),
            status="aberta",
            data_abertura=datetime.utcnow(),
            valor_total=Decimal("0"),
            desconto_ajuste=Decimal("0"),
            economia_napel_total=Decimal("0"),
        )
        db.add(os_)
        await db.flush()
        ids_geradas.append(os_.id)

        try:
            await notify_os_transition(db, os_, "aberta")
        except Exception as exc:
            log.warning("Notify checklist->OS falhou (item %s): %s", item, exc)

    ck.os_geradas = ids_geradas
    await db.commit()
    # Refresh eager pra evitar lazy load no _to_out
    await db.refresh(ck, ["veiculo"])
    return await _to_out(db, ck)


@router.get("", response_model=dict)
async def listar_checklists(
    veiculo_id: Optional[int] = Query(default=None),
    filial_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ChecklistVeiculo).where(ChecklistVeiculo.deleted_at.is_(None))
    if user.role not in ("admin", "aprovador"):
        stmt = stmt.where(ChecklistVeiculo.filial_id == user.filial_id)
    elif filial_id:
        stmt = stmt.where(ChecklistVeiculo.filial_id == filial_id)
    if veiculo_id:
        stmt = stmt.where(ChecklistVeiculo.veiculo_id == veiculo_id)

    total = (await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )).scalar_one()

    rows = list((await db.execute(
        stmt.options(selectinload(ChecklistVeiculo.veiculo))
        .order_by(ChecklistVeiculo.data_checklist.desc())
        .offset(offset).limit(limit)
    )).scalars().all())

    data = [await _to_out(db, c) for c in rows]
    return {"data": data, "total": int(total), "limit": limit, "offset": offset}


@router.get("/{checklist_id}", response_model=ChecklistOut)
async def detalhe(
    checklist_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ck = (await db.execute(
        select(ChecklistVeiculo)
        .options(selectinload(ChecklistVeiculo.veiculo))
        .where(ChecklistVeiculo.id == checklist_id, ChecklistVeiculo.deleted_at.is_(None))
    )).scalar_one_or_none()
    if not ck:
        raise HTTPException(404, "Checklist não encontrado")
    if not check_filial_access(user, ck.filial_id):
        raise HTTPException(403, "Cross-filial denied")
    return await _to_out(db, ck)


# ---------- Helpers ----------

def _categorizar(item: str) -> str:
    """Mapa simples item -> categoria de OS."""
    it = item.lower()
    if "freio" in it or "fluido freio" in it: return "Pastilha / Lona"
    if "pneu" in it or "calibragem" in it: return "Pneu"
    if "luz" in it or "lâmpada" in it or "lampada" in it: return "Lâmpadas"
    if "fio" in it or "elétr" in it or "elet" in it: return "Elétrica"
    if "óleo" in it or "oleo" in it or "vazamento" in it: return "Motor"
    if "radiador" in it: return "Motor"
    if "relação" in it or "relacao" in it: return "Relação"
    return "Outros"


async def _to_out(db: AsyncSession, ck: ChecklistVeiculo) -> dict:
    veic = ck.veiculo if getattr(ck, "veiculo", None) else await db.get(VeiculoSnapshot, ck.veiculo_id)
    itens = ck.itens_status or {}
    return {
        "id": ck.id,
        "veiculo_id": ck.veiculo_id,
        "filial_id": ck.filial_id,
        "tipo_veiculo": ck.tipo_veiculo,
        "km_veiculo": ck.km_veiculo,
        "data_checklist": ck.data_checklist,
        "itens_status": itens,
        "observacao": ck.observacao,
        "os_geradas": ck.os_geradas or [],
        "veiculo_placa": veic.placa if veic else None,
        "veiculo_modelo": veic.modelo if veic else None,
        "total_problemas": sum(1 for v in itens.values() if v == "PROBLEMA"),
        "total_ok": sum(1 for v in itens.values() if v == "OK"),
    }
