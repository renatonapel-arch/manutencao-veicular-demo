"""Caixa Interno → OS (#0233): compra de manutenção de veículo vira OS aberta.

Cobre o contrato combinado com a sessão do Caixa (POST/DELETE com X-Sync-Secret,
idempotência por cupom, placa fora da Frota, cancelamento) e o botão "Conferido".
HTTP de verdade (ASGI) contra um app só com este router — sem service worker, sem
Frota, sem WhatsApp.
"""
import asyncio
import threading
import uuid
from decimal import Decimal

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import models
from app import service as svc
from app.config import settings
from app.database import get_db
from app.models import AnexosOs, AuditoriaOs, OrdemServico, OsItemLinha, User
from app.routers import integracao_caixa
from app.schemas import OrdemServicoOut

SEGREDO = "segredo-de-teste-caixa"
HEADERS = {"X-Sync-Secret": SEGREDO}


@pytest.fixture(autouse=True)
def segredo_e_sync(monkeypatch):
    monkeypatch.setattr(settings, "MANUTENCAO_CAIXA_SYNC_SECRET", SEGREDO)
    monkeypatch.setattr(integracao_caixa, "_ultimo_sync", None)
    chamadas, evento = [], threading.Event()

    def sync_falso():
        chamadas.append(1)
        evento.set()

    monkeypatch.setattr(integracao_caixa, "sync_veiculos_job", sync_falso)
    return chamadas, evento


@pytest.fixture
def sync_chamadas(segredo_e_sync):
    return segredo_e_sync


@pytest.fixture
async def http(db):
    app = FastAPI()
    app.include_router(integracao_caixa.router, prefix="/api")

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://caixa.test") as c:
        yield c


def _payload(**sobre):
    base = {
        "origem_cupom_id": 290,
        "origem_compra_id": 77,
        "kind": "fiscal",
        "placa": "TST1A23",
        "data": "2026-10-05",
        "descricao": "Lâmpada do farol — TST1A23",
        "funcionario_nome": "Crisleide",
        "valor_total": 45.9,
        "emitente": "Auto Peças Boa Vista",
        "emitente_cnpj": "12.345.678/0001-90",
        "doc_ref": "35261012345678000190550010000012341000012345",
        "itens": [{"descricao": "LAMPADA H4", "valor_total": 45.9}],
        "link_compra": "https://clavis.napel.com.br/financeiro/caixa-interno?compra=77",
    }
    base.update(sobre)
    return base


async def _os_do_cupom(db, cupom="290"):
    return (await db.execute(
        select(OrdemServico).where(OrdemServico.origem_ref == cupom).order_by(OrdemServico.id)
    )).scalars().all()


# ------------------------------------------------------------------ segredo

async def test_sem_segredo_ou_segredo_errado_401(http, veiculo, admin_user):
    assert (await http.post("/api/integracoes/caixa-interno", json=_payload())).status_code == 401
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(), headers={"X-Sync-Secret": "errado"})
    assert r.status_code == 401
    assert (await http.delete("/api/integracoes/caixa-interno/290")).status_code == 401


async def test_segredo_com_acento_nao_vira_500(http, veiculo, admin_user):
    # compare_digest com str não-ASCII levanta TypeError — aqui tem que ser 401
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(), headers={"X-Sync-Secret": "açaí".encode("latin-1")})
    assert r.status_code == 401


async def test_fechada_quando_o_segredo_nao_esta_configurado(http, veiculo, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "MANUTENCAO_CAIXA_SYNC_SECRET", "")
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(), headers={"X-Sync-Secret": ""})
    assert r.status_code == 401


# ------------------------------------------------------------------ criar

