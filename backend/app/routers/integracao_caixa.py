"""Integração Caixa Interno → Manutenção Veicular (#0233).

Compra de manutenção de veículo registrada no Caixa Interno (lâmpada, pneu
furado...) vira uma OS ABERTA aqui, para o gestor conferir, dar continuidade
ou cancelar — sem isso o custo some do controle da frota. Troca de óleo fica
FORA (card próprio do Raul / app troca-óleo): o Caixa não envia.

Auth: X-Sync-Secret (mesmo padrão system-to-system do RH Jornada e do
troca-óleo) — quem chama é outro serviço, não uma pessoa logada.

Contrato (alinhado com a sessão do Caixa Interno em 05/10/2026):
  POST   /api/integracoes/caixa-interno                    cria — ou devolve — a OS do cupom
  DELETE /api/integracoes/caixa-interno/{origem_cupom_id}  cancela a OS se ainda intocada

Regras que o Caixa conta com elas:
  - Idempotência pelo cupom: repetir o POST devolve a MESMA OS (`duplicado: true`).
    Só vale enquanto existir OS não cancelada; se a única OS do cupom foi cancelada,
    o novo POST cria uma OS NOVA (é assim que "corrigir a placa" funciona).
  - Só consulta o banco daqui (nunca a Frota) — o Caixa espera a resposta no upload.
  - Placa fora do cadastro → 404 `placa_desconhecida` e um sync com a Frota roda em
    segundo plano (veículo recém-comprado); tentar de novo em ~1 min resolve.
  - SEM notify_os_transition: a OS nasce sem aviso de WhatsApp (evita enxurrada).
"""
from __future__ import annotations

import asyncio
import hmac
import logging
import time
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..database import get_db
from ..jobs.sync_veiculos import sync_veiculos_job
from ..models import AuditoriaOs, OrdemServico, OsItemLinha, User, VeiculoSnapshot

log = logging.getLogger("manutencao.integracao_caixa")

ORIGEM = "caixa_interno"

# Mesmo usuário "de sistema" do RH Jornada: precisa de um FK válido em aberto_por.
_SYSTEM_USER_EMAIL = "hudson@napel.local"

# Sync sob demanda com a Frota: no máx. 1 a cada 5 min (o snapshot já atualiza de hora em hora).
_SYNC_INTERVALO_S = 300
_ultimo_sync: Optional[float] = None


def require_secret(x_sync_secret: str = Header(default="", alias="X-Sync-Secret")):
    segredo = settings.MANUTENCAO_CAIXA_SYNC_SECRET
    # bytes: compare_digest com str não-ASCII levanta TypeError (viraria 500)
    if not segredo or not hmac.compare_digest((x_sync_secret or "").encode(), segredo.encode()):
        raise HTTPException(status_code=401, detail="X-Sync-Secret inválido")


router = APIRouter(
    prefix="/integracoes/caixa-interno", tags=["integracao-caixa"],
    dependencies=[Depends(require_secret)],
)


class CompraCaixaIn(BaseModel):
    origem_cupom_id: int = Field(gt=0, description="Chave de idempotência (cupom do Caixa)")
    origem_compra_id: Optional[int] = None
    kind: Literal["fiscal", "sem_nota"]  # cupom com erro nunca é enviado
    placa: str
    data: date  # dia da compra no Caixa (não a data do OCR)
    descricao: str = Field(min_length=1, description="Finalidade escrita pela operadora")
    funcionario_nome: Optional[str] = None
    valor_total: Decimal = Field(gt=0, le=1_000_000)
    emitente: Optional[str] = None
    emitente_cnpj: Optional[str] = None
    doc_ref: Optional[str] = None  # chave de acesso da NF-e
    itens: Optional[list[dict]] = Field(default=None, max_length=500)  # só informativo (OCR)
    motivo: Optional[str] = None  # sem_nota: por que não tem nota
    # vira href na tela: só https (nada de javascript:)
    link_compra: Optional[str] = Field(default=None, pattern=r"^https://")


def _erro(codigo_http: int, motivo: str, detail: str, /, **extra) -> JSONResponse:
    # posicionais-apenas: `status` (da OS) vai em **extra e não pode colidir com o código HTTP
    return JSONResponse(status_code=codigo_http, content={"ok": False, "motivo": motivo, "detail": detail, **extra})


def _normalizar_placa(placa: str) -> str:
    return (placa or "").strip().upper().replace("-", "").replace(" ", "")


def _link(os_id: int) -> str:
    # O embed do Clavis ainda ignora ?os= (abre o módulo na home); o parâmetro já
    # fica no link para virar atalho direto assim que o Clavis passar a repassá-lo.
    return f"{settings.CLAVIS_PUBLIC_URL.rstrip('/')}/patrimonio/manutencao?os={os_id}"


