"""Dashboard CPK por filial — KPIs + distribuição + top veículos/oficinas (async)."""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import get_current_user
from ..models import (
    AnexosOs, OficinaPadronizada, OrdemServico, User, VeiculoSnapshot,
)
from ..schemas import DashboardFilial

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _base_stmt(user: User, filial_id: Optional[int]):
    stmt = select(OrdemServico).where(OrdemServico.deleted_at.is_(None))
    if user.role != "admin":
        stmt = stmt.where(OrdemServico.filial_id == user.filial_id)
    elif filial_id:
        stmt = stmt.where(OrdemServico.filial_id == filial_id)
    return stmt


async def _scalar_sum(db: AsyncSession, base_stmt, extra_where=None) -> Decimal:
    stmt = select(func.coalesce(func.sum(OrdemServico.valor_total), 0))
    stmt = stmt.select_from(OrdemServico).where(OrdemServico.deleted_at.is_(None))
    # Recopia filtros do base_stmt
    for cond in base_stmt.whereclause.clauses if base_stmt.whereclause is not None else []:
        stmt = stmt.where(cond)
    if extra_where is not None:
        for cond in (extra_where if isinstance(extra_where, list) else [extra_where]):
            stmt = stmt.where(cond)
    return Decimal(str((await db.execute(stmt)).scalar_one() or 0))


async def _scalar_count(db: AsyncSession, base_stmt, extra_where=None) -> int:
    stmt = select(func.count()).select_from(OrdemServico).where(OrdemServico.deleted_at.is_(None))
    for cond in base_stmt.whereclause.clauses if base_stmt.whereclause is not None else []:
        stmt = stmt.where(cond)
    if extra_where is not None:
        for cond in (extra_where if isinstance(extra_where, list) else [extra_where]):
            stmt = stmt.where(cond)
    return int((await db.execute(stmt)).scalar_one())


