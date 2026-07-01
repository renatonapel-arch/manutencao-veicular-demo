"""Service do módulo Manutenção Veicular — regras de negócio + máquina de estados.

Padrão: 100% async (AsyncSession), transições validadas server-side,
soft-delete via helper `_ativas`, auto-aprovação abaixo do teto configurável.
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .dependencies import get_membro
from .models import (
    AuditoriaOs, MembroManutencao, OrdemServico, OsItemLinha, User,
)

log = logging.getLogger("manutencao.service")


# ============================================================
# Máquina de estados (9 estados)
# ============================================================

TRANSICOES_VALIDAS: dict[str, set[str]] = {
    "rascunho":              {"aberta", "cancelada"},
    "aberta":                {"em_triagem", "cancelada"},
    "em_triagem":            {"aguardando_orcamento", "cancelada"},
    "aguardando_orcamento":  {"aguardando_aprovacao", "cancelada"},
    "aguardando_aprovacao":  {"em_execucao", "aguardando_orcamento", "cancelada"},
    "em_execucao":           {"aguardando_peca", "encerrada", "cancelada"},
    "aguardando_peca":       {"em_execucao", "cancelada"},
    "encerrada":             set(),
    "cancelada":             set(),
}

TETO_AUTOAPROVACAO_DEFAULT = Decimal("500.00")


# ============================================================
# Helpers
# ============================================================

def _ativas(stmt, model):
    """Filtro global soft-delete. Aplicar em toda query."""
    return stmt.where(model.deleted_at.is_(None))


async def _auditar(
    db: AsyncSession, os_id: int, user: User,
    operacao: str, motivo: Optional[str] = None,
    before: Optional[dict] = None, after: Optional[dict] = None,
    filial_id: Optional[int] = None,
) -> None:
    db.add(AuditoriaOs(
        os_id=os_id, operacao=operacao,
        user_id=user.id if user else None,
        filial_id=filial_id,
        before_data=before, after_data=after,
        motivo=motivo,
    ))


async def _get_config(db: AsyncSession, chave: str, default: Any) -> Any:
    """Placeholder — quando houver tabela de config, buscar aqui."""
    return default


async def autorizar_transicao(
    db: AsyncSession, user: User, os: OrdemServico, novo_status: str,
) -> None:
    """RBAC por papel × filial × tipo_destino.

    Admin do Clavis passa sempre. Demais papéis validados via MembroManutencao.
    """
    if user.role == "admin":
        return

    membro = await get_membro(db, user, filial_id=os.filial_id)
    if not membro:
        raise HTTPException(403, "Sem vínculo com a filial da OS")

    # filial_responsavel controla toda transição na sua filial
    if membro.papel == "filial_responsavel":
        return

    # mecanico_interno: só transições operacionais e só em OS dele
    if membro.papel == "mecanico_interno":
        if os.tipo_destino != "mecanico_interno":
            raise HTTPException(403, "OS não é para mecânico interno")
        if novo_status not in {"em_execucao", "aguardando_peca", "encerrada"}:
            raise HTTPException(403, "Mecânico não pode fazer essa transição")
        return

    # motorista: só abre (nova OS) e move rascunho→aberta em OS que ele mesmo relatou
    if membro.papel == "motorista":
        if os.funcionario_relator_id != membro.funcionario_id:
            raise HTTPException(403, "OS não é sua")
        if novo_status not in {"aberta", "cancelada"}:
            raise HTTPException(403, "Motorista só pode abrir/cancelar")
        return

    raise HTTPException(403, f"Papel '{membro.papel}' sem permissão")


# ============================================================
# CRUD
# ============================================================

async def get_os(db: AsyncSession, os_id: int) -> Optional[OrdemServico]:
    os = await db.get(OrdemServico, os_id)
    if os and os.deleted_at is None:
        return os
    return None


async def listar_os(
    db: AsyncSession,
    *,
    filial_id: Optional[int] = None,
    status: Optional[str] = None,
    categoria: Optional[str] = None,
    tipo_os: Optional[str] = None,
    oficina_id: Optional[int] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[OrdemServico]:
    stmt = _ativas(select(OrdemServico), OrdemServico)
    if filial_id is not None:
        stmt = stmt.where(OrdemServico.filial_id == filial_id)
    if status:
        stmt = stmt.where(OrdemServico.status == status)
    if categoria:
        stmt = stmt.where(OrdemServico.categoria == categoria)
    if tipo_os:
        stmt = stmt.where(OrdemServico.tipo_os == tipo_os)
    if oficina_id is not None:
        stmt = stmt.where(OrdemServico.oficina_id == oficina_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(OrdemServico.descricao_problema.ilike(like))
    stmt = stmt.order_by(OrdemServico.data_abertura.desc()).limit(limit).offset(offset)
    return list((await db.execute(stmt)).scalars().all())


async def contar_os(
    db: AsyncSession, *, filial_id: Optional[int] = None, status: Optional[str] = None,
) -> int:
    stmt = _ativas(select(func.count()).select_from(OrdemServico), OrdemServico)
    if filial_id is not None:
        stmt = stmt.where(OrdemServico.filial_id == filial_id)
    if status:
        stmt = stmt.where(OrdemServico.status == status)
    return int((await db.execute(stmt)).scalar_one())


# ============================================================
# Transições
# ============================================================

async def transicionar(
    db: AsyncSession, os_id: int, novo_status: str,
    user: User, motivo: Optional[str] = None,
) -> OrdemServico:
    """Move a OS pelo fluxo, validando estado + RBAC + auditando."""
    os = await get_os(db, os_id)
    if os is None:
        raise HTTPException(404, "OS não encontrada")

    if os.status == novo_status:
        return os

    validos = TRANSICOES_VALIDAS.get(os.status, set())
    if novo_status not in validos:
        raise HTTPException(
            400, f"Transição {os.status}→{novo_status} inválida"
        )

    await autorizar_transicao(db, user, os, novo_status)

    if novo_status == "cancelada" and not motivo:
        raise HTTPException(400, "Motivo obrigatório para cancelar")

    status_anterior = os.status
    os.status = novo_status
    if novo_status == "cancelada":
        os.motivo_reprovacao = motivo
    if novo_status == "encerrada":
        os.data_encerramento = datetime.utcnow()

    await _auditar(
        db, os_id, user,
        operacao=f"status:{status_anterior}→{novo_status}",
        motivo=motivo, filial_id=os.filial_id,
    )
    await db.commit()
    await db.refresh(os)
    return os


async def submeter_orcamento(
    db: AsyncSession, os_id: int, user: User,
) -> OrdemServico:
    """Envia OS para aprovação. Auto-aprova se valor < teto.

    Regras:
    - `valor_total > 0` (não permite submeter OS vazia)
    - `status == aguardando_orcamento` (não pode pular fase)
    - Auto: `aprovado_por = NULL` + `motivo_aprovacao = "auto"` (sem SYSTEM_USER_ID)
    """
    os = await get_os(db, os_id)
    if os is None:
        raise HTTPException(404, "OS não encontrada")
    if os.status != "aguardando_orcamento":
        raise HTTPException(
            400, "Só submete orçamento a partir de aguardando_orcamento"
        )
    if (os.valor_total or Decimal("0")) <= 0:
        raise HTTPException(
            400, "Lance ao menos 1 item de peça/serviço antes de submeter"
        )

    await autorizar_transicao(db, user, os, "aguardando_aprovacao")

    teto = await _get_config(db, "teto_autoaprovacao", TETO_AUTOAPROVACAO_DEFAULT)

    if os.valor_total < teto:
        # Auto-aprovação: pula direto pra em_execucao
        os.status = "em_execucao"
        os.aprovado_por_user_id = None  # v3: NULL em vez de SYSTEM_USER_ID
        os.aprovado_em = datetime.utcnow()
        os.motivo_aprovacao = "auto"
        await _auditar(
            db, os_id, user,
            operacao="auto-aprovada",
            motivo=f"valor {os.valor_total} < teto {teto}",
            filial_id=os.filial_id,
        )
    else:
        os.status = "aguardando_aprovacao"
        os.motivo_aprovacao = None
        await _auditar(
            db, os_id, user,
            operacao="submetido-orcamento",
            motivo=f"valor {os.valor_total} >= teto {teto}",
            filial_id=os.filial_id,
        )

    await db.commit()
    await db.refresh(os)
    return os


async def aprovar(
    db: AsyncSession, os_id: int, user: User,
    observacoes: Optional[str] = None,
) -> OrdemServico:
    """Aprovação manual — só filial_responsavel/admin."""
    os = await get_os(db, os_id)
    if os is None:
        raise HTTPException(404, "OS não encontrada")
    if os.status != "aguardando_aprovacao":
        raise HTTPException(400, "OS não está aguardando aprovação")

    await autorizar_transicao(db, user, os, "em_execucao")

    os.status = "em_execucao"
    os.aprovado_por_user_id = user.id
    os.aprovado_em = datetime.utcnow()
    os.motivo_aprovacao = "manual"

    await _auditar(
        db, os_id, user,
        operacao="aprovada",
        motivo=observacoes,
        filial_id=os.filial_id,
    )
    await db.commit()
    await db.refresh(os)
    return os


async def reprovar(
    db: AsyncSession, os_id: int, user: User, motivo: str,
) -> OrdemServico:
    """Reprova → cancela a OS."""
    if not motivo:
        raise HTTPException(400, "Motivo obrigatório")
    return await transicionar(db, os_id, "cancelada", user, motivo=motivo)


async def pedir_2o_orcamento(
    db: AsyncSession, os_id: int, user: User, motivo: str,
) -> OrdemServico:
    """Volta de aguardando_aprovacao → aguardando_orcamento."""
    if not motivo:
        raise HTTPException(400, "Motivo obrigatório")
    return await transicionar(
        db, os_id, "aguardando_orcamento", user, motivo=motivo,
    )


# ============================================================
# Reabrir em garantia
# ============================================================

async def reabrir_em_garantia(
    db: AsyncSession, os_id: int, user: User,
) -> OrdemServico:
    """Cria OS nova, com `reaberta_de_os_id` apontando p/ a original.

    Só permitido se a original está `encerrada` e algum item ainda tem
    garantia ativa (usar view `manutencao_garantia_ativa` pra confirmar).
    """
    original = await get_os(db, os_id)
    if original is None:
        raise HTTPException(404, "OS original não encontrada")
    if original.status != "encerrada":
        raise HTTPException(400, "Só reabre OS encerrada")

    # Verifica se ainda tem item em garantia ativa
    stmt = select(func.count()).select_from(OsItemLinha).where(
        OsItemLinha.os_id == original.id,
        OsItemLinha.garantia_dias > 0,
    )
    tem_itens = int((await db.execute(stmt)).scalar_one())
    if tem_itens == 0:
        raise HTTPException(400, "OS original sem itens com garantia")

    # Cria nova OS
    nova = OrdemServico(
        veiculo_id=original.veiculo_id,
        filial_id=original.filial_id,
        tipo_os="devolucao",
        status="aberta",
        categoria=original.categoria,
        km_veiculo=original.km_veiculo,  # atualiza no submit
        oficina_id=original.oficina_id,
        valor_total=Decimal("0"),
        descricao_problema=f"Reabertura em garantia da OS #{original.id}",
        aberto_por_user_id=user.id,
        funcionario_relator_id=original.funcionario_relator_id,
        tipo_destino=original.tipo_destino,
        reaberta_de_os_id=original.id,
    )
    db.add(nova)
    await db.flush()

    await _auditar(
        db, nova.id, user,
        operacao="reaberta-garantia",
        motivo=f"a partir de OS #{original.id}",
        filial_id=nova.filial_id,
    )
    await db.commit()
    await db.refresh(nova)
    return nova


# ============================================================
# Soft delete
# ============================================================

async def soft_delete_os(
    db: AsyncSession, os_id: int, user: User, motivo: Optional[str] = None,
) -> None:
    os = await get_os(db, os_id)
    if os is None:
        raise HTTPException(404, "OS não encontrada")
    os.deleted_at = datetime.utcnow()
    await _auditar(
        db, os_id, user,
        operacao="deleted",
        motivo=motivo,
        filial_id=os.filial_id,
    )
    await db.commit()
