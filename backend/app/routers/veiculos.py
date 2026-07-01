"""Listagem de veículos (consumido do Controle Patrimonial via cache)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import check_filial_access, get_current_user
from ..models import User, VeiculoSnapshot
from ..schemas import VeiculoOut

router = APIRouter(prefix="/veiculos", tags=["veiculos"])


@router.get("", response_model=List[VeiculoOut])
async def list_veiculos(
    filial_id: Optional[int] = Query(default=None),
    q: Optional[str] = Query(default=None, description="Busca por placa ou modelo"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(VeiculoSnapshot).where(VeiculoSnapshot.ativo.is_(True))
    if user.role != "admin":
        stmt = stmt.where(VeiculoSnapshot.filial_id == user.filial_id)
    elif filial_id:
        stmt = stmt.where(VeiculoSnapshot.filial_id == filial_id)
    if q:
        like = f"%{q.upper()}%"
        stmt = stmt.where(or_(
            VeiculoSnapshot.placa.ilike(like),
            VeiculoSnapshot.modelo.ilike(like),
        ))
    stmt = stmt.order_by(VeiculoSnapshot.placa)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{vid}", response_model=VeiculoOut)
async def get_veiculo(
    vid: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    v = await db.get(VeiculoSnapshot, vid)
    if not v:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    if not check_filial_access(user, v.filial_id):
        raise HTTPException(status_code=403, detail="Cross-filial denied")
    return v
