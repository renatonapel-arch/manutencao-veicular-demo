"""Catálogo de oficinas — texto livre bloqueado, gestão via RBAC admin_oficinas."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_role
from ..models import OficinaPadronizada, OrdemServico, User
from ..schemas import OficinaCreate, OficinaOut

router = APIRouter(prefix="/oficinas", tags=["oficinas"])


@router.get("", response_model=List[OficinaOut])
def list_oficinas(
    q: Optional[str] = Query(default=None),
    ativa: bool = Query(default=True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(OficinaPadronizada).filter(OficinaPadronizada.ativa.is_(ativa))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            OficinaPadronizada.nome.ilike(like),
            OficinaPadronizada.cnpj.ilike(like),
            OficinaPadronizada.cidade.ilike(like),
        ))
    return query.order_by(OficinaPadronizada.nome).all()


@router.get("/{oid}/stats")
def oficina_stats(oid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    of = db.query(OficinaPadronizada).filter(OficinaPadronizada.id == oid).first()
    if not of:
        raise HTTPException(status_code=404)
    qry = db.query(
        func.count(OrdemServico.id).label("total_os"),
        func.coalesce(func.sum(OrdemServico.valor_total), 0).label("custo_total"),
        func.coalesce(func.avg(OrdemServico.valor_total), 0).label("ticket_medio"),
    ).filter(OrdemServico.oficina_id == oid)
    row = qry.first()
    return {
        "id": of.id, "nome": of.nome,
        "total_os": int(row.total_os or 0),
        "custo_total": float(row.custo_total or 0),
        "ticket_medio": float(row.ticket_medio or 0),
    }


@router.post("", response_model=OficinaOut, status_code=201)
def create_oficina(
    payload: OficinaCreate,
    user: User = Depends(require_role(["admin_oficinas", "admin"])),
    db: Session = Depends(get_db),
):
    nome_normalizado = payload.nome.strip()
    existing = db.query(OficinaPadronizada).filter(
        func.lower(func.trim(OficinaPadronizada.nome)) == nome_normalizado.lower()
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Oficina já existe (ID {existing.id})")
    of = OficinaPadronizada(nome=nome_normalizado, **payload.model_dump(exclude={"nome"}))
    db.add(of)
    db.commit()
    db.refresh(of)
    return of


@router.delete("/{oid}")
def deactivate_oficina(
    oid: int,
    user: User = Depends(require_role(["admin_oficinas", "admin"])),
    db: Session = Depends(get_db),
):
    of = db.query(OficinaPadronizada).filter(OficinaPadronizada.id == oid).first()
    if not of:
        raise HTTPException(status_code=404)
    of.ativa = False
    db.commit()
    return {"ok": True, "detail": "Oficina desativada"}
