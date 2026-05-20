"""Login / logout / me."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from jose import JWTError
from sqlalchemy.orm import Session

from ..auth import blacklist_jti, create_access_token, decode_token, verify_password
from ..database import get_db
from ..dependencies import get_current_user
from ..models import User
from ..schemas import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.email == payload.email.lower().strip(),
        User.ativo.is_(True),
    ).first()
    if not user or not verify_password(payload.senha, user.senha_hash):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    token, _jti = create_access_token(user.id, user.role, user.filial_id, user.email)
    user.last_login_at = datetime.utcnow()
    db.commit()
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/logout")
def logout(authorization: Optional[str] = Header(default=None), user: User = Depends(get_current_user)):
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
def me(user: User = Depends(get_current_user)):
    return user
