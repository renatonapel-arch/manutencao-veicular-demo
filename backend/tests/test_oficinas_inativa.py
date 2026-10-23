"""#0267: "Oficina já existe (ID 70)" sobre uma oficina DESATIVADA que a lista não mostra,
e o sync-oficinas desativando oficina cadastrada à mão."""
import pytest
from fastapi import HTTPException

from app.integrations import oleo_client
from app.models import OficinaPadronizada
from app.routers import admin, oficinas
from app.schemas import OficinaCreate


async def _of(db, nome, ativa, **kw):
    o = OficinaPadronizada(nome=nome, ativa=ativa, **kw)
    db.add(o)
    await db.commit()
    await db.refresh(o)
    return o


async def test_nome_de_oficina_inativa_reativa_e_completa_os_vazios(db, admin_user):
    antiga = await _of(db, "Borracharia Bonsucesso", False)
    r = await oficinas.create_oficina(OficinaCreate(nome=" borracharia bonsucesso ", cidade="Ponta Grossa", uf="PR"), user=admin_user, db=db)
    assert r.id == antiga.id and r.ativa is True and r.manual is True
    assert (r.cidade, r.uf) == ("Ponta Grossa", "PR")
    assert [o.id for o in await oficinas.list_oficinas(q=None, ativa=True, user=admin_user, db=db)] == [antiga.id]


async def test_reativar_nao_sobrescreve_dado_ja_preenchido(db, admin_user):
    await _of(db, "Oficina X", False, cidade="Maringá", uf="PR")
    r = await oficinas.create_oficina(OficinaCreate(nome="Oficina X", cidade="Ponta Grossa", uf="SP", telefone="4499"), user=admin_user, db=db)
    assert (r.cidade, r.uf, r.telefone) == ("Maringá", "PR", "4499")


async def test_nome_de_oficina_ativa_continua_409_com_orientacao(db, admin_user):
    await _of(db, "Oficina Y", True)
    with pytest.raises(HTTPException) as e:
        await oficinas.create_oficina(OficinaCreate(nome="oficina y"), user=admin_user, db=db)
    assert e.value.status_code == 409 and "selecione na lista" in e.value.detail


async def test_oficina_nova_nasce_manual(db, admin_user):
    r = await oficinas.create_oficina(OficinaCreate(nome="Nova Borracharia"), user=admin_user, db=db)
    assert r.manual is True and r.ativa is True


async def test_sync_nao_desativa_nem_apaga_dados_de_oficina_manual(db, admin_user, monkeypatch):
    manual = await _of(db, "Borracharia Bonsucesso", True, manual=True, cidade="Ponta Grossa", uf="PR", telefone="4499")
    antiga = await _of(db, "Oficina Seed Velha", True)  # não manual, fora do catálogo → continua sendo desativada

    async def _remotas():
        return [{"nome": "Oficina Real", "cidades": ["Maringá"]}]

    monkeypatch.setattr(oleo_client, "listar_oficinas", _remotas)
    r = await admin.trigger_sync_oficinas(user=admin_user, db=db)
    await db.refresh(manual)
    await db.refresh(antiga)
    assert manual.ativa is True and manual.telefone == "4499" and manual.cidade == "Ponta Grossa"
    assert antiga.ativa is False and r["desativadas"] == 1