async def test_cria_os_aberta_com_um_item_e_origem(http, db, veiculo, admin_user):
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(), headers=HEADERS)
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["ok"] is True and corpo["duplicado"] is False and corpo["status"] == "aberta"
    assert corpo["link"].endswith(f"/patrimonio/manutencao?os={corpo['os_id']}")

    os_ = (await db.execute(select(OrdemServico).where(OrdemServico.id == corpo["os_id"]))).scalar_one()
    assert os_.status == "aberta" and os_.tipo_os == "corretiva_manual" and os_.categoria == "Outros"
    assert os_.veiculo_id == veiculo.id and os_.filial_id == veiculo.filial_id
    assert os_.km_veiculo == veiculo.km_atual
    assert os_.valor_total == Decimal("45.90")
    assert (os_.origem, os_.origem_ref) == ("caixa_interno", "290")
    assert os_.aberto_por_user_id == admin_user.id
    assert os_.data_abertura.date().isoformat() == "2026-10-05"
    assert "Lâmpada do farol" in os_.descricao_problema and "Crisleide" in os_.descricao_problema
    assert "05/10/2026" in os_.descricao_problema and "R$ 45,90" in os_.descricao_problema

    itens = (await db.execute(select(OsItemLinha).where(OsItemLinha.os_id == os_.id))).scalars().all()
    assert len(itens) == 1 and itens[0].subtotal == Decimal("45.90") and itens[0].quantidade == 1

    auditorias = (await db.execute(select(AuditoriaOs).where(AuditoriaOs.os_id == os_.id))).scalars().all()
    assert [a.operacao for a in auditorias] == ["criada-via-caixa-interno"]
    assert "Compra #77" in auditorias[0].motivo

    # a tela recebe os dados da origem pelo schema da OS
    visto = OrdemServicoOut.model_validate(os_)
    assert visto.origem == "caixa_interno" and visto.origem_dados["valor_total"] == "45.90"
    assert visto.origem_dados["link_compra"].startswith("https://")
    assert visto.origem_dados["itens"][0]["descricao"] == "LAMPADA H4"


async def test_sem_id_da_compra_a_auditoria_nao_escreve_none(http, db, veiculo, admin_user):
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(origem_compra_id=None), headers=HEADERS)
    assert r.status_code == 201
    os_ = (await _os_do_cupom(db))[0]
    motivo = (await db.execute(select(AuditoriaOs.motivo).where(AuditoriaOs.os_id == os_.id))).scalar_one()
    assert motivo == "Cupom #290 do Caixa Interno"
    # e o cancelamento também cai no id do cupom
    await http.delete("/api/integracoes/caixa-interno/290", headers=HEADERS)
    await db.refresh(os_)
    assert os_.motivo_reprovacao == "Caixa Interno: cupom #290 excluída/placa corrigida"


async def test_prefere_o_usuario_de_sistema_hudson(http, db, veiculo, admin_user):
    hudson = User(email="hudson@napel.local", role="usuario", filial_id=None, nome="Hudson", senha_hash="x", ativo=True)
    db.add(hudson)
    await db.commit()
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(), headers=HEADERS)
    assert r.status_code == 201
    os_ = (await _os_do_cupom(db))[0]
    assert os_.aberto_por_user_id == hudson.id


async def test_replay_do_mesmo_cupom_devolve_a_mesma_os(http, db, veiculo, admin_user):
    a = (await http.post("/api/integracoes/caixa-interno", json=_payload(), headers=HEADERS)).json()
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(), headers=HEADERS)
    assert r.status_code == 200
    b = r.json()
    assert b["os_id"] == a["os_id"] and b["duplicado"] is True and b["status"] == "aberta"
    assert len(await _os_do_cupom(db)) == 1


async def test_placa_com_hifen_e_minuscula_casa_com_o_cadastro(http, db, veiculo, admin_user):
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(placa=" tst-1a23 "), headers=HEADERS)
    assert r.status_code == 201


async def test_sem_nota_leva_o_motivo_no_texto(http, db, veiculo, admin_user):
    r = await http.post("/api/integracoes/caixa-interno", headers=HEADERS, json=_payload(
        kind="sem_nota", motivo="borracharia não emite nota", doc_ref=None, itens=None, emitente=None))
    assert r.status_code == 201
    os_ = (await _os_do_cupom(db))[0]
    assert "Sem nota fiscal — motivo: borracharia não emite nota." in os_.descricao_problema
    assert os_.origem_dados["kind"] == "sem_nota"


