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

from datetime import datetime

from .auth import decode_token, hash_password, is_blacklisted
from .config import settings
from .database import get_db
from .models import MembroManutencao, User

# Mapa role Clavis -> role deste módulo
# admin do Clavis (Renato/Hudson) -> admin do módulo
# gerente do Clavis (Cesar operacional) -> aprovador
# demais -> usuario (acesso restrito à própria filial via papel do módulo)
CLAVIS_ROLE_MAP = {
    "admin":      "admin",
    "gerente":    "aprovador",
    "financeiro": "aprovador",
    "operador":   "usuario",
    "vendedor":   "usuario",
}


def _allowlist() -> set[str]:
    raw = (settings.CLAVIS_ALLOWED_EMAILS or "").strip()
    if not raw:
        return set()
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


async def _provision_from_clavis(db: AsyncSession, payload: dict) -> User:
    """Cria/atualiza user local a partir do JWT do Clavis.

    Idempotente por email. Se allowlist estiver configurada, rejeita emails
    fora dela com 403 (não com 401 pra deixar claro que o token é válido mas
    o usuário não faz parte do piloto).
    """
    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail="JWT Clavis sem email")

    permitidos = _allowlist()
    if permitidos and email not in permitidos:
        raise HTTPException(
            status_code=403,
            detail="Módulo Manutenção em piloto — acesso não liberado pra este usuário",
        )

    role_clavis = (payload.get("role") or "").lower()
    role_local = CLAVIS_ROLE_MAP.get(role_clavis, "usuario")
    nome = payload.get("name") or email.split("@")[0].title()

    stmt = select(User).where(User.email == email)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user:
        # Atualiza role/nome caso tenha mudado no Clavis
        if user.role != role_local: user.role = role_local
        if user.nome != nome:       user.nome = nome
        user.last_login_at = datetime.utcnow()
        await db.commit()
        return user

    user = User(
        email=email, nome=nome, role=role_local, filial_id=None,
        senha_hash=hash_password("clavis-sso-no-local-login"),
        telefone=None, created_at=datetime.utcnow(),
    )
    db.add(user)
    await db.flush()
    # Membro admin global — dá acesso a todas as filiais no piloto.
    # Depois do piloto, o admin ajusta papel/filial via /admin.
    db.add(MembroManutencao(
        user_id=user.id, filial_id=0,
        papel="admin" if role_local == "admin" else "aprovador",
        funcionario_id=None, ativo=True,
    ))
    await db.commit()
    return user


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

    # SSO Clavis — auto-provisionamento por email
    if payload.get("_source") == "clavis":
        return await _provision_from_clavis(db, payload)

    # Auth local — lookup por sub (user_id)
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
    """Roles globais (admin/aprovador) veem tudo; demais só a própria filial.

    - admin: total no Clavis (todos módulos).
    - aprovador: role dedicada a quem aprova compras/OS entre filiais — não é
      restringido por filial de origem. Sem isso, Cesar tomava 403 e o papel
      ficava inutilizado.
    """
    if user.role in ("admin", "aprovador"):
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
        # filial 0 = "todas" — membro global (Hudson/Cesar) atende qualquer filial
        stmt = stmt.where(MembroManutencao.filial_id.in_([filial_id, 0]))
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
