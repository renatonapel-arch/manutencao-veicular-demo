"""Auth + RBAC dependencies (FastAPI Depends)."""
from typing import Callable, List, Optional

from fastapi import Depends, Header, HTTPException
from jose import JWTError
from sqlalchemy.orm import Session

from .auth import decode_token, is_blacklisted
from .database import get_db
from .models import User


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
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
    user = db.query(User).filter(User.id == user_id, User.ativo.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user


def require_role(roles: List[str]) -> Callable:
    def _dep(user: User = Depends(get_current_user)) -> User:
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
        raise HTTPException(status_code=403, detail=f"Cross-filial denied (user {user.filial_id} → {filial_id})")
