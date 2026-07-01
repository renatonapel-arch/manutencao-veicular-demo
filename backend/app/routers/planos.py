"""Planos preventivos — CRUD com gestão admin (async)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
async def list_planos(
    modelo: Optional[str] = Query(default=None),
    ativo: bool = Query(default=True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PlanoPreventiva).where(PlanoPreventiva.ativo.is_(ativo))
    if modelo:
        stmt = stmt.where(PlanoPreventiva.modelo_veiculo.ilike(f"%{modelo}%"))
    stmt = stmt.order_by(PlanoPreventiva.modelo_veiculo, PlanoPreventiva.item)
    return list((await db.execute(stmt)).scalars().all())


@router.post("", response_model=PlanoOut, status_code=201)
async def create_plano(
    payload: PlanoCreate,
    user: User = Depends(require_role(["admin", "filial_responsavel"])),
    db: AsyncSession = Depends(get_db),
):
    if not payload.km_intervalo and not payload.dias_intervalo:
        raise HTTPException(400, "Pelo menos 1 intervalo (km ou dias) é obrigatório")
    plano = PlanoPreventiva(**payload.model_dump())
    db.add(plano)
    await db.commit()
    await db.refresh(plano)
    return plano


@router.patch("/{plano_id}", response_model=PlanoOut)
async def update_plano(
    plano_id: int,
    payload: PlanoUpdate,
    user: User = Depends(require_role(["admin", "filial_responsavel"])),
    db: AsyncSession = Depends(get_db),
):
    p = await db.get(PlanoPreventiva, plano_id)
    if not p:
        raise HTTPException(404, "Plano não encontrado")
    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(p, field, val)
    await db.commit()
    await db.refresh(p)
    return p


@router.delete("/{plano_id}")
async def delete_plano(
    plano_id: int,
    user: User = Depends(require_role(["admin", "filial_responsavel"])),
    db: AsyncSession = Depends(get_db),
):
    p = await db.get(PlanoPreventiva, plano_id)
    if not p:
        raise HTTPException(404, "Plano não encontrado")
    await db.delete(p)
    await db.commit()
    return {"ok": True, "id": plano_id}
