"""Timeline unificada do veículo — 3 fontes (OS + Troca Óleo + Checklist V2) — async."""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..dependencies import check_filial_access, get_current_user
from ..models import OrdemServico, TrocaOleoCache, User, VeiculoSnapshot
from ..schemas import TimelineItem, VeiculoOut, VeiculoTimeline

router = APIRouter(prefix="/veiculos", tags=["timeline"])


@router.get("/{veiculo_id}/timeline", response_model=VeiculoTimeline)
async def get_timeline(
    veiculo_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    v = await db.get(VeiculoSnapshot, veiculo_id)
    if not v:
        raise HTTPException(404, "Veículo não encontrado")
    if not check_filial_access(user, v.filial_id):
        raise HTTPException(403, "Cross-filial denied")

    warnings: List[str] = []
    items: List[TimelineItem] = []

    # ---- Fonte 1: OS-Manutenção ----
    try:
        stmt = (
            select(OrdemServico)
            .options(selectinload(OrdemServico.oficina))
            .where(
                OrdemServico.veiculo_id == veiculo_id,
                OrdemServico.deleted_at.is_(None),
            )
            .order_by(OrdemServico.data_abertura.desc())
            .limit(50)
        )
        oss = list((await db.execute(stmt)).scalars().all())
        for o in oss:
            items.append(TimelineItem(
                tipo="os_manutencao",
                data=o.data_abertura,
                titulo=f"OS #{o.id} · {o.descricao_problema or 'manutenção'}",
                descricao=f"{o.oficina.nome if o.oficina else '—'} · km {o.km_veiculo:,}".replace(",", "."),
                valor=o.valor_total,
                subtipo=o.tipo_os,
                status=o.status,
                oficina=o.oficina.nome if o.oficina else None,
                economia=o.economia_napel_total if o.economia_napel_total else None,
                ref_id=o.id,
            ))
    except Exception as e:
        warnings.append(f"OS-Manutenção indisponível: {e}")

    # ---- Fonte 2: Troca de óleo (cache do app dedicado) ----
    try:
        stmt = (
            select(TrocaOleoCache)
            .where(TrocaOleoCache.veiculo_id == veiculo_id)
            .order_by(TrocaOleoCache.data_troca.desc())
            .limit(30)
        )
        trocas = list((await db.execute(stmt)).scalars().all())
        for t in trocas:
            items.append(TimelineItem(
                tipo="troca_oleo",
                data=t.data_troca,
                titulo=f"Troca de óleo — {t.produto or 'Lubrax'}",
                descricao=(
                    f"{t.oficina_nome or '—'} · km {t.km:,}".replace(",", ".")
                    if t.km else (t.oficina_nome or "")
                ),
                valor=t.valor,
                status="encerrada",
                oficina=t.oficina_nome,
                ref_id=t.id,
            ))
    except Exception as e:
        warnings.append(f"Trocas de óleo temporariamente indisponíveis: {e}")

    # ---- Fonte 3: Checklist V2 — placeholder ----
    warnings.append("Checklist eletrônico indisponível — disponível a partir da Fase 2 (V2)")

    # ---- Fonte 4: Patrimonial (CRLV) ----
    if v.vencimento_crlv:
        items.append(TimelineItem(
            tipo="patrimonial",
            data=datetime.combine(v.vencimento_crlv, datetime.min.time()) - timedelta(days=365),
            titulo=f"CRLV vigente — vence em {v.vencimento_crlv.isoformat()}",
            descricao="via Cadastro Veicular",
            status="ok",
            ref_id=v.id,
        ))

    # Achata tz pra ordenação
    items.sort(key=lambda x: x.data.replace(tzinfo=None), reverse=True)

    # KPIs
    total_os = sum(1 for i in items if i.tipo == "os_manutencao")
    cutoff = datetime.utcnow() - timedelta(days=365)
    custo_12m = sum(
        (i.valor or Decimal("0")) for i in items
        if i.tipo == "os_manutencao" and i.data.replace(tzinfo=None) >= cutoff
    )
    cpk = (custo_12m / max(v.km_atual, 1)) if v.km_atual else Decimal("0")

    return VeiculoTimeline(
        veiculo=VeiculoOut.model_validate(v),
        items=items, warnings=warnings,
        total_os=total_os, custo_12m=custo_12m,
        cpk=Decimal(str(round(float(cpk), 2))),
    )
