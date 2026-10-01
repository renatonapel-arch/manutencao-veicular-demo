"""Login / logout / me."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import blacklist_jti, create_access_token, decode_token, verify_password
from ..config import settings
from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from ..schemas import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config")
async def auth_config():
    """Público. A SPA decide: formulário de demo (local) ou 'entre pelo Clavis'."""
    return {"local_login": settings.LOCAL_LOGIN_ENABLED}


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Checa ANTES de qualquer consulta ao banco. Os usuários SSO do Clavis também
    # têm senha local (constante no código), então a porta tem que ficar fechada
    # para todos, não só para os seeds.
    if not settings.LOCAL_LOGIN_ENABLED:
        raise HTTPException(status_code=403, detail="Login local desativado — entre pelo Clavis")
    stmt = select(User).where(
        User.email == payload.email.lower().strip(),
        User.ativo.is_(True),
    )
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not verify_password(payload.senha, user.senha_hash):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    token, _jti = create_access_token(user.id, user.role, user.filial_id, user.email)
    user.last_login_at = datetime.utcnow()
    await db.commit()
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/logout")
async def logout(
    authorization: Optional[str] = Header(default=None),
    user: User = Depends(get_current_user),
):
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = decode_token(token)
            jti = payload.get("jti")
            if jti:
                blacklist_jti(jti)
        except JWTError:
            pass
    return {"ok": True, "detail": "Token revogado"}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
