"""Integração RH Jornada → Manutenção Veicular.

O módulo RH - Jornada do Colaborador (rh-jornada.demos.napel.com.br) substitui
o pipe Pipefy "RH - Solicitações e Autorizações". Quando o RH autoriza uma
solicitação marcada como "manutenção de veículo", ele chama este endpoint
pra criar a OS automaticamente — equivalente ao conector "Criar Card
Manutenção" que existia no Pipefy.

Auth: X-Sync-Secret (mesmo padrão system-to-system usado por troca-óleo e
frota) — não é JWT de usuário porque quem chama é outro serviço, não uma
pessoa logada.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..integrations.evolution_whatsapp import notify_os_transition
from ..models import AnexosOs, AuditoriaOs, OrdemServico, User, VeiculoSnapshot

log = logging.getLogger("manutencao.integracao_rh")

RH_SECRET = os.environ.get("RH_JORNADA_SYNC_SECRET", "")

# Users "de sistema" pra atribuir como aberto_por quando a chamada vem de
# integração automatizada (sem usuário Clavis logado no momento da criação).
# Se não achar, usa o primeiro admin ativo (fallback nunca falha por causa disso).
_SYSTEM_USER_EMAIL_FALLBACK = "hudson@napel.local"

FILIAL_CODIGO_PARA_ID = {100: 1, 700: 2, 900: 3}


def require_secret(x_sync_secret: str = Header(default="", alias="X-Sync-Secret")):
    if not RH_SECRET or not hmac_compare(x_sync_secret, RH_SECRET):
        raise HTTPException(status_code=401, detail="X-Sync-Secret inválido")


def hmac_compare(a: str, b: str) -> bool:
    import hmac
    return hmac.compare_digest(a or "", b or "")


router = APIRouter(
    prefix="/integracoes/rh-jornada", tags=["integracao-rh"],
    dependencies=[Depends(require_secret)],
)


class RHSolicitacaoIn(BaseModel):
    veiculo_placa: str = Field(..., description="Placa do veículo (obrigatório — toda OS precisa de 1 veículo)")
    nome_solicitante: str
    filial_codigo: int = Field(..., description="100, 700 ou 900")
    titulo: str
    descricao: Optional[str] = None
    anexo_url: Optional[str] = None
    autorizado_por: str
    data_autorizacao: Optional[datetime] = None
    request_id: Optional[str] = None  # idempotência — se ausente, gera um


class RHSolicitacaoOut(BaseModel):
    ok: bool
    os_id: int
    status: str
    link: str


@router.post("", response_model=RHSolicitacaoOut, status_code=201)
async def criar_os_via_rh(
    payload: RHSolicitacaoIn,
    db: AsyncSession = Depends(get_db),
):
    # --- 1. Resolve veículo pela placa ---
    placa_norm = payload.veiculo_placa.strip().upper().replace("-", "").replace(" ", "")
    veic = (await db.execute(
        select(VeiculoSnapshot).where(VeiculoSnapshot.placa == placa_norm)
    )).scalar_one_or_none()
    if not veic:
        raise HTTPException(
            404,
            f"Veículo com placa '{payload.veiculo_placa}' não encontrado no "
            f"Cadastro Veicular. Confirme a placa antes de reenviar.",
        )

    # --- 2. Idempotência ---
    req_id = payload.request_id or f"rh-jornada:{placa_norm}:{payload.titulo}:{payload.autorizado_por}"
    existente = (await db.execute(
        select(OrdemServico).where(OrdemServico.descricao_itens_original == req_id)
    )).scalar_one_or_none()
    if existente:
        return RHSolicitacaoOut(
            ok=True, os_id=existente.id, status=existente.status,
            link=f"https://manutencao.demos.napel.com.br/os/{existente.id}",
        )

    # --- 3. User "aberto_por" — precisa de um FK válido. Usa o primeiro admin. ---
    user = (await db.execute(
        select(User).where(User.email == _SYSTEM_USER_EMAIL_FALLBACK)
    )).scalar_one_or_none()
    if not user:
        user = (await db.execute(select(User).where(User.role == "admin").limit(1))).scalar_one_or_none()
    if not user:
        raise HTTPException(500, "Nenhum usuário admin cadastrado — não é possível atribuir a OS")

    filial_id = FILIAL_CODIGO_PARA_ID.get(payload.filial_codigo, veic.filial_id)

    # --- 4. Cria a OS já "aberta" (autorização do RH já é uma decisão formal) ---
    descricao = f"[RH] {payload.titulo}"
    if payload.descricao:
        descricao += f" — {payload.descricao}"
    descricao += f" · Solicitante: {payload.nome_solicitante} · Autorizado por: {payload.autorizado_por}"

    os_ = OrdemServico(
        request_id=uuid.uuid4(),
        veiculo_id=veic.id,
        filial_id=filial_id,
        aberto_por_user_id=user.id,
        tipo_os="corretiva_manual",
        tipo_destino="oficina_terceirizada",
        km_veiculo=veic.km_atual,
        descricao_problema=descricao,
        descricao_itens_original=req_id,  # usado só pra idempotência (ver acima)
        categoria="Outros",
        status="aberta",
        data_abertura=payload.data_autorizacao or datetime.utcnow(),
        valor_total=Decimal("0"),
        desconto_ajuste=Decimal("0"),
        economia_napel_total=Decimal("0"),
    )
    db.add(os_)
    await db.flush()

    db.add(AuditoriaOs(
        os_id=os_.id, operacao="criada-via-rh-jornada",
        user_id=user.id, filial_id=filial_id,
        motivo=f"Autorizado por {payload.autorizado_por} via RH Jornada",
    ))

    # --- 5. Anexo opcional (link direto, sem upload) ---
    if payload.anexo_url:
        db.add(AnexosOs(
            os_id=os_.id, tipo="foto_problema",
            arquivo_url=payload.anexo_url,
            uploaded_by=user.id,
            filename_original="anexo-rh-jornada",
        ))

    await db.commit()
    await db.refresh(os_)

    try:
        await notify_os_transition(db, os_, "aberta")
    except Exception as exc:
        log.warning("notify falhou (criar-via-rh): %s", exc)

    log.info(
        "OS #%s criada via RH Jornada · veiculo=%s · solicitante=%s · autorizado_por=%s",
        os_.id, placa_norm, payload.nome_solicitante, payload.autorizado_por,
    )

    return RHSolicitacaoOut(
        ok=True, os_id=os_.id, status=os_.status,
        link=f"https://manutencao.demos.napel.com.br/os/{os_.id}",
    )