def _brl(v: Decimal) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _texto_os(p: CompraCaixaIn, valor: Decimal) -> str:
    quem = f"{p.funcionario_nome} comprou" if p.funcionario_nome else "Comprado"
    onde = f" ({p.emitente})" if p.emitente else ""
    texto = (f"Compra no Caixa Interno: {p.descricao.strip()}. "
             f"{quem} em {p.data.strftime('%d/%m/%Y')}{onde} por {_brl(valor)}.")
    if p.kind == "sem_nota":
        texto += f" Sem nota fiscal — motivo: {p.motivo}." if p.motivo else " Sem nota fiscal."
    return texto


def disparar_sync_frota() -> Optional[asyncio.Future]:
    """Veículo recém-comprado ainda não está no snapshot da Frota: pede um sync agora,
    em segundo plano (a resposta ao Caixa não espera). Devolve None se já rodou há pouco."""
    global _ultimo_sync
    agora = time.monotonic()
    if _ultimo_sync is not None and agora - _ultimo_sync < _SYNC_INTERVALO_S:
        return None
    _ultimo_sync = agora
    return asyncio.get_running_loop().run_in_executor(None, sync_veiculos_job)


async def _os_ativa(db: AsyncSession, origem_ref: str) -> Optional[OrdemServico]:
    """A OS NÃO cancelada do cupom (no máx. 1 — garantido pelo índice único parcial)."""
    return (await db.execute(
        select(OrdemServico)
        .options(selectinload(OrdemServico.veiculo), selectinload(OrdemServico.itens),
                 selectinload(OrdemServico.anexos))
        .where(
            OrdemServico.origem == ORIGEM,
            OrdemServico.origem_ref == origem_ref,
            OrdemServico.deleted_at.is_(None),
            OrdemServico.status != "cancelada",
        )
    )).scalar_one_or_none()


def _resposta_duplicado(os_: OrdemServico) -> JSONResponse:
    return JSONResponse(status_code=200, content={
        "ok": True, "os_id": os_.id, "status": os_.status, "link": _link(os_.id), "duplicado": True,
    })


def _resumo_validacao(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())[:400]


@router.post("", status_code=201)
async def receber_compra(request: Request, db: AsyncSession = Depends(get_db)):
    # Valida aqui (e não pelo parâmetro tipado) para que TODO erro saia no formato do
    # contrato — {ok, motivo, detail: texto}: o Caixa mostra o `detail` à operadora, e o
    # 422 padrão do FastAPI traria `detail` como lista.
    try:
        payload = CompraCaixaIn.model_validate(await request.json())
    except ValidationError as exc:
        return _erro(422, "payload_invalido", _resumo_validacao(exc))
    except ValueError:  # corpo que não é JSON
        return _erro(422, "payload_invalido", "O corpo da requisição não é um JSON válido")
    placa = _normalizar_placa(payload.placa)
    if not placa or len(placa) > 10:
        return _erro(422, "placa_invalida", f"Placa '{payload.placa}' inválida")
    chave = str(payload.origem_cupom_id)

    # --- 1. Idempotência: já existe OS ativa deste cupom? ---
    existente = await _os_ativa(db, chave)
    if existente:
        if existente.veiculo and existente.veiculo.placa != placa:
            # Corrigir a placa = DELETE (cancela) e só então POST de novo. Devolver a OS
            # antiga como se fosse da placa nova ligaria o custo ao veículo errado.
            return _erro(
                409, "placa_divergente",
                f"A OS #{existente.id} deste cupom é do veículo {existente.veiculo.placa}. "
                f"Para trocar a placa, cancele-a (DELETE) antes.",
                os_id=existente.id, status=existente.status,
            )
        return _resposta_duplicado(existente)

    # --- 2. Veículo pela placa (só o banco daqui) ---
    veic = (await db.execute(
        select(VeiculoSnapshot).where(VeiculoSnapshot.placa == placa)
    )).scalar_one_or_none()
    if not veic:
        disparar_sync_frota()
        return _erro(
            404, "placa_desconhecida",
            f"Placa '{placa}' não está no cadastro de veículos (Frota). "
            f"Se o veículo é novo, tente de novo em ~1 min.",
        )

    # --- 3. User "aberto_por": FK válido (mesmo critério do RH Jornada) ---
    user = (await db.execute(select(User).where(User.email == _SYSTEM_USER_EMAIL))).scalar_one_or_none()
    if not user:
        user = (await db.execute(select(User).where(User.role == "admin").limit(1))).scalar_one_or_none()
    if not user:
        raise HTTPException(500, "Nenhum usuário admin cadastrado — não é possível atribuir a OS")

    # --- 4. Cria a OS ABERTA, com 1 item = total do cupom (itens do OCR só ficam na origem) ---
    valor = payload.valor_total.quantize(Decimal("0.01"))
    # meio-dia UTC: em Brasília (UTC-3) continua no mesmo dia; meia-noite UTC cairia na véspera
    abertura = datetime(payload.data.year, payload.data.month, payload.data.day, 12, tzinfo=timezone.utc)
    os_ = OrdemServico(
        request_id=uuid.uuid4(),
        veiculo_id=veic.id,
        filial_id=veic.filial_id,
        aberto_por_user_id=user.id,
        tipo_os="corretiva_manual",
        tipo_destino="oficina_terceirizada",
        km_veiculo=veic.km_atual,
        km_api_snapshot=veic.km_atual,
        descricao_problema=_texto_os(payload, valor)[:2000],
        categoria="Outros",
        status="aberta",
        data_abertura=abertura,
        valor_total=valor,
        desconto_ajuste=Decimal("0"),
        economia_napel_total=Decimal("0"),
        origem=ORIGEM,
        origem_ref=chave,
        origem_dados={
            "cupom_id": payload.origem_cupom_id,
            "compra_id": payload.origem_compra_id,
            "kind": payload.kind,
            "data": payload.data.isoformat(),
            "descricao": payload.descricao.strip(),
            "funcionario_nome": payload.funcionario_nome,
            "emitente": payload.emitente,
            "emitente_cnpj": payload.emitente_cnpj,
            "doc_ref": payload.doc_ref,
            "valor_total": str(valor),
            "motivo": payload.motivo,
            "link_compra": payload.link_compra,
            "itens": payload.itens,
        },
    )
    db.add(os_)
    try:
        await db.flush()
    except IntegrityError:
        # Dois POSTs do mesmo cupom ao mesmo tempo: o índice único barrou o segundo.
        await db.rollback()
        concorrente = await _os_ativa(db, chave)
        if concorrente:
            return _resposta_duplicado(concorrente)
        raise

    db.add(OsItemLinha(
        os_id=os_.id, tipo_item="peca",
        descricao=f"Compra Caixa Interno: {payload.descricao.strip()}"[:200],
        quantidade=Decimal("1"), valor_unitario=valor, subtotal=valor, garantia_dias=0,
    ))
    db.add(AuditoriaOs(
        os_id=os_.id, operacao="criada-via-caixa-interno",
        user_id=user.id, filial_id=veic.filial_id,
        after_data={"origem": ORIGEM, "origem_ref": chave, "placa": placa, "valor_total": str(valor)},
        motivo=(f"Compra #{payload.origem_compra_id} do Caixa Interno (cupom #{payload.origem_cupom_id})"
                if payload.origem_compra_id else f"Cupom #{payload.origem_cupom_id} do Caixa Interno"),
    ))
    await db.commit()
    await db.refresh(os_)

    log.info("OS #%s criada via Caixa Interno · cupom=%s · placa=%s · valor=%s",
             os_.id, chave, placa, valor)
    return {"ok": True, "os_id": os_.id, "status": os_.status, "link": _link(os_.id), "duplicado": False}


