"""CRUD da OS-Manutenção — coração do módulo.

Implementa: Idempotency-Key, máquina de estados, RBAC filial, validação NF, soft-delete.
"""
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import and_, func
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..dependencies import check_filial_access, get_current_user
from ..models import (AuditoriaOs, IdempotencyKey, OrdemServico, OsItemLinha,
                      StatusOsEnum, TipoItemEnum, TipoOsEnum, User,
                      VeiculoSnapshot)
from ..schemas import (ItemLinhaIn, ListaOSResponse, OrdemServicoCreate,
                       OrdemServicoDetalhe, OrdemServicoOut, OrdemServicoUpdate)
from ..validators import pode_encerrar, pode_transicao

log = logging.getLogger("manutencao.os")
router = APIRouter(prefix="/ordem-servico", tags=["ordem-servico"])


def _record_audit(db: Session, os_id: int, op: str, user: User, before: dict | None, after: dict | None, motivo: str | None = None):
    db.add(AuditoriaOs(
        os_id=os_id, operacao=op, user_id=user.id, filial_id=user.filial_id,
        before_data=before, after_data=after, motivo=motivo,
    ))


def _serialize_for_audit(os: OrdemServico) -> dict:
    return {
        "id": os.id, "status": os.status.value if os.status else None,
        "valor_total": float(os.valor_total or 0),
        "oficina_id": os.oficina_id, "km_veiculo": os.km_veiculo,
    }


def _recalc_valor(os: OrdemServico):
    subtotal = sum((it.subtotal or Decimal("0")) for it in os.itens)
    desconto = os.desconto_ajuste or Decimal("0")
    os.valor_total = subtotal + desconto