@router.get("", response_model=DashboardFilial)
async def dashboard(
    filial_id: Optional[int] = Query(default=None),
    periodo_dias: int = Query(default=30),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base = _base_stmt(user, filial_id)

    agora = datetime.utcnow()
    inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    custo_mes = await _scalar_sum(db, base, [
        OrdemServico.data_abertura >= inicio_mes,
        OrdemServico.status == "encerrada",
    ])
    count_mes = await _scalar_count(db, base, OrdemServico.data_abertura >= inicio_mes)
    ticket_medio_mes = (custo_mes / count_mes) if count_mes else Decimal("0")

    maior_stmt = select(func.coalesce(func.max(OrdemServico.valor_total), 0)).select_from(
        OrdemServico
    ).where(OrdemServico.deleted_at.is_(None), OrdemServico.data_abertura >= inicio_mes)
    if user.role != "admin":
        maior_stmt = maior_stmt.where(OrdemServico.filial_id == user.filial_id)
    elif filial_id:
        maior_stmt = maior_stmt.where(OrdemServico.filial_id == filial_id)
    maior_mes = Decimal(str((await db.execute(maior_stmt)).scalar_one() or 0))

    abertas = await _scalar_count(db, base, OrdemServico.status.in_([
        "aberta", "em_triagem", "aguardando_orcamento",
        "aguardando_aprovacao", "em_execucao", "aguardando_peca",
    ]))
    cutoff_atrasada = agora - timedelta(days=5)
    atrasadas = await _scalar_count(db, base, [
        OrdemServico.status.in_(["aberta", "em_execucao"]),
        OrdemServico.data_abertura < cutoff_atrasada,
    ])

    inicio_ano = agora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    custo_ytd = await _scalar_sum(db, base, [
        OrdemServico.status == "encerrada",
        OrdemServico.data_encerramento >= inicio_ano,
    ])

    # CPK YTD
    veic_stmt = select(func.coalesce(func.sum(VeiculoSnapshot.km_atual), 0)).select_from(
        VeiculoSnapshot
    ).where(VeiculoSnapshot.ativo.is_(True))
    if user.role != "admin":
        veic_stmt = veic_stmt.where(VeiculoSnapshot.filial_id == user.filial_id)
    elif filial_id:
        veic_stmt = veic_stmt.where(VeiculoSnapshot.filial_id == filial_id)
    km_total = int((await db.execute(veic_stmt)).scalar_one() or 0) or 1
    cpk = (custo_ytd / km_total).quantize(Decimal("0.01")) if km_total else Decimal("0")

    # % com NF
    total_encerradas = await _scalar_count(db, base, OrdemServico.status == "encerrada")
    com_nf = await _scalar_count(db, base, [
        OrdemServico.status == "encerrada",
        OrdemServico.id.in_(select(AnexosOs.os_id).where(AnexosOs.tipo == "nf")),
    ])
    pct_nf = (Decimal(str(com_nf * 100)) / total_encerradas).quantize(Decimal("0.1")) if total_encerradas else Decimal("0")

    # % preventivas no prazo
    prev_total = await _scalar_count(db, base, OrdemServico.tipo_os == "preventiva_automatica")
    prev_ok = await _scalar_count(db, base, [
        OrdemServico.tipo_os == "preventiva_automatica",
        OrdemServico.status == "encerrada",
    ])
    pct_prev = (Decimal(str(prev_ok * 100)) / prev_total).quantize(Decimal("0.1")) if prev_total else Decimal("0")

    # Série temporal 12 meses
    serie = []
    for m in range(11, -1, -1):
        mes_inicio = (agora.replace(day=1) - timedelta(days=30 * m)).replace(day=1)
        mes_fim = (mes_inicio + timedelta(days=32)).replace(day=1)
        valor = await _scalar_sum(db, base, [
            OrdemServico.status == "encerrada",
            OrdemServico.data_encerramento >= mes_inicio,
            OrdemServico.data_encerramento < mes_fim,
        ])
        serie.append({"mes": mes_inicio.strftime("%Y-%m"), "valor": float(valor)})

    # Distribuição por categoria (novo campo v3)
    dist_stmt = (
        select(
            OrdemServico.categoria,
            func.count(OrdemServico.id),
            func.coalesce(func.sum(OrdemServico.valor_total), 0),
        )
        .where(
            OrdemServico.deleted_at.is_(None),
            OrdemServico.status == "encerrada",
        )
        .group_by(OrdemServico.categoria)
    )
    if user.role != "admin":
        dist_stmt = dist_stmt.where(OrdemServico.filial_id == user.filial_id)
    elif filial_id:
        dist_stmt = dist_stmt.where(OrdemServico.filial_id == filial_id)
    dist_rows = (await db.execute(dist_stmt)).all()
    distribuicao = sorted(
        [
            {"tipo": (cat or "Outros"), "count": int(c), "valor": float(v)}
            for cat, c, v in dist_rows
        ],
        key=lambda x: x["valor"],
        reverse=True,
    )[:10]

    # Top 5 veículos
    top_v_stmt = (
        select(
            VeiculoSnapshot.placa, VeiculoSnapshot.modelo, VeiculoSnapshot.filial_id,
            func.count(OrdemServico.id),
            func.coalesce(func.sum(OrdemServico.valor_total), 0),
        )
        .join(VeiculoSnapshot, VeiculoSnapshot.id == OrdemServico.veiculo_id)
        .where(
            OrdemServico.deleted_at.is_(None),
            OrdemServico.status == "encerrada",
        )
        .group_by(VeiculoSnapshot.placa, VeiculoSnapshot.modelo, VeiculoSnapshot.filial_id)
        .order_by(func.sum(OrdemServico.valor_total).desc())
        .limit(5)
    )
    if user.role != "admin":
        top_v_stmt = top_v_stmt.where(OrdemServico.filial_id == user.filial_id)
    elif filial_id:
        top_v_stmt = top_v_stmt.where(OrdemServico.filial_id == filial_id)
    top_v_rows = (await db.execute(top_v_stmt)).all()
    top_veiculos = [
        {"placa": p, "modelo": m, "filial_id": f, "count": int(c), "custo_total": float(v)}
        for p, m, f, c, v in top_v_rows
    ]

    # Top 5 oficinas
    top_o_stmt = (
        select(
            OficinaPadronizada.nome,
            func.count(OrdemServico.id),
            func.coalesce(func.sum(OrdemServico.valor_total), 0),
        )
        .join(OficinaPadronizada, OficinaPadronizada.id == OrdemServico.oficina_id)
        .where(
            OrdemServico.deleted_at.is_(None),
            OrdemServico.status == "encerrada",
        )
        .group_by(OficinaPadronizada.nome)
        .order_by(func.sum(OrdemServico.valor_total).desc())
        .limit(5)
    )
    if user.role != "admin":
        top_o_stmt = top_o_stmt.where(OrdemServico.filial_id == user.filial_id)
    elif filial_id:
        top_o_stmt = top_o_stmt.where(OrdemServico.filial_id == filial_id)
    top_o_rows = (await db.execute(top_o_stmt)).all()
    top_oficinas = [
        {"nome": n, "count": int(c), "custo_total": float(v)} for n, c, v in top_o_rows
    ]

    # Variação % mês atual vs anterior
    inicio_mes_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)
    custo_mes_anterior = await _scalar_sum(db, base, [
        OrdemServico.status == "encerrada",
        OrdemServico.data_encerramento >= inicio_mes_anterior,
        OrdemServico.data_encerramento < inicio_mes,
    ])
    if custo_mes_anterior > 0:
        variacao = ((custo_mes - custo_mes_anterior) / custo_mes_anterior * 100).quantize(Decimal("0.1"))
    else:
        variacao = Decimal("0")

    return DashboardFilial(
        cpk_acumulado_ytd=cpk,
        cpk_variacao_pct=variacao,
        custo_total_mes=custo_mes,
        os_no_mes=count_mes, ticket_medio=ticket_medio_mes.quantize(Decimal("0.01")),
        maior_os_mes=maior_mes,
        os_abertas=abertas, os_atrasadas=atrasadas,
        pct_preventiva_no_prazo=pct_prev,
        pct_com_nf=pct_nf,
        serie_temporal_12m=serie,
        distribuicao_tipo=distribuicao,
        top_veiculos=top_veiculos,
        top_oficinas=top_oficinas,
    )
