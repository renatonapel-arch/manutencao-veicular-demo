"""Dispatch + histórico de alertas WhatsApp (mock no MVP)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..dependencies import get_current_user
from ..integrations.evolution_whatsapp import dispatch_alerta, render_template
from ..models import AlertaHistory, OrdemServico, User, VeiculoSnapshot
from ..schemas import AlertaDispatch, AlertaOut, AlertaPreview

router = APIRouter(prefix="/alertas", tags=["alertas"])


@router.get("", response_model=List[AlertaOut])
def list_alertas(
    status: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    filial_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(AlertaHistory)
    if status:
        q = q.filter(AlertaHistory.status == status)
    if tipo:
        q = q.filter(AlertaHistory.tipo_alerta == tipo)
    if filial_id:
        q = q.filter(AlertaHistory.filial_id == filial_id)
    if user.role != "admin" and user.filial_id:
        q = q.filter(AlertaHistory.filial_id == user.filial_id)
    return q.order_by(AlertaHistory.created_at.desc()).limit(limit).all()


@router.get("/stats")
def alertas_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from sqlalchemy import func
    base = db.query(AlertaHistory)
    if user.role != "admin" and user.filial_id:
        base = base.filter(AlertaHistory.filial_id == user.filial_id)
    enviados = base.filter(AlertaHistory.status == "sent").count()
    pendentes = base.filter(AlertaHistory.status == "pending").count()
    falhas = base.filter(AlertaHistory.status == "failed").count()
    dlq = base.filter(AlertaHistory.status == "dlq").count()
    return {"enviados_hoje": enviados, "pendentes": pendentes, "falhas_24h": falhas, "dlq": dlq}


@router.post("/dispatch", response_model=AlertaPreview)
def dispatch(payload: AlertaDispatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    os = db.query(OrdemServico).filter(OrdemServico.id == payload.os_id).first() if payload.os_id else None
    veic = db.query(VeiculoSnapshot).filter(VeiculoSnapshot.id == payload.veiculo_id).first() if payload.veiculo_id else (os.veiculo if os else None)
    telefone = payload.telefone or (
        db.query(User).filter(User.id == payload.destinatario_user_id).first().telefone
        if payload.destinatario_user_id else None
    )
    if not telefone:
        raise HTTPException(status_code=400, detail="Telefone obrigatório (ou destinatario_user_id)")

    mensagem = render_template(payload.tipo_alerta, payload.template, os=os, veiculo=veic)
    alerta = AlertaHistory(
        os_id=payload.os_id, veiculo_id=payload.veiculo_id,
        filial_id=(veic.filial_id if veic else None),
        tipo_alerta=payload.tipo_alerta,
        telefone=telefone,
        template_name=payload.template or payload.tipo_alerta,
        mensagem=mensagem,
        status="pending" if settings.EVOLUTION_ENABLED else "sent",  # mock entrega imediata
        enviado_por=user.id,
    )
    db.add(alerta)
    db.commit()
    db.refresh(alerta)
    result = dispatch_alerta(alerta)
    db.commit()
    return AlertaPreview(
        mensagem=mensagem, telefone=telefone,
        enviado=result.get("sent", False), alerta_id=alerta.id,
    )
