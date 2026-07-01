"""Dispatch + histórico de alertas WhatsApp (async)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..dependencies import get_current_user
from ..integrations.evolution_whatsapp import dispatch_alerta, render_template
from ..models import AlertaHistory, OrdemServico, User, VeiculoSnapshot
from ..schemas import AlertaDispatch, AlertaOut, AlertaPreview

router = APIRouter(prefix="/alertas", tags=["alertas"])


@router.get("", response_model=List[AlertaOut])
async def list_alertas(
    status: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    filial_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AlertaHistory)
    if status:
        stmt = stmt.where(AlertaHistory.status == status)
    if tipo:
        stmt = stmt.where(AlertaHistory.tipo_alerta == tipo)
    if filial_id:
        stmt = stmt.where(AlertaHistory.filial_id == filial_id)
    if user.role != "admin" and user.filial_id:
        stmt = stmt.where(AlertaHistory.filial_id == user.filial_id)
    stmt = stmt.order_by(AlertaHistory.created_at.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


async def _count(db: AsyncSession, base_filter, status: str) -> int:
    stmt = select(func.count()).select_from(AlertaHistory).where(AlertaHistory.status == status)
    for cond in base_filter:
        stmt = stmt.where(cond)
    return int((await db.execute(stmt)).scalar_one())


@router.get("/stats")
async def alertas_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base_filter = []
    if user.role != "admin" and user.filial_id:
        base_filter.append(AlertaHistory.filial_id == user.filial_id)
    enviados = await _count(db, base_filter, "sent")
    pendentes = await _count(db, base_filter, "pending")
    falhas = await _count(db, base_filter, "failed")
    dlq = await _count(db, base_filter, "dlq")
    return {
        "enviados_hoje": enviados, "pendentes": pendentes,
        "falhas_24h": falhas, "dlq": dlq,
    }


@router.post("/dispatch", response_model=AlertaPreview)
async def dispatch(
    payload: AlertaDispatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    os = await db.get(OrdemServico, payload.os_id) if payload.os_id else None
    veic = (
        await db.get(VeiculoSnapshot, payload.veiculo_id)
        if payload.veiculo_id
        else (os.veiculo if os else None)
    )
    telefone = payload.telefone
    if not telefone and payload.destinatario_user_id:
        u = await db.get(User, payload.destinatario_user_id)
        telefone = u.telefone if u else None
    if not telefone:
        raise HTTPException(
            status_code=400,
            detail="Telefone obrigatório (ou destinatario_user_id)",
        )

    mensagem = render_template(payload.tipo_alerta, payload.template, os=os, veiculo=veic)
    alerta = AlertaHistory(
        os_id=payload.os_id, veiculo_id=payload.veiculo_id,
        filial_id=(veic.filial_id if veic else None),
        tipo_alerta=payload.tipo_alerta,
        telefone=telefone,
        template_name=payload.template or payload.tipo_alerta,
        mensagem=mensagem,
        status="pending" if settings.EVOLUTION_ENABLED else "sent",
        enviado_por=user.id,
    )
    db.add(alerta)
    await db.commit()
    await db.refresh(alerta)
    result = dispatch_alerta(alerta)
    await db.commit()
    return AlertaPreview(
        mensagem=mensagem, telefone=telefone,
        enviado=result.get("sent", False), alerta_id=alerta.id,
    )