@pytest.mark.parametrize("mudanca", [
    {"kind": "erro"},                                   # cupom com erro nunca é enviado
    {"valor_total": 0},
    {"origem_cupom_id": 0},
    {"link_compra": "javascript:alert(1)"},             # vira href na tela: só https
    {"data": "05/10/2026"},
])
async def test_payload_invalido_422(http, veiculo, admin_user, mudanca):
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(**mudanca), headers=HEADERS)
    assert r.status_code == 422


@pytest.mark.parametrize("placa", ["   ", "ABCDEFGHIJK"])
async def test_placa_invalida_422(http, veiculo, admin_user, placa):
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(placa=placa), headers=HEADERS)
    assert r.status_code == 422 and r.json()["motivo"] == "placa_invalida"


# ------------------------------------------------------------------ placa fora da Frota

async def test_placa_desconhecida_404_e_sync_em_segundo_plano_uma_vez_so(http, db, veiculo, admin_user, sync_chamadas):
    chamadas, evento = sync_chamadas
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(placa="ZZZ9Z99"), headers=HEADERS)
    assert r.status_code == 404
    corpo = r.json()
    assert corpo["ok"] is False and corpo["motivo"] == "placa_desconhecida"
    assert "tente de novo" in corpo["detail"].lower()
    assert await asyncio.to_thread(evento.wait, 2), "o sync com a Frota não foi disparado"
    assert len(chamadas) == 1
    assert await _os_do_cupom(db) == []

    # outra placa nova logo depois: continua 404, mas não dispara um 2º sync (máx. 1 a cada 5 min)
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(placa="YYY8Y88", origem_cupom_id=291), headers=HEADERS)
    assert r.status_code == 404
    await asyncio.sleep(0.2)
    assert len(chamadas) == 1


# ------------------------------------------------------------------ corrigir placa / cancelar

async def test_delete_cancela_a_os_intocada_e_o_mesmo_cupom_gera_os_nova(http, db, veiculo, admin_user):
    a = (await http.post("/api/integracoes/caixa-interno", json=_payload(), headers=HEADERS)).json()

    r = await http.delete("/api/integracoes/caixa-interno/290", headers=HEADERS)
    assert r.status_code == 200 and r.json() == {"ok": True, "cancelada": True, "os_id": a["os_id"], "status": "cancelada"}
    antiga = (await _os_do_cupom(db))[0]
    assert antiga.status == "cancelada" and antiga.deleted_at is None  # fica no histórico, não some
    assert antiga.motivo_reprovacao == "Caixa Interno: compra #77 excluída/placa corrigida"
    ops = (await db.execute(select(AuditoriaOs.operacao).where(AuditoriaOs.os_id == antiga.id))).scalars().all()
    assert "cancelada-via-caixa-interno" in ops

    # "corrigir a placa": mesmo cupom, agora com OS cancelada → cria OS NOVA
    outro = models.VeiculoSnapshot(veiculo_patrimonial_id=2002, placa="NEW2B34", modelo="Outro", tipo="carro",
                                   filial_id=2, km_atual=500, ativo=True)
    db.add(outro)
    await db.commit()
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(placa="NEW2B34"), headers=HEADERS)
    assert r.status_code == 201 and r.json()["duplicado"] is False
    assert r.json()["os_id"] != a["os_id"]
    todas = await _os_do_cupom(db)
    assert [o.status for o in todas] == ["cancelada", "aberta"]
    assert todas[1].veiculo_id == outro.id and todas[1].filial_id == 2  # filial = a do veículo


@pytest.mark.parametrize("cupom", [999, 290])
async def test_delete_de_cupom_inexistente_ou_ja_cancelado_e_200(http, db, veiculo, admin_user, cupom):
    if cupom == 290:
        await http.post("/api/integracoes/caixa-interno", json=_payload(), headers=HEADERS)
        await http.delete("/api/integracoes/caixa-interno/290", headers=HEADERS)
    r = await http.delete(f"/api/integracoes/caixa-interno/{cupom}", headers=HEADERS)
    assert r.status_code == 200 and r.json() == {"ok": True, "cancelada": False}


