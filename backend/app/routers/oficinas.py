"""Catálogo de oficinas — texto livre bloqueado, gestão via RBAC admin_oficinas (async)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_user, require_role
from ..models import OficinaPadronizada, OrdemServico, User
from ..schemas import OficinaCreate, OficinaOut

router = APIRouter(prefix="/oficinas", tags=["oficinas"])


@router.get("", response_model=List[OficinaOut])
async def list_oficinas(
    q: Optional[str] = Query(default=None),
    ativa: bool = Query(default=True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(OficinaPadronizada).where(OficinaPadronizada.ativa.is_(ativa))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(
            OficinaPadronizada.nome.ilike(like),
            OficinaPadronizada.cnpj.ilike(like),
            OficinaPadronizada.cidade.ilike(like),
        ))
    stmt = stmt.order_by(OficinaPadronizada.nome)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{oid}/stats")
async def oficina_stats(
    oid: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    of = await db.get(OficinaPadronizada, oid)
    if not of:
        raise HTTPException(status_code=404)
    stmt = select(
        func.count(OrdemServico.id).label("total_os"),
        func.coalesce(func.sum(OrdemServico.valor_total), 0).label("custo_total"),
        func.coalesce(func.avg(OrdemServico.valor_total), 0).label("ticket_medio"),
    ).where(OrdemServico.oficina_id == oid)
    row = (await db.execute(stmt)).one()
    return {
        "id": of.id, "nome": of.nome,
        "total_os": int(row.total_os or 0),
        "custo_total": float(row.custo_total or 0),
        "ticket_medio": float(row.ticket_medio or 0),
    }


@router.post("", response_model=OficinaOut, status_code=201)
async def create_oficina(
    payload: OficinaCreate,
    user: User = Depends(require_role(["admin_oficinas", "admin", "filial_responsavel"])),
    db: AsyncSession = Depends(get_db),
):
    nome_normalizado = payload.nome.strip()
    if not nome_normalizado:
        raise HTTPException(status_code=400, detail="Nome obrigatório")
    stmt = select(OficinaPadronizada).where(
        func.lower(func.trim(OficinaPadronizada.nome)) == nome_normalizado.lower()
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Oficina já existe (ID {existing.id})")

    # Normaliza strings vazias pra None (evita UNIQUE violation em CNPJ='')
    data = payload.model_dump(exclude={"nome"})
    for k in ("cnpj", "telefone", "cidade", "uf"):
        v = data.get(k)
        if isinstance(v, str):
            data[k] = v.strip() or None

    of = OficinaPadronizada(nome=nome_normalizado, **data)
    db.add(of)
    await db.commit()
    await db.refresh(of)
    return of


@router.delete("/{oid}")
async def deactivate_oficina(
    oid: int,
    user: User = Depends(require_role(["admin_oficinas", "admin", "filial_responsavel"])),
    db: AsyncSession = Depends(get_db),
):
    of = await db.get(OficinaPadronizada, oid)
    if not of:
        raise HTTPException(status_code=404)
    of.ativa = False
    await db.commit()
    return {"ok": True, "detail": "Oficina desativada"}
