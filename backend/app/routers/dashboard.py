"""Dashboard CPK por filial — KPIs + distribuição + top veículos/oficinas."""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import (OficinaPadronizada, OrdemServico, OsItemLinha, StatusOsEnum,
                      User, VeiculoSnapshot, AnexosOs, TipoAnexoEnum)
from ..schemas import DashboardFilial

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardFilial)
def dashboard(
    filial_id: Optional[int] = Query(default=None),
    periodo_dias: int = Query(default=30),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    base = db.query(OrdemServico).filter(OrdemServico.deleted_at.is_(None))
    if user.role != "admin":
        base = base.filter(OrdemServico.filial_id == user.filial_id)
    elif filial_id:
        base = base.filter(OrdemServico.filial_id == filial_id)

    agora = datetime.utcnow()
    inicio_mes = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    janela_periodo = agora - timedelta(days=periodo_dias)

    no_mes = base.filter(OrdemServico.data_abertura >= inicio_mes)
    encerradas_mes = no_mes.filter(OrdemServico.status == StatusOsEnum.encerrada)
    custo_mes = encerradas_mes.with_entities(func.coalesce(func.sum(OrdemServico.valor_total), 0)).scalar() or Decimal("0")
    count_mes = no_mes.count()
    ticket_medio_mes = (Decimal(str(custo_mes)) / count_mes) if count_mes else Decimal("0")
    maior_mes = no_mes.with_entities(func.coalesce(func.max(OrdemServico.valor_total), 0)).scalar() or Decimal("0")

    abertas = base.filter(OrdemServico.status.in_([
        StatusOsEnum.aberta, StatusOsEnum.aguardando_anexos,
        StatusOsEnum.pronta_execucao, StatusOsEnum.em_execucao,
    ])).count()
    cutoff_atrasada = agora - timedelta(days=5)
    atrasadas = base.filter(
        OrdemServico.status.in_([StatusOsEnum.aberta, StatusOsEnum.em_execucao]),
        OrdemServico.data_abertura < cutoff_atrasada,
    ).count()

    # CPK YTD: custo encerrado YTD / soma km veículos
    inicio_ano = agora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    custo_ytd = base.filter(
        OrdemServico.status == StatusOsEnum.encerrada,
        OrdemServico.data_encerramento >= inicio_ano,
    ).with_entities(func.coalesce(func.sum(OrdemServico.valor_total), 0)).scalar() or Decimal("0")

    veiculos_query = db.query(VeiculoSnapshot).filter(VeiculoSnapshot.ativo.is_(True))
    if user.role != "admin":
        veiculos_query = veiculos_query.filter(VeiculoSnapshot.filial_id == user.filial_id)
    elif filial_id:
        veiculos_query = veiculos_query.filter(VeiculoSnapshot.filial_id == filial_id)
    km_total = sum(v.km_atual for v in veiculos_query.all()) or 1
    cpk = (Decimal(str(custo_ytd)) / km_total).quantize(Decimal("0.01")) if km_total else Decimal("0")

    # % com NF: % das encerradas com pelo menos 1 anexo tipo nf
    total_encerradas = base.filter(OrdemServico.status == StatusOsEnum.encerrada).count()
    com_nf = base.filter(
        OrdemServico.status == StatusOsEnum.encerrada,
        OrdemServico.id.in_(
            db.query(AnexosOs.os_id).filter(AnexosOs.tipo == TipoAnexoEnum.nf)
        ),
    ).count()
    pct_nf = (Decimal(str(com_nf * 100)) / total_encerradas).quantize(Decimal("0.1")) if total_encerradas else Decimal("0")

    # % preventivas no prazo (proxy: encerradas/total preventivas)
    prev_total = base.filter(OrdemServico.tipo_os == "preventiva_automatica").count()
    prev_ok = base.filter(
        OrdemServico.tipo_os == "preventiva_automatica",
        OrdemServico.status == StatusOsEnum.encerrada,
    ).count()
    pct_prev = (Decimal(str(prev_ok * 100)) / prev_total).quantize(Decimal("0.1")) if prev_total else Decimal("0")

    # Série temporal últimos 12 meses
    serie = []
    for m in range(11, -1, -1):
        mes_inicio = (agora.replace(day=1) - timedelta(days=30 * m)).replace(day=1)
        mes_fim = (mes_inicio + timedelta(days=32)).replace(day=1)
        valor = base.filter(
            OrdemServico.status == StatusOsEnum.encerrada,
            OrdemServico.data_encerramento >= mes_inicio,
            OrdemServico.data_encerramento < mes_fim,
        ).with_entities(func.coalesce(func.sum(OrdemServico.valor_total), 0)).scalar() or 0
        serie.append({"mes": mes_inicio.strftime("%Y-%m"), "valor": float(valor)})

    # Distribuição por tipo (categorias do problema)
    dist_rows = (
        base.filter(OrdemServico.status == StatusOsEnum.encerrada)
        .with_entities(
            OrdemServico.descricao_problema,
            func.count(OrdemServico.id),
            func.coalesce(func.sum(OrdemServico.valor_total), 0),
        )
        .group_by(OrdemServico.descricao_problema)
        .all()
    )
    cats = {}
    for desc, cnt, val in dist_rows:
        if not desc:
            continue
        cat = desc.split(" — ")[0] if " — " in desc else desc.split()[0]
        cur = cats.setdefault(cat, {"count": 0, "valor": 0.0})
        cur["count"] += cnt
        cur["valor"] += float(val)
    distribuicao = sorted(
        [{"tipo": k, **v} for k, v in cats.items()],
        key=lambda x: x["valor"], reverse=True,
    )[:10]

    # Top 5 veículos
    top_v_rows = (
        base.filter(OrdemServico.status == StatusOsEnum.encerrada)
        .with_entities(
            VeiculoSnapshot.placa, VeiculoSnapshot.modelo, VeiculoSnapshot.filial_id,
            func.count(OrdemServico.id), func.coalesce(func.sum(OrdemServico.valor_total), 0),
        )
        .join(VeiculoSnapshot, VeiculoSnapshot.id == OrdemServico.veiculo_id)
        .group_by(VeiculoSnapshot.placa, VeiculoSnapshot.modelo, VeiculoSnapshot.filial_id)
        .order_by(func.sum(OrdemServico.valor_total).desc())
        .limit(5).all()
    )
    top_veiculos = [
        {"placa": p, "modelo": m, "filial_id": f, "count": int(c), "custo_total": float(v)}
        for p, m, f, c, v in top_v_rows
    ]

    # Top 5 oficinas
    top_o_rows = (
        base.filter(OrdemServico.status == StatusOsEnum.encerrada)
        .with_entities(
            OficinaPadronizada.nome,
            func.count(OrdemServico.id),
            func.coalesce(func.sum(OrdemServico.valor_total), 0),
        )
        .join(OficinaPadronizada, OficinaPadronizada.id == OrdemServico.oficina_id)
        .group_by(OficinaPadronizada.nome)
        .order_by(func.sum(OrdemServico.valor_total).desc())
        .limit(5).all()
    )
    top_oficinas = [
        {"nome": n, "count": int(c), "custo_total": float(v)} for n, c, v in top_o_rows
    ]

    # Variação % do custo do mês atual vs mês anterior (cálculo real, sem mock)
    inicio_mes_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)
    custo_mes_anterior = base.filter(
        OrdemServico.status == StatusOsEnum.encerrada,
        OrdemServico.data_encerramento >= inicio_mes_anterior,
        OrdemServico.data_encerramento < inicio_mes,
    ).with_entities(func.coalesce(func.sum(OrdemServico.valor_total), 0)).scalar() or Decimal("0")
    if custo_mes_anterior > 0:
        variacao = ((Decimal(str(custo_mes)) - Decimal(str(custo_mes_anterior))) / Decimal(str(custo_mes_anterior)) * 100).quantize(Decimal("0.1"))
    else:
        variacao = Decimal("0")

    return DashboardFilial(
        cpk_acumulado_ytd=cpk,
        cpk_variacao_pct=variacao,
        custo_total_mes=Decimal(str(custo_mes)),
        os_no_mes=count_mes, ticket_medio=ticket_medio_mes.quantize(Decimal("0.01")),
        maior_os_mes=Decimal(str(maior_mes)),
        os_abertas=abertas, os_atrasadas=atrasadas,
        pct_preventiva_no_prazo=pct_prev,
        pct_com_nf=pct_nf,
        serie_temporal_12m=serie,
        distribuicao_tipo=distribuicao,
        top_veiculos=top_veiculos,
        top_oficinas=top_oficinas,
    )