async def _tocar(db, os_, como):
    if como == "triagem":
        os_.status = "em_triagem"
    elif como == "encerrada":
        os_.status = "encerrada"
    elif como == "anexo":
        db.add(AnexosOs(os_id=os_.id, tipo="foto_problema", arquivo_url="/uploads/x.jpg", uploaded_by=1))
    elif como == "item_extra":
        db.add(OsItemLinha(os_id=os_.id, tipo_item="servico", descricao="mão de obra",
                           quantidade=1, valor_unitario=Decimal("30"), subtotal=Decimal("30")))
    elif como == "item_trocado":
        item = (await db.execute(select(OsItemLinha).where(OsItemLinha.os_id == os_.id))).scalar_one()
        item.valor_unitario = item.subtotal = Decimal("99.90")
    elif como == "editada":  # todo PATCH grava auditoria
        db.add(AuditoriaOs(os_id=os_.id, operacao="UPDATE", user_id=1))
    elif como == "oficina":
        oficina = models.OficinaPadronizada(nome="Borracharia do Zé")
        db.add(oficina)
        await db.flush()
        os_.oficina_id = oficina.id
    await db.commit()


@pytest.mark.parametrize("como", ["triagem", "encerrada", "anexo", "item_extra", "item_trocado", "editada", "oficina"])
async def test_delete_recusa_com_409_quando_a_os_ja_foi_trabalhada(http, db, veiculo, admin_user, como):
    a = (await http.post("/api/integracoes/caixa-interno", json=_payload(), headers=HEADERS)).json()
    os_ = (await _os_do_cupom(db))[0]
    await _tocar(db, os_, como)
    estado = os_.status

    r = await http.delete("/api/integracoes/caixa-interno/290", headers=HEADERS)
    assert r.status_code == 409
    corpo = r.json()
    assert corpo["ok"] is False and corpo["motivo"] == "os_em_andamento"
    assert corpo["os_id"] == a["os_id"] and corpo["status"] == estado
    await db.refresh(os_)
    assert os_.status == estado  # nada foi cancelado


async def test_mesmo_cupom_com_outra_placa_enquanto_a_os_esta_ativa_e_409(http, db, veiculo, admin_user):
    db.add(models.VeiculoSnapshot(veiculo_patrimonial_id=2002, placa="NEW2B34", modelo="Outro", tipo="carro",
                                  filial_id=2, km_atual=500, ativo=True))
    await db.commit()
    a = (await http.post("/api/integracoes/caixa-interno", json=_payload(), headers=HEADERS)).json()
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(placa="NEW2B34"), headers=HEADERS)
    assert r.status_code == 409
    corpo = r.json()
    assert corpo["motivo"] == "placa_divergente" and corpo["os_id"] == a["os_id"]
    assert "TST1A23" in corpo["detail"]
    assert len(await _os_do_cupom(db)) == 1


# ------------------------------------------------------------------ índice único / corrida

async def test_indice_unico_so_vale_entre_os_ativas(db, veiculo, admin_user):
    # ids em variáveis: o rollback expira os objetos e reler atributo fora do greenlet quebra
    veiculo_id, filial_id, user_id = veiculo.id, veiculo.filial_id, admin_user.id

    def nova():
        return OrdemServico(
            request_id=uuid.uuid4(), veiculo_id=veiculo_id, filial_id=filial_id,
            aberto_por_user_id=user_id, tipo_os="corretiva_manual", km_veiculo=1,
            status="aberta", origem="caixa_interno", origem_ref="500",
        )

    primeira = nova()
    db.add(primeira)
    await db.commit()
    primeira_id = primeira.id

    db.add(nova())
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()

    primeira = await db.get(OrdemServico, primeira_id)
    primeira.status = "cancelada"          # cancelada libera a chave
    await db.commit()
    db.add(nova())
    await db.commit()                      # agora pode

    # OS sem origem não entra na regra (várias com origem NULL)
    for _ in range(2):
        os_ = nova()
        os_.origem = os_.origem_ref = None
        db.add(os_)
    await db.commit()


