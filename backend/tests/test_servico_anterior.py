"""#0272: OS mostra a última vez do mesmo serviço no veículo + categoria obrigatória + preenchimento."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.models import AuditoriaOs, OrdemServico, VeiculoSnapshot
from app.routers import admin, ordem_servico
from app.schemas import OrdemServicoCreate

AGORA = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)


async def _veiculo(db, vid=1, placa="BEE2A87"):
    db.add(VeiculoSnapshot(id=vid, veiculo_patrimonial_id=vid, placa=placa, modelo="M", tipo="moto",
                           km_atual=1, filial_id=1, ativo=True))
    await db.flush()


async def _os(db, admin, dias_atras, km, categoria="Pastilha / Lona", status="encerrada", vid=1, desc="lona"):
    o = OrdemServico(request_id=uuid.uuid4(), veiculo_id=vid, filial_id=1, aberto_por_user_id=admin.id,
                     tipo_os="corretiva_manual", km_veiculo=km, status=status, categoria=categoria,
                     descricao_problema=desc, data_abertura=AGORA - timedelta(days=dias_atras))
    db.add(o)
    await db.commit()
    return o.id


async def test_ultimas_3_mesma_categoria_sem_canceladas_nem_a_propria(db, admin_user):
    await _veiculo(db)
    await _veiculo(db, 2, "OUT1A11")
    ids = [await _os(db, admin_user, d, km) for d, km in ((400, 10000), (200, 15000), (100, 18000), (50, 19000))]
    await _os(db, admin_user, 30, 19500, status="cancelada")       # cancelada não conta
    await _os(db, admin_user, 20, 19600, categoria="Pneu")         # outra categoria
    await _os(db, admin_user, 10, 19700, vid=2)                    # outro veículo
    await _os(db, admin_user, -5, 21000)                           # aberta DEPOIS desta
    atual = await _os(db, admin_user, 0, 20000, status="aberta")
    d = await ordem_servico.get_os(atual, user=admin_user, db=db)
    assert [s.id for s in d.servico_anterior] == [ids[3], ids[2], ids[1]]
    ult = d.servico_anterior[0]
    assert ult.dias_antes == 50 and ult.km_antes == 1000 and ult.km_veiculo == 19000


async def test_sem_registro_e_outros_nao_compara(db, admin_user):
    await _veiculo(db)
    sozinha = await _os(db, admin_user, 0, 5000, status="aberta")
    assert (await ordem_servico.get_os(sozinha, user=admin_user, db=db)).servico_anterior == []
    await _os(db, admin_user, 100, 4000, categoria="Outros")
    outros = await _os(db, admin_user, 0, 5000, categoria="Outros", status="aberta")
    assert (await ordem_servico.get_os(outros, user=admin_user, db=db)).servico_anterior == []


async def test_km_que_nao_ajuda_vira_none(db, admin_user):
    await _veiculo(db)
    await _os(db, admin_user, 100, 30000)  # km maior que o atual (troca de painel, digitação)
    atual = await _os(db, admin_user, 0, 20000, status="aberta")
    assert (await ordem_servico.get_os(atual, user=admin_user, db=db)).servico_anterior[0].km_antes is None


def test_categoria_obrigatoria_ao_abrir():
    base = dict(request_id=uuid.uuid4(), veiculo_id=1, tipo_os="corretiva_manual", km_veiculo=10)
    with pytest.raises(ValidationError):
        OrdemServicoCreate(**base)
    assert OrdemServicoCreate(**base, categoria="Pneu").categoria == "Pneu"


@pytest.mark.parametrize("texto,cat", [
    ("Troca de lona de freio traseiro", "Pastilha / Lona"),
    ("pneu traseiro furado", "Pneu"),
    ("Trocar Kit relação", "Relação"),
    ("Trocar cabo de empreagem", "Embreagem"),
    ("Luz de ré queimada", "Lâmpadas"),
    ("Trocar junta da tampa de valvula", "Motor"),
    ("Protetor solto na rodovia", "Outros"),       # "rodovia" não é roda/pneu
    ("motorista relatou barulho no baú", "Outros"),  # "motorista" não é motor
])
def test_palavras_chave(texto, cat):
    assert admin._sugerir_categoria(texto)[0] == cat


async def test_preencher_so_vazias_registra_e_desfaz(db, admin_user):
    await _veiculo(db)
    vazia = await _os(db, admin_user, 10, 100, categoria=None, desc="pneu furado")
    cheia = await _os(db, admin_user, 10, 100, categoria="Motor", desc="pneu furado")
    previa = await admin.preencher_categorias("previa", user=admin_user, db=db)
    assert [o["os_id"] for o in previa["os"]] == [vazia]
    assert (await db.get(OrdemServico, vazia)).categoria is None  # prévia não grava

    await admin.preencher_categorias("aplicar", user=admin_user, db=db)
    cats = dict((await db.execute(select(OrdemServico.id, OrdemServico.categoria)
                                  .execution_options(populate_existing=True))).all())
    assert cats == {vazia: "Pneu", cheia: "Motor"}
    aud = (await db.execute(select(AuditoriaOs).where(AuditoriaOs.operacao == "categoria:preenchida_auto"))).scalar_one()
    assert aud.os_id == vazia and aud.after_data == {"categoria": "Pneu"}

    r = await admin.preencher_categorias("desfazer", user=admin_user, db=db)
    assert r["desfeitas"] == [vazia]
    cats = dict((await db.execute(select(OrdemServico.id, OrdemServico.categoria)
                                  .execution_options(populate_existing=True))).all())
    assert cats == {vazia: None, cheia: "Motor"}
