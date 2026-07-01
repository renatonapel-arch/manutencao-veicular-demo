"""CRUD da OS-Manutenção — coração do módulo (async).

Implementa: Idempotency-Key, transições via service.py, RBAC filial, soft-delete.
"""
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import service as svc
from ..database import get_db
from ..dependencies import check_filial_access, get_current_user
from ..models import (
    AuditoriaOs, IdempotencyKey, OrdemServico, OsItemLinha, User, VeiculoSnapshot,
)
from ..schemas import (
    ItemLinhaIn, ListaOSResponse, OrdemServicoCreate,
    OrdemServicoDetalhe, OrdemServicoOut, OrdemServicoUpdate,
)

log = logging.getLogger("manutencao.os")
router = APIRouter(prefix="/ordem-servico", tags=["ordem-servico"])


async def _record_audit(
    db: AsyncSession, os_id: int, op: str, user: User,
    before: dict | None, after: dict | None, motivo: str | None = None,
):
    db.add(AuditoriaOs(
        os_id=os_id, operacao=op, user_id=user.id, filial_id=user.filial_id,
        before_data=before, after_data=after, motivo=motivo,
    ))


def _serialize_for_audit(os: OrdemServico) -> dict:
    return {
        "id": os.id, "status": os.status,
        "valor_total": float(os.valor_total or 0),
        "oficina_id": os.oficina_id, "km_veiculo": os.km_veiculo,
    }


async def _recalc_valor(db: AsyncSession, os: OrdemServico):
    """Recalcula valor_total via SELECT SUM (refresh de relationship nao funciona em AsyncSession)."""
    stmt = select(func.coalesce(func.sum(OsItemLinha.subtotal), 0)).where(
        OsItemLinha.os_id == os.id
    )
    subtotal = Decimal(str((await db.execute(stmt)).scalar_one()))
    desconto = os.desconto_ajuste or Decimal("0")
    os.valor_total = subtotal + desconto


# ---------- CRUD ----------

