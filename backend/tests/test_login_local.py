"""Login local desligado por padrão (achado de segurança de 01/10/2026).

Em produção o módulo abria como admin para qualquer pessoa com o link: o front
fazia auto-login com o usuário seed e a senha de demo. Agora o login local só
existe com LOCAL_LOGIN_ENABLED=true; sem isso nem a senha certa nem um token
local emitido antes abrem a porta. O SSO do Clavis continua valendo.

O hash de senha é trocado por um dublê ("plain:<senha>"): o que se testa aqui é
a TRAVA, não o bcrypt — e assim o teste não depende da combinação passlib/bcrypt
instalada na máquina.
"""
import time

import pytest
from fastapi import HTTPException
from jose import jwt
from sqlalchemy import select

from app import dependencies, models
from app.auth import create_access_token
from app.config import Settings, settings
from app.routers import auth_routes
from app.schemas import LoginRequest


@pytest.fixture(autouse=True)
def hash_de_mentira(monkeypatch):
    monkeypatch.setattr(auth_routes, "verify_password", lambda plain, hashed: hashed == f"plain:{plain}")
    monkeypatch.setattr(dependencies, "hash_password", lambda plain: f"plain:{plain}")


@pytest.fixture
def login_local(monkeypatch):
    def _set(ligado: bool):
        monkeypatch.setattr(settings, "LOCAL_LOGIN_ENABLED", ligado)
    return _set


async def _user(db, senha: str, email: str = "demo@napel.local") -> models.User:
    u = models.User(email=email, role="admin", filial_id=None, nome="Demo",
                    senha_hash=f"plain:{senha}", ativo=True)
    db.add(u)
    await db.commit()
    return u


def test_padrao_e_desligado():
    """Seguro por padrão: quem esquecer a variável em produção fica fechado."""
    assert Settings.model_fields["LOCAL_LOGIN_ENABLED"].default is False


async def test_config_reflete_a_flag(login_local):
    login_local(False)
    assert await auth_routes.auth_config() == {"local_login": False}
    login_local(True)
    assert await auth_routes.auth_config() == {"local_login": True}


# a 2ª senha é a constante que TODO usuário criado pelo SSO do Clavis tem no banco
@pytest.mark.parametrize("senha", ["password123", "clavis-sso-no-local-login"])
async def test_login_recusado_com_a_senha_certa_quando_desligado(db, login_local, senha):
    await _user(db, senha)
    login_local(False)
    with pytest.raises(HTTPException) as e:
        await auth_routes.login(LoginRequest(email="demo@napel.local", senha=senha), db)
    assert e.value.status_code == 403


async def test_login_funciona_quando_ligado(db, login_local):
    await _user(db, "password123")
    login_local(True)
    r = await auth_routes.login(LoginRequest(email="demo@napel.local", senha="password123"), db)
    assert r.access_token and r.user.email == "demo@napel.local"


async def test_token_local_emitido_antes_morre_quando_desligado(db, login_local):
    u = await _user(db, "password123")
    token, _ = create_access_token(u.id, u.role, u.filial_id, u.email)

    login_local(True)
    ok = await dependencies.get_current_user(authorization=f"Bearer {token}", db=db)
    assert ok.id == u.id

    login_local(False)  # o deploy desliga: o mesmo token (válido por 24 h) para de valer
    with pytest.raises(HTTPException) as e:
        await dependencies.get_current_user(authorization=f"Bearer {token}", db=db)
    assert e.value.status_code == 401


async def test_sso_do_clavis_continua_valendo_com_login_local_desligado(db, login_local, monkeypatch):
    # segredo de TESTE definido aqui — nunca o do Clavis de verdade
    monkeypatch.setattr(settings, "CLAVIS_JWT_SECRET", "segredo-so-de-teste-do-clavis")
    login_local(False)
    token = jwt.encode(
        {"sub": "42", "email": "pessoa@napel.com.br", "name": "Pessoa Teste", "role": "admin",
         "exp": int(time.time()) + 600},
        "segredo-so-de-teste-do-clavis", algorithm=settings.JWT_ALGORITHM,
    )
    u = await dependencies.get_current_user(authorization=f"Bearer {token}", db=db)
    assert u.email == "pessoa@napel.com.br" and u.role == "admin"
    assert (await db.execute(select(models.User).where(models.User.email == u.email))).scalar_one()
