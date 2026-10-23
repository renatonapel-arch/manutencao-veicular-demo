"""#0269: excluir foto/NF anexada por engano — exclusão SUAVE (arquivo fica no disco)."""
import io
import uuid

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.datastructures import Headers

from app.config import settings
from app.models import AnexosOs, AuditoriaOs, OrdemServico, VeiculoSnapshot
from app.routers import ordem_servico, upload
from app import validators


async def _os(db, admin, filial_id=1, status="aberta"):
    if not (await db.execute(select(VeiculoSnapshot))).first():
        db.add(VeiculoSnapshot(id=1, veiculo_patrimonial_id=1, placa="TST1A23", modelo="M", tipo="carro",
                               km_atual=1, filial_id=filial_id, ativo=True))
        await db.flush()
    o = OrdemServico(request_id=uuid.uuid4(), veiculo_id=1, filial_id=filial_id, aberto_por_user_id=admin.id,
                     tipo_os="corretiva_manual", km_veiculo=1, status=status)
    db.add(o)
    await db.commit()
    await db.refresh(o)
    return o


async def _anexo(db, os_, user, tipo="foto_problema"):
    a = AnexosOs(os_id=os_.id, tipo=tipo, arquivo_url="/uploads/x/a.jpg", uploaded_by=user.id)
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


async def _anexos_visiveis(db, os_id):
    # recarrega a OS e a relação do banco (sem expirar o resto da sessão)
    return (await db.execute(
        select(OrdemServico).options(selectinload(OrdemServico.anexos))
        .where(OrdemServico.id == os_id).execution_options(populate_existing=True)
    )).scalar_one()


async def test_gestor_exclui_suave_some_da_os_e_audita(db, admin_user):
    os_ = await _os(db, admin_user)
    a = await _anexo(db, os_, admin_user, "nf")
    os_id, a_id, uid = os_.id, a.id, admin_user.id  # ids antes de expirar a sessão
    assert validators.tem_nf(await _anexos_visiveis(db, os_id))
    r = await upload.delete_anexo(os_id, a_id, user=admin_user, db=db)
    assert r == {"ok": True}
    row = (await db.execute(select(AnexosOs).where(AnexosOs.id == a_id))).scalar_one()
    assert row.excluido_em is not None and row.excluido_por == uid  # linha fica (arquivo também)
    o = await _anexos_visiveis(db, os_id)
    assert o.anexos == [] and not validators.tem_nf(o)
    aud = (await db.execute(select(AuditoriaOs).where(AuditoriaOs.os_id == os_id, AuditoriaOs.operacao == "anexo:excluido"))).scalar_one()
    assert aud.user_id == uid and aud.before_data["tipo"] == "nf" and aud.before_data["arquivo"] == "/uploads/x/a.jpg"


@pytest.mark.parametrize("estado", ["encerrada", "cancelada"])
async def test_os_finalizada_recusa_409(db, admin_user, estado):
    os_ = await _os(db, admin_user, status=estado)
    a = await _anexo(db, os_, admin_user)
    with pytest.raises(HTTPException) as e:
        await upload.delete_anexo(os_.id, a.id, user=admin_user, db=db)
    assert e.value.status_code == 409
    assert len((await _anexos_visiveis(db, os_.id)).anexos) == 1


async def test_excluir_duas_vezes_da_404(db, admin_user):
    os_ = await _os(db, admin_user)
    a = await _anexo(db, os_, admin_user)
    await upload.delete_anexo(os_.id, a.id, user=admin_user, db=db)
    with pytest.raises(HTTPException) as e:
        await upload.delete_anexo(os_.id, a.id, user=admin_user, db=db)
    assert e.value.status_code == 404


async def test_motorista_exclui_so_o_que_ele_enviou(db, admin_user, motorista_user):
    os_ = await _os(db, admin_user)
    meu = await _anexo(db, os_, motorista_user)
    do_gestor = await _anexo(db, os_, admin_user)
    with pytest.raises(HTTPException) as e:
        await upload.delete_anexo(os_.id, do_gestor.id, user=motorista_user, db=db)
    assert e.value.status_code == 403
    assert (await upload.delete_anexo(os_.id, meu.id, user=motorista_user, db=db)) == {"ok": True}


async def test_responsavel_da_filial_exclui_de_qualquer_um_mas_so_na_sua_filial(db, admin_user, responsavel_user):
    os1 = await _os(db, admin_user, filial_id=1)
    a = await _anexo(db, os1, admin_user)
    assert (await upload.delete_anexo(os1.id, a.id, user=responsavel_user, db=db)) == {"ok": True}
    db.add(VeiculoSnapshot(id=2, veiculo_patrimonial_id=2, placa="OUT2B34", modelo="M", tipo="carro", km_atual=1, filial_id=2, ativo=True))
    os2 = OrdemServico(request_id=uuid.uuid4(), veiculo_id=2, filial_id=2, aberto_por_user_id=admin_user.id,
                       tipo_os="corretiva_manual", km_veiculo=1, status="aberta")
    db.add(os2)
    await db.commit()
    b = await _anexo(db, os2, admin_user)
    with pytest.raises(HTTPException) as e:
        await upload.delete_anexo(os2.id, b.id, user=responsavel_user, db=db)
    assert e.value.status_code == 403


async def test_api_da_os_nao_devolve_anexo_excluido(db, admin_user):
    os_ = await _os(db, admin_user)
    a1 = await _anexo(db, os_, admin_user)
    await _anexo(db, os_, admin_user)
    await upload.delete_anexo(os_.id, a1.id, user=admin_user, db=db)
    d = await ordem_servico.get_os(os_.id, user=admin_user, db=db)
    assert len(d.anexos) == 1 and d.anexos[0].id != a1.id and d.anexos[0].uploaded_by == admin_user.id


async def test_substituir_nf_exclui_a_anterior_na_mesma_gravacao(db, admin_user, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    os_ = await _os(db, admin_user)
    velha = await _anexo(db, os_, admin_user, "nf")
    os_id, velha_id = os_.id, velha.id
    arq = UploadFile(io.BytesIO(b"%PDF-1.4 teste"), filename="nf.pdf", headers=Headers({"content-type": "application/pdf"}))
    nova = await upload.upload_anexo(os_id, tipo="nf", posicao_pneu=None, substituir_nf=True, arquivo=arq, user=admin_user, db=db)
    nova_id = nova.id
    o = await _anexos_visiveis(db, os_id)
    assert [x.id for x in o.anexos] == [nova_id]
    assert (await db.get(AnexosOs, velha_id, populate_existing=True)).excluido_em is not None
    # sem substituir_nf a NF nova só soma
    arq2 = UploadFile(io.BytesIO(b"%PDF-1.4 outra"), filename="nf2.pdf", headers=Headers({"content-type": "application/pdf"}))
    await upload.upload_anexo(os_id, tipo="nf", posicao_pneu=None, substituir_nf=False, arquivo=arq2, user=admin_user, db=db)
    assert len((await _anexos_visiveis(db, os_id)).anexos) == 2


async def test_substituir_nf_em_os_encerrada_recusa_sem_deixar_arquivo(db, admin_user, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    os_ = await _os(db, admin_user, status="encerrada")
    arq = UploadFile(io.BytesIO(b"%PDF-1.4"), filename="nf.pdf", headers=Headers({"content-type": "application/pdf"}))
    with pytest.raises(HTTPException) as e:
        await upload.upload_anexo(os_.id, tipo="nf", posicao_pneu=None, substituir_nf=True, arquivo=arq, user=admin_user, db=db)
    assert e.value.status_code == 409 and not list(tmp_path.rglob("*.pdf"))