@router.post("", response_model=OrdemServicoOut, status_code=201)
def create_os(
    payload: OrdemServicoCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Idempotency check
    if idempotency_key:
        try:
            existing = db.query(IdempotencyKey).filter(
                IdempotencyKey.request_id == uuid.UUID(idempotency_key)
            ).first()
            if existing:
                os = db.query(OrdemServico).filter(OrdemServico.id == existing.resource_id).first()
                if os:
                    return os
        except (ValueError, TypeError):
            pass

    veiculo = db.query(VeiculoSnapshot).filter(VeiculoSnapshot.id == payload.veiculo_id).first()
    if not veiculo:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    if not check_filial_access(user, veiculo.filial_id):
        raise HTTPException(status_code=403, detail="Cross-filial denied")

    os = OrdemServico(
        request_id=payload.request_id,
        veiculo_id=veiculo.id, filial_id=veiculo.filial_id,
        tipo_os=TipoOsEnum(payload.tipo_os),
        status=StatusOsEnum.rascunho,
        km_veiculo=payload.km_veiculo, km_api_snapshot=veiculo.km_atual,
        oficina_id=payload.oficina_id,
        descricao_problema=payload.descricao_problema,
        data_agendada=payload.data_agendada,
        prazo_estimado_dias=payload.prazo_estimado_dias,
        created_by=user.id,
    )
    db.add(os)
    db.flush()

    subtotal_total = Decimal("0")
    for it in payload.itens:
        sub = it.valor_unitario * (it.quantidade or Decimal("1"))
        db.add(OsItemLinha(
            os_id=os.id, tipo_item=TipoItemEnum(it.tipo_item),
            descricao=it.descricao, sige_sku=it.sige_sku, sige_peca_id=it.sige_peca_id,
            quantidade=it.quantidade or Decimal("1"),
            valor_unitario=it.valor_unitario, subtotal=sub,
            garantia_dias=it.garantia_dias,
        ))
        subtotal_total += sub
    os.valor_total = subtotal_total

    if idempotency_key:
        try:
            db.add(IdempotencyKey(
                request_id=uuid.UUID(idempotency_key),
                resource_type="os_manutencao", resource_id=os.id,
                response_json={"id": os.id, "status": os.status.value},
            ))
        except (ValueError, TypeError):
            pass

    _record_audit(db, os.id, "INSERT", user, None, _serialize_for_audit(os))
    db.commit()
    db.refresh(os)
    log.info("OS criada · id=%s · veiculo=%s · user=%s", os.id, veiculo.placa, user.email)
    return os


@router.get("", response_model=ListaOSResponse)
def list_os(
    filial_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    veiculo_id: Optional[int] = Query(default=None),
    oficina_id: Optional[int] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(OrdemServico).filter(OrdemServico.deleted_at.is_(None))
    if user.role != "admin":
        query = query.filter(OrdemServico.filial_id == user.filial_id)
    elif filial_id:
        query = query.filter(OrdemServico.filial_id == filial_id)
    if status:
        query = query.filter(OrdemServico.status == status)
    if tipo:
        query = query.filter(OrdemServico.tipo_os == tipo)
    if veiculo_id:
        query = query.filter(OrdemServico.veiculo_id == veiculo_id)
    if oficina_id:
        query = query.filter(OrdemServico.oficina_id == oficina_id)
    if q:
        query = query.filter(OrdemServico.descricao_problema.ilike(f"%{q}%"))

    total = query.count()
    items = (
        query
        .options(selectinload(OrdemServico.veiculo), selectinload(OrdemServico.oficina))
        .order_by(OrdemServico.data_abertura.desc())
        .offset(offset).limit(limit).all()
    )
    # Popula campos derivados (placa, modelo, oficina_nome) pra UI evitar 2º round-trip
    out = []
    for o in items:
        d = OrdemServicoOut.model_validate(o)
        d.veiculo_placa = o.veiculo.placa if o.veiculo else None
        d.veiculo_modelo = o.veiculo.modelo if o.veiculo else None
        d.oficina_nome = o.oficina.nome if o.oficina else None
        out.append(d)
    return ListaOSResponse(data=out, total=total, limit=limit, offset=offset)


@router.get("/{os_id}", response_model=OrdemServicoDetalhe)
def get_os(os_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    os = (
        db.query(OrdemServico)
        .options(selectinload(OrdemServico.itens), selectinload(OrdemServico.anexos),
                 selectinload(OrdemServico.veiculo), selectinload(OrdemServico.oficina))
        .filter(OrdemServico.id == os_id, OrdemServico.deleted_at.is_(None))
        .first()
    )
    if not os:
        raise HTTPException(status_code=404, detail="OS não encontrada")
    if not check_filial_access(user, os.filial_id):
        raise HTTPException(status_code=403, detail="Cross-filial denied")
    return os


@router.patch("/{os_id}", response_model=OrdemServicoOut)
def update_os(
    os_id: int, payload: OrdemServicoUpdate,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    os = db.query(OrdemServico).filter(OrdemServico.id == os_id, OrdemServico.deleted_at.is_(None)).first()
    if not os:
        raise HTTPException(status_code=404)
    if not check_filial_access(user, os.filial_id):
        raise HTTPException(status_code=403)

    before = _serialize_for_audit(os)
    motivo = None

    if payload.status:
        novo = StatusOsEnum(payload.status)
        if novo != os.status:
            if not pode_transicao(os.status, novo):
                raise HTTPException(status_code=400,
                                    detail=f"Transição inválida: {os.status.value} → {novo.value}")
            if novo == StatusOsEnum.encerrada:
                ok, erros = pode_encerrar(os)
                if not ok:
                    raise HTTPException(status_code=400,
                                        detail="Não pode encerrar: " + "; ".join(erros))
                os.data_encerramento = datetime.utcnow()
            os.status = novo
            motivo = f"Status: {before['status']} → {novo.value}"

    for field in ("oficina_id", "descricao_problema", "garantia_peca_dias",
                  "garantia_servico_dias", "garantia_observacoes", "desconto_ajuste"):
        val = getattr(payload, field, None)
        if val is not None:
            setattr(os, field, val)

    if payload.motivo_cancelamento:
        os.observacoes_internas = (os.observacoes_internas or "") + f"\n[cancel] {payload.motivo_cancelamento}"

    _recalc_valor(os)
    _record_audit(db, os.id, "UPDATE", user, before, _serialize_for_audit(os), motivo)
    db.commit()
    db.refresh(os)
    return os


@router.post("/{os_id}/itens", status_code=201)
def add_item(os_id: int, item: ItemLinhaIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    os = db.query(OrdemServico).filter(OrdemServico.id == os_id).first()
    if not os:
        raise HTTPException(404)
    if not check_filial_access(user, os.filial_id):
        raise HTTPException(403)
    sub = item.valor_unitario * (item.quantidade or Decimal("1"))
    novo = OsItemLinha(
        os_id=os.id, tipo_item=TipoItemEnum(item.tipo_item),
        descricao=item.descricao, sige_sku=item.sige_sku,
        quantidade=item.quantidade or Decimal("1"),
        valor_unitario=item.valor_unitario, subtotal=sub,
        garantia_dias=item.garantia_dias,
    )
    db.add(novo)
    db.flush()
    db.refresh(os)
    _recalc_valor(os)
    db.commit()
    return {"id": novo.id, "valor_total": float(os.valor_total)}


@router.delete("/{os_id}/itens/{item_id}")
def del_item(os_id: int, item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    it = db.query(OsItemLinha).filter(OsItemLinha.id == item_id, OsItemLinha.os_id == os_id).first()
    if not it:
        raise HTTPException(404)
    os = it.os
    if not check_filial_access(user, os.filial_id):
        raise HTTPException(403)
    db.delete(it)
    db.flush()
    db.refresh(os)
    _recalc_valor(os)
    db.commit()
    return {"ok": True, "valor_total": float(os.valor_total)}
