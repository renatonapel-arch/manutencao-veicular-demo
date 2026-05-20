"""Planos preventivos — CRUD básico + listagem."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import PlanoPreventiva, User
from ..schemas import PlanoOut

router = APIRouter(prefix="/planos", tags=["planos"])


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
