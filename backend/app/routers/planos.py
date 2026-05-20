"""Planos preventivos — CRUD com gestão admin."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_role
from ..models import PlanoPreventiva, User
from ..schemas import PlanoOut

router = APIRouter(prefix="/planos", tags=["planos"])


class PlanoCreate(BaseModel):
    modelo_veiculo: str
    item: str
    descricao: Optional[str] = None
    km_intervalo: Optional[int] = None
    dias_intervalo: Optional[int] = None
    antecedencia_dias: int = 7
    ativo: bool = True


class PlanoUpdate(BaseModel):
    modelo_veiculo: Optional[str] = None
    item: Optional[str] = None
    descricao: Optional[str] = None
    km_intervalo: Optional[int] = None
    dias_intervalo: Optional[int] = None
    antecedencia_dias: Optional[int] = None
    ativo: Optional[bool] = None


@router.get("", response_model=List[PlanoOut])
def list_planos(
    modelo: Optional[str] = Query(default=None),
    ativo: bool = Query(default=True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(PlanoPreventiva).filter(PlanoPreventiva.ativo.is_(ativo))
    if modelo:
        q = q.filter(PlanoPreventiva.modelo_veiculo.ilike(f"%{modelo}%"))
    return q.order_by(PlanoPreventiva.modelo_veiculo, PlanoPreventiva.item).all()


@router.post("", response_model=PlanoOut, status_code=201)
def create_plano(
    payload: PlanoCreate,
    user: User = Depends(require_role(["admin", "filial_responsavel"])),
    db: Session = Depends(get_db),
):
    if not payload.km_intervalo and not payload.dias_intervalo:
        raise HTTPException(400, "Pelo menos 1 intervalo (km ou dias) é obrigatório")
    plano = PlanoPreventiva(**payload.model_dump())
    db.add(plano)
    db.commit()
    db.refresh(plano)
    return plano


@router.patch("/{plano_id}", response_model=PlanoOut)
def update_plano(
    plano_id: int,
    payload: PlanoUpdate,
    user: User = Depends(require_role(["admin", "filial_responsavel"])),
    db: Session = Depends(get_db),
):
    p = db.query(PlanoPreventiva).filter(PlanoPreventiva.id == plano_id).first()
    if not p:
        raise HTTPException(404, "Plano não encontrado")
    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(p, field, val)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{plano_id}")
def delete_plano(
    plano_id: int,
    user: User = Depends(require_role(["admin", "filial_responsavel"])),
    db: Session = Depends(get_db),
):
    p = db.query(PlanoPreventiva).filter(PlanoPreventiva.id == plano_id).first()
    if not p:
        raise HTTPException(404, "Plano não encontrado")
    db.delete(p)
    db.commit()
    return {"ok": True, "id": plano_id}