async def test_dois_posts_ao_mesmo_tempo_nao_criam_duas_os(http, db, veiculo, admin_user, monkeypatch):
    """A corrida: o 2º POST passa pela checagem de duplicado antes de o 1º gravar e é barrado
    pelo índice único — tem que devolver a OS do 1º (200 duplicado), não 500."""
    await http.post("/api/integracoes/caixa-interno", json=_payload(), headers=HEADERS)

    real = integracao_caixa._os_ativa
    chamadas = {"n": 0}

    async def _cega_na_primeira(db_, ref):
        chamadas["n"] += 1
        return None if chamadas["n"] == 1 else await real(db_, ref)

    monkeypatch.setattr(integracao_caixa, "_os_ativa", _cega_na_primeira)
    r = await http.post("/api/integracoes/caixa-interno", json=_payload(), headers=HEADERS)
    assert r.status_code == 200 and r.json()["duplicado"] is True
    assert len(await _os_do_cupom(db)) == 1


# ------------------------------------------------------------------ "Conferido" (gestor)

async def _os_caixa(db, veiculo, admin, status="aberta", origem="caixa_interno"):
    os_ = OrdemServico(
        request_id=uuid.uuid4(), veiculo_id=veiculo.id, filial_id=veiculo.filial_id,
        aberto_por_user_id=admin.id, tipo_os="corretiva_manual", km_veiculo=1000, status=status,
        valor_total=Decimal("45.90"), origem=origem, origem_ref="290" if origem else None,
    )
    db.add(os_)
    await db.commit()
    await db.refresh(os_)
    return os_


async def test_gestor_confere_e_encerra_sem_foto_nf_nem_item(db, veiculo, admin_user, monkeypatch):
    avisos = []

    async def _aviso(*a, **k):
        avisos.append(a)

    monkeypatch.setattr(svc, "notify_os_transition", _aviso)
    os_ = await _os_caixa(db, veiculo, admin_user)
    r = await svc.conferir_os_externa(db, os_.id, admin_user)
    assert r.status == "encerrada" and r.data_encerramento is not None
    assert r.valor_total == Decimal("45.90")           # custo real: NÃO zera (diferente da garantia)
    assert r.encerrada_em_garantia is False
    ops = (await db.execute(select(AuditoriaOs.operacao).where(AuditoriaOs.os_id == os_.id))).scalars().all()
    assert ops == ["conferida:aberta→encerrada"]
    assert avisos == []                                 # conferir não manda WhatsApp


@pytest.mark.parametrize("de", ["aberta", "em_triagem", "aguardando_orcamento", "em_execucao", "aguardando_peca"])
async def test_confere_de_qualquer_estado_ativo(db, veiculo, admin_user, de):
    os_ = await _os_caixa(db, veiculo, admin_user, status=de)
    assert (await svc.conferir_os_externa(db, os_.id, admin_user)).status == "encerrada"


async def test_responsavel_de_filial_tambem_confere(db, veiculo, admin_user, responsavel_user):
    os_ = await _os_caixa(db, veiculo, admin_user)   # filial 1 = a do responsavel_user
    assert (await svc.conferir_os_externa(db, os_.id, responsavel_user)).status == "encerrada"


async def test_nao_gestor_nao_confere(db, veiculo, admin_user, motorista_user):
    os_ = await _os_caixa(db, veiculo, admin_user)
    with pytest.raises(Exception) as e:
        await svc.conferir_os_externa(db, os_.id, motorista_user)
    assert getattr(e.value, "status_code", None) == 403


async def test_so_confere_os_que_veio_de_outro_modulo(db, veiculo, admin_user):
    os_ = await _os_caixa(db, veiculo, admin_user, origem=None)
    with pytest.raises(Exception) as e:
        await svc.conferir_os_externa(db, os_.id, admin_user)
    assert getattr(e.value, "status_code", None) == 400


@pytest.mark.parametrize("estado", ["encerrada", "cancelada"])
async def test_os_finalizada_nao_confere(db, veiculo, admin_user, estado):
    os_ = await _os_caixa(db, veiculo, admin_user, status=estado)
    with pytest.raises(Exception) as e:
        await svc.conferir_os_externa(db, os_.id, admin_user)
    assert getattr(e.value, "status_code", None) == 400


async def test_conferir_os_inexistente_404(db, admin_user):
    with pytest.raises(Exception) as e:
        await svc.conferir_os_externa(db, 9999, admin_user)
    assert getattr(e.value, "status_code", None) == 404
