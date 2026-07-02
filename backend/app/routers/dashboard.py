"""Dashboard CPK por filial — KPIs + distribuição + top veículos/oficinas (async).

Filtros de escopo (filial/admin) são uma LISTA de condições aplicada
explicitamente em cada query — sem introspecção de whereclause (frágil:
quebrava com 1 condição só, BinaryExpression não tem .clauses).
"""
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


def _escopo(user: User, filial_id: Optional[int]) -> list:
    """Condições de escopo: sempre deleted_at IS NULL + filial conforme RBAC."""
    conds = [OrdemServico.deleted_at.is_(None)]
    if user.role != "admin":
        conds.append(OrdemServico.filial_id == user.filial_id)
    elif filial_id:
        conds.append(OrdemServico.filial_id == filial_id)
    return conds


async def _soma(db: AsyncSession, conds: list) -> Decimal:
    stmt = select(func.coalesce(func.sum(OrdemServico.valor_total), 0)).where(*conds)
    return Decimal(str((await db.execute(stmt)).scalar_one() or 0))


async def _conta(db: AsyncSession, conds: list) -> int:
    stmt = select(func.count()).select_from(OrdemServico).where(*conds)
    return int((await db.execute(stmt)).scalar_one())


@router.get("", response_model=DashboardFilial)
async def dashboard(
    filial_id: Optional[int] = Query(default=None),
    periodo_dias: int = Query(default=30),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    escopo = _escopo(user, filial_id)

    agora = datetime.utcnow()
    inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    custo_mes = await _soma(db, escopo + [
        OrdemServico.data_abertura >= inicio_mes,
        OrdemServico.status == "encerrada",
    ])
    count_mes = await _conta(db, escopo + [OrdemServico.data_abertura >= inicio_mes])
    ticket_medio_mes = (custo_mes / count_mes) if count_mes else Decimal("0")

    maior_stmt = select(func.coalesce(func.max(OrdemServico.valor_total), 0)).where(
        *(escopo + [OrdemServico.data_abertura >= inicio_mes])
    )
    maior_mes = Decimal(str((await db.execute(maior_stmt)).scalar_one() or 0))

    abertas = await _conta(db, escopo + [OrdemServico.status.in_([
        "aberta", "em_triagem", "aguardando_orcamento",
        "aguardando_aprovacao", "em_execucao", "aguardando_peca",
    ])])
    cutoff_atrasada = agora - timedelta(days=5)
    atrasadas = await _conta(db, escopo + [
        OrdemServico.status.in_(["aberta", "em_execucao"]),
        OrdemServico.data_abertura < cutoff_atrasada,
    ])

    inicio_ano = agora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    custo_ytd = await _soma(db, escopo + [
        OrdemServico.status == "encerrada",
        OrdemServico.data_encerramento >= inicio_ano,
    ])

    # CPK YTD = custo_ytd / km_percorrido_no_ano
    # km percorrido é aproximado por (max - min) de km_veiculo nas OS do ano por veículo.
    # Se um veículo não teve OS no ano, ele não entra no denominador (nem no numerador).
    # Fallback: se não der pra calcular (ex: 1 OS só por veículo), usa 3% do km_atual como
    # heurística de km_ano_típico (~15-30k km/ano em frota comercial).
    km_stmt = (
        select(
            OrdemServico.veiculo_id,
            func.max(OrdemServico.km_veiculo).label("km_max"),
            func.min(OrdemServico.km_veiculo).label("km_min"),
        )
        .where(*escopo, OrdemServico.data_abertura >= inicio_ano,
               OrdemServico.km_veiculo > 0)
        .group_by(OrdemServico.veiculo_id)
    )
    km_rows = (await db.execute(km_stmt)).all()
    km_percorrido_calc = sum(int(r.km_max - r.km_min) for r in km_rows if r.km_max and r.km_min)

    # Fallback: soma 3% do km_atual dos veículos com OS mas sem spread
    if km_percorrido_calc < 1000:
        veic_stmt = select(func.coalesce(func.sum(VeiculoSnapshot.km_atual), 0)).where(
            VeiculoSnapshot.ativo.is_(True)
        )
        if user.role != "admin":
            veic_stmt = veic_stmt.where(VeiculoSnapshot.filial_id == user.filial_id)
        elif filial_id:
            veic_stmt = veic_stmt.where(VeiculoSnapshot.filial_id == filial_id)
        km_frota_total = int((await db.execute(veic_stmt)).scalar_one() or 0)
        km_percorrido_calc = int(km_frota_total * 0.03)  # ~3% do km total = km/ano típico

    km_percorrido = km_percorrido_calc or 1
    cpk = (custo_ytd / km_percorrido).quantize(Decimal("0.01"))

    # % com NF
    total_encerradas = await _conta(db, escopo + [OrdemServico.status == "encerrada"])
    com_nf = await _conta(db, escopo + [
        OrdemServico.status == "encerrada",
        OrdemServico.id.in_(select(AnexosOs.os_id).where(AnexosOs.tipo == "nf")),
    ])
    pct_nf = (
        (Decimal(str(com_nf * 100)) / total_encerradas).quantize(Decimal("0.1"))
        if total_encerradas else Decimal("0")
    )

    # % preventivas encerradas
    prev_total = await _conta(db, escopo + [OrdemServico.tipo_os == "preventiva_automatica"])
    prev_ok = await _conta(db, escopo + [
        OrdemServico.tipo_os == "preventiva_automatica",
        OrdemServico.status == "encerrada",
    ])
    pct_prev = (
        (Decimal(str(prev_ok * 100)) / prev_total).quantize(Decimal("0.1"))
        if prev_total else Decimal("0")
    )

    # Série temporal — 1 query com GROUP BY em vez de 12 queries
    doze_meses_atras = (agora.replace(day=1) - timedelta(days=366)).replace(day=1)
    serie_stmt = (
        select(
            func.to_char(OrdemServico.data_encerramento, "YYYY-MM").label("mes"),
            func.coalesce(func.sum(OrdemServico.valor_total), 0),
        )
        .where(*(escopo + [
            OrdemServico.status == "encerrada",
            OrdemServico.data_encerramento >= doze_meses_atras,
        ]))
        .group_by("mes")
        .order_by("mes")
    )
    serie_rows = dict((await db.execute(serie_stmt)).all())
    serie = []
    for m in range(11, -1, -1):
        mes_dt = (agora.replace(day=1) - timedelta(days=30 * m)).replace(day=1)
        key = mes_dt.strftime("%Y-%m")
        serie.append({"mes": key, "valor": float(serie_rows.get(key, 0))})

    # Distribuição por categoria (v3)
    dist_stmt = (
        select(
            OrdemServico.categoria,
            func.count(OrdemServico.id),
            func.coalesce(func.sum(OrdemServico.valor_total), 0),
        )
        .where(*(escopo + [OrdemServico.status == "encerrada"]))
        .group_by(OrdemServico.categoria)
    )
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
        .where(*(escopo + [OrdemServico.status == "encerrada"]))
        .group_by(VeiculoSnapshot.placa, VeiculoSnapshot.modelo, VeiculoSnapshot.filial_id)
        .order_by(func.sum(OrdemServico.valor_total).desc())
        .limit(5)
    )
    top_veiculos = [
        {"placa": p, "modelo": m, "filial_id": f, "count": int(c), "custo_total": float(v)}
        for p, m, f, c, v in (await db.execute(top_v_stmt)).all()
    ]

    # Top 5 oficinas
    top_o_stmt = (
        select(
            OficinaPadronizada.nome,
            func.count(OrdemServico.id),
            func.coalesce(func.sum(OrdemServico.valor_total), 0),
        )
        .join(OficinaPadronizada, OficinaPadronizada.id == OrdemServico.oficina_id)
        .where(*(escopo + [OrdemServico.status == "encerrada"]))
        .group_by(OficinaPadronizada.nome)
        .order_by(func.sum(OrdemServico.valor_total).desc())
        .limit(5)
    )
    top_oficinas = [
        {"nome": n, "count": int(c), "custo_total": float(v)}
        for n, c, v in (await db.execute(top_o_stmt)).all()
    ]

    # Variação mês atual vs anterior
    inicio_mes_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)
    custo_mes_anterior = await _soma(db, escopo + [
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
        os_no_mes=count_mes,
        ticket_medio=ticket_medio_mes.quantize(Decimal("0.01")),
        maior_os_mes=maior_mes,
        os_abertas=abertas,
        os_atrasadas=atrasadas,
        pct_preventiva_no_prazo=pct_prev,
        pct_com_nf=pct_nf,
        serie_temporal_12m=serie,
        distribuicao_tipo=distribuicao,
        top_veiculos=top_veiculos,
        top_oficinas=top_oficinas,
    )
