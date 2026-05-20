"""Listagem de veículos (consumido do Controle Patrimonial via cache)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import check_filial_access, get_current_user
from ..models import User, VeiculoSnapshot
from ..schemas import VeiculoOut

router = APIRouter(prefix="/veiculos", tags=["veiculos"])


@router.get("", response_model=List[VeiculoOut])
def list_veiculos(
    filial_id: Optional[int] = Query(default=None),
    q: Optional[str] = Query(default=None, description="Busca por placa ou modelo"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(VeiculoSnapshot).filter(VeiculoSnapshot.ativo.is_(True))
    if user.role != "admin":
        query = query.filter(VeiculoSnapshot.filial_id == user.filial_id)
    elif filial_id:
        query = query.filter(VeiculoSnapshot.filial_id == filial_id)
    if q:
        like = f"%{q.upper()}%"
        from sqlalchemy import or_
        query = query.filter(or_(
            VeiculoSnapshot.placa.ilike(like),
            VeiculoSnapshot.modelo.ilike(like),
        ))
    return query.order_by(VeiculoSnapshot.placa).all()


@router.get("/{vid}", response_model=VeiculoOut)
def get_veiculo(vid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    v = db.query(VeiculoSnapshot).filter(VeiculoSnapshot.id == vid).first()
    if not v:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    if not check_filial_access(user, v.filial_id):
        raise HTTPException(status_code=403, detail="Cross-filial denied")
    return v