async def _intocada(db: AsyncSession, os_: OrdemServico) -> bool:
    """Ainda do jeito que o Caixa criou: aberta, sem anexo, sem oficina, só o item original
    e nenhuma edição (todo PATCH grava auditoria; transição de status também)."""
    if os_.status != "aberta" or os_.oficina_id is not None or os_.anexos:
        return False
    valor_original = (os_.origem_dados or {}).get("valor_total")
    if len(os_.itens) != 1 or valor_original is None or os_.itens[0].subtotal != Decimal(valor_original):
        return False
    n_auditorias = (await db.execute(
        select(func.count()).select_from(AuditoriaOs).where(AuditoriaOs.os_id == os_.id)
    )).scalar_one()
    return n_auditorias == 1


@router.delete("/{origem_cupom_id}")
async def cancelar_por_cupom(origem_cupom_id: int, db: AsyncSession = Depends(get_db)):
    """Compra excluída (ou placa corrigida) no Caixa: cancela a OS de verdade — fica no
    histórico como "Cancelada" com o motivo, não some. Se a OS já foi trabalhada pelo
    gestor, recusa (409): o Caixa bloqueia a exclusão até alguém cancelar a OS aqui."""
    os_ = await _os_ativa(db, str(origem_cupom_id))
    if os_ is None:
        return {"ok": True, "cancelada": False}  # não existia, ou já estava cancelada
    if not await _intocada(db, os_):
        return _erro(
            409, "os_em_andamento",
            f"A OS #{os_.id} já foi trabalhada (status: {os_.status}). Cancele-a na Manutenção primeiro.",
            os_id=os_.id, status=os_.status,
        )
    compra_id = (os_.origem_dados or {}).get("compra_id")
    ref = f"compra #{compra_id}" if compra_id else f"cupom #{origem_cupom_id}"
    motivo = f"Caixa Interno: {ref} excluída/placa corrigida"
    os_.status = "cancelada"
    os_.motivo_reprovacao = motivo
    db.add(AuditoriaOs(
        os_id=os_.id, operacao="cancelada-via-caixa-interno",
        filial_id=os_.filial_id, motivo=motivo,
    ))
    await db.commit()
    log.info("OS #%s cancelada via Caixa Interno · cupom=%s", os_.id, origem_cupom_id)
    return {"ok": True, "cancelada": True, "os_id": os_.id, "status": "cancelada"}
