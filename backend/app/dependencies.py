"""Auth + RBAC dependencies (FastAPI Depends) — async.

Compatível com padrão Clavis (troca_carteira, cadastro_contatos):
- `AsyncSession = Depends(get_db)` em toda rota
- `await db.execute(select(...))` para lookups
"""
from typing import Callable, List, Optional

from fastapi import Depends, Header, HTTPException
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import decode_token, is_blacklisted
from .database import get_db
from .models import MembroManutencao, User


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token ausente")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {e}")
    jti = payload.get("jti")
    if jti and is_blacklisted(jti):
        raise HTTPException(status_code=401, detail="Token revogado")
    user_id = int(payload.get("sub", 0))
    stmt = select(User).where(User.id == user_id, User.ativo.is_(True))
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user


def require_role(roles: List[str]) -> Callable:
    async def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail=f"Role '{user.role}' sem permissão")
        return user
    return _dep


def check_filial_access(user: User, filial_id: Optional[int]) -> bool:
    """Admin vê tudo; demais só veem a própria filial."""
    if user.role == "admin":
        return True
    if filial_id is None:
        return False
    return user.filial_id == filial_id


def enforce_filial_access(user: User, filial_id: int) -> None:
    if not check_filial_access(user, filial_id):
        raise HTTPException(
            status_code=403,
            detail=f"Cross-filial denied (user {user.filial_id} → {filial_id})",
        )


# ---------- Papéis do módulo Manutenção (usa MembroManutencao) ----------

async def get_membro(
    db: AsyncSession, user: User, filial_id: Optional[int] = None,
) -> Optional[MembroManutencao]:
    """Retorna o vínculo do user com o módulo manutenção (opcionalmente por filial)."""
    stmt = select(MembroManutencao).where(
        MembroManutencao.user_id == user.id,
        MembroManutencao.ativo.is_(True),
    )
    if filial_id is not None:
        stmt = stmt.where(MembroManutencao.filial_id == filial_id)
    result = await db.execute(stmt)
    return result.scalars().first()


def require_papel_manutencao(*papeis: str) -> Callable:
    """Exige um dos papéis do módulo (admin do Clavis sempre passa)."""
    async def _dep(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if user.role == "admin":
            return user
        membro = await get_membro(db, user)
        if not membro or membro.papel not in papeis:
            raise HTTPException(403, "Sem papel adequado na manutenção")
        return user
    return _dep