@router.post("", response_model=OrdemServicoOut, status_code=201)
async def create_os(
    payload: OrdemServicoCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Idempotency check
    if idempotency_key:
        try:
            key_uuid = uuid.UUID(idempotency_key)
            stmt = select(IdempotencyKey).where(IdempotencyKey.request_id == key_uuid)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                os = await db.get(OrdemServico, existing.resource_id)
                if os:
                    return os
        except (ValueError, TypeError):
            pass

    veiculo = await db.get(VeiculoSnapshot, payload.veiculo_id)
    if not veiculo:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    if not check_filial_access(user, veiculo.filial_id):
        raise HTTPException(status_code=403, detail="Cross-filial denied")

    os = OrdemServico(
        request_id=payload.request_id,
        veiculo_id=veiculo.id, filial_id=veiculo.filial_id,
        tipo_os=payload.tipo_os,
        status="rascunho",
        categoria=payload.categoria,
        urgencia=payload.urgencia,
        tipo_destino=payload.tipo_destino,
        km_veiculo=payload.km_veiculo, km_api_snapshot=veiculo.km_atual,
        oficina_id=payload.oficina_id,
        descricao_problema=payload.descricao_problema,
        data_agendada=payload.data_agendada,
        prazo_estimado_dias=payload.prazo_estimado_dias,
        aberto_por_user_id=user.id,
        funcionario_relator_id=payload.funcionario_relator_id,
    )
    db.add(os)
    await db.flush()

    subtotal_total = Decimal("0")
    for it in payload.itens:
        sub = it.valor_unitario * (it.quantidade or Decimal("1"))
        db.add(OsItemLinha(
            os_id=os.id, tipo_item=it.tipo_item,
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
                response_json={"id": os.id, "status": os.status},
            ))
        except (ValueError, TypeError):
            pass

    await _record_audit(db, os.id, "INSERT", user, None, _serialize_for_audit(os))
    await db.commit()
    await db.refresh(os)
    log.info("OS criada · id=%s · veiculo=%s · user=%s", os.id, veiculo.placa, user.email)
    return os


@router.get("", response_model=ListaOSResponse)
async def list_os(
    filial_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    categoria: Optional[str] = Query(default=None),
    veiculo_id: Optional[int] = Query(default=None),
    oficina_id: Optional[int] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base = select(OrdemServico).where(OrdemServico.deleted_at.is_(None))
    if user.role != "admin":
        base = base.where(OrdemServico.filial_id == user.filial_id)
    elif filial_id:
        base = base.where(OrdemServico.filial_id == filial_id)
    if status:
        base = base.where(OrdemServico.status == status)
    if tipo:
        base = base.where(OrdemServico.tipo_os == tipo)
    if categoria:
        base = base.where(OrdemServico.categoria == categoria)
    if veiculo_id:
        base = base.where(OrdemServico.veiculo_id == veiculo_id)
    if oficina_id:
        base = base.where(OrdemServico.oficina_id == oficina_id)
    if q:
        base = base.where(OrdemServico.descricao_problema.ilike(f"%{q}%"))

    count_stmt = select(func.count()).select_from(base.subquery())
    total = int((await db.execute(count_stmt)).scalar_one())

    items_stmt = (
        base.options(
            selectinload(OrdemServico.veiculo),
            selectinload(OrdemServico.oficina),
        )
        .order_by(OrdemServico.data_abertura.desc())
        .offset(offset).limit(limit)
    )
    items = list((await db.execute(items_stmt)).scalars().all())

    out = []
    for o in items:
        d = OrdemServicoOut.model_validate(o)
        d.veiculo_placa = o.veiculo.placa if o.veiculo else None
        d.veiculo_modelo = o.veiculo.modelo if o.veiculo else None
        d.oficina_nome = o.oficina.nome if o.oficina else None
        out.append(d)
    return ListaOSResponse(data=out, total=total, limit=limit, offset=offset)


@router.get("/{os_id}", response_model=OrdemServicoDetalhe)
async def get_os(
    os_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(OrdemServico)
        .options(
            selectinload(OrdemServico.itens), selectinload(OrdemServico.anexos),
            selectinload(OrdemServico.veiculo), selectinload(OrdemServico.oficina),
        )
        .where(OrdemServico.id == os_id, OrdemServico.deleted_at.is_(None))
    )
    os = (await db.execute(stmt)).scalar_one_or_none()
    if not os:
        raise HTTPException(status_code=404, detail="OS não encontrada")
    if not check_filial_access(user, os.filial_id):
        raise HTTPException(status_code=403, detail="Cross-filial denied")
    return os


@router.patch("/{os_id}", response_model=OrdemServicoOut)
async def update_os(
    os_id: int, payload: OrdemServicoUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Atualização de campos gerais (sem transição de status).

    Transição de status agora vai por /os/{id}/{acao} (ver seção Transições).
    """
    os = await svc.get_os(db, os_id)
    if not os:
        raise HTTPException(status_code=404)
    if not check_filial_access(user, os.filial_id):
        raise HTTPException(status_code=403)

    before = _serialize_for_audit(os)

    for field in ("oficina_id", "descricao_problema", "garantia_peca_dias",
                  "garantia_servico_dias", "garantia_observacoes", "desconto_ajuste",
                  "categoria", "urgencia", "tipo_destino"):
        val = getattr(payload, field, None)
        if val is not None:
            setattr(os, field, val)

    if payload.motivo_cancelamento:
        os.observacoes_internas = (
            (os.observacoes_internas or "") + f"\n[cancel] {payload.motivo_cancelamento}"
        )

    await _recalc_valor(db, os)
    await _record_audit(db, os.id, "UPDATE", user, before, _serialize_for_audit(os))
    await db.commit()
    await db.refresh(os)
    return os


@router.post("/{os_id}/itens", status_code=201)
async def add_item(
    os_id: int, item: ItemLinhaIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    os = await svc.get_os(db, os_id)
    if not os:
        raise HTTPException(404)
    if not check_filial_access(user, os.filial_id):
        raise HTTPException(403)
    sub = item.valor_unitario * (item.quantidade or Decimal("1"))
    novo = OsItemLinha(
        os_id=os.id, tipo_item=item.tipo_item,
        descricao=item.descricao, sige_sku=item.sige_sku,
        quantidade=item.quantidade or Decimal("1"),
        valor_unitario=item.valor_unitario, subtotal=sub,
        garantia_dias=item.garantia_dias,
    )
    db.add(novo)
    await db.flush()
    await _recalc_valor(db, os)
    await db.commit()
    await db.refresh(os)
    return {"id": novo.id, "valor_total": float(os.valor_total)}


@router.delete("/{os_id}/itens/{item_id}")
async def del_item(
    os_id: int, item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(OsItemLinha).where(
        OsItemLinha.id == item_id, OsItemLinha.os_id == os_id
    )
    it = (await db.execute(stmt)).scalar_one_or_none()
    if not it:
        raise HTTPException(404)
    os = await svc.get_os(db, os_id)
    if not os or not check_filial_access(user, os.filial_id):
        raise HTTPException(403)
    await db.delete(it)
    await db.flush()
    await _recalc_valor(db, os)
    await db.commit()
    await db.refresh(os)
    return {"ok": True, "valor_total": float(os.valor_total)}


# ---------- Transições (via service.py) ----------

@router.post("/{os_id}/abrir", response_model=OrdemServicoOut)
async def abrir(os_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await svc.transicionar(db, os_id, "aberta", user)


@router.post("/{os_id}/triagem", response_model=OrdemServicoOut)
async def triagem(os_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await svc.transicionar(db, os_id, "em_triagem", user)


@router.post("/{os_id}/enviar-orcamento", response_model=OrdemServicoOut)
async def enviar_orcamento(os_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await svc.transicionar(db, os_id, "aguardando_orcamento", user)


@router.post("/{os_id}/submeter-orcamento", response_model=OrdemServicoOut)
async def submeter_orcamento(os_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await svc.submeter_orcamento(db, os_id, user)


@router.post("/{os_id}/aprovar", response_model=OrdemServicoOut)
async def aprovar(
    os_id: int,
    observacoes: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.aprovar(db, os_id, user, observacoes=observacoes)


@router.post("/{os_id}/reprovar", response_model=OrdemServicoOut)
async def reprovar(
    os_id: int, motivo: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.reprovar(db, os_id, user, motivo=motivo)


@router.post("/{os_id}/pedir-2o-orcamento", response_model=OrdemServicoOut)
async def pedir_2o_orcamento(
    os_id: int, motivo: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.pedir_2o_orcamento(db, os_id, user, motivo=motivo)


@router.post("/{os_id}/iniciar-execucao", response_model=OrdemServicoOut)
async def iniciar_execucao(os_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await svc.transicionar(db, os_id, "em_execucao", user)


@router.post("/{os_id}/aguardando-peca", response_model=OrdemServicoOut)
async def aguardando_peca(os_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await svc.transicionar(db, os_id, "aguardando_peca", user)


@router.post("/{os_id}/retomar-execucao", response_model=OrdemServicoOut)
async def retomar_execucao(os_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await svc.transicionar(db, os_id, "em_execucao", user)


@router.post("/{os_id}/encerrar", response_model=OrdemServicoOut)
async def encerrar(os_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await svc.transicionar(db, os_id, "encerrada", user)


@router.post("/{os_id}/cancelar", response_model=OrdemServicoOut)
async def cancelar(
    os_id: int, motivo: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.transicionar(db, os_id, "cancelada", user, motivo=motivo)


@router.post("/{os_id}/reabrir-garantia", response_model=OrdemServicoOut, status_code=201)
async def reabrir_garantia(os_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await svc.reabrir_em_garantia(db, os_id, user)


@router.delete("/{os_id}")
async def delete_os(
    os_id: int, motivo: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await svc.soft_delete_os(db, os_id, user, motivo=motivo)
    return {"ok": True}
