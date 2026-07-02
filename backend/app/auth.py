"""JWT + Redis blacklist + bcrypt — espelha ADR-09 do spec."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple

import redis
from jose import jwt
from passlib.context import CryptContext

from .config import settings

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_ctx.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(user_id: int, role: str, filial_id: Optional[int], email: str) -> Tuple[str, str]:
    jti = uuid.uuid4().hex
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "filial_id": filial_id,
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_TTL_HOURS),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict:
    """Decode dual-mode:

    1) Se `CLAVIS_JWT_SECRET` estiver setado, tenta validar como token do Clavis
       (SSO no piloto — Opção D). Payload esperado: `sub`, `email`, `name`, `role`.
       Se válido, marca `_source="clavis"` pra o get_current_user decidir se auto-provisiona.
    2) Fallback: valida como token próprio deste backend (auth local).

    Nunca emite tokens usando o secret do Clavis — só valida. Isso mantém a
    regra de "nunca sintetizar JWT com signing secret lido da infra".
    """
    if settings.CLAVIS_JWT_SECRET:
        try:
            payload = jwt.decode(
                token, settings.CLAVIS_JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            payload["_source"] = "clavis"
            return payload
        except jwt.JWTError:
            pass  # cai no local
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    payload["_source"] = "local"
    return payload


def blacklist_jti(jti: str, ttl_seconds: Optional[int] = None) -> None:
    ttl = ttl_seconds or (settings.JWT_TTL_HOURS * 3600)
    try:
        get_redis().setex(f"jwt:blacklist:{jti}", ttl, "1")
    except Exception:
        # Redis indisponível não derruba logout
        pass


def is_blacklisted(jti: str) -> bool:
    try:
        return get_redis().exists(f"jwt:blacklist:{jti}") == 1
    except Exception:
        return False
