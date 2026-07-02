import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { fmtBRL, StatusBadge } from '../components/Badges'
import { Icon } from '../components/Icons'
import { useFilial } from '../context/FilialContext'

/** Dashboard — layout 1:1 com o mockup aprovado:
 *  4 KPIs grandes → chart área + "Onde o dinheiro foi" → últimas OS. */
export default function DashboardPage() {
  const { filialId } = useFilial()
  const qs = filialId ? `?filial_id=${filialId}` : ''

  const { data: dash, isLoading } = useQuery({
    queryKey: ['dashboard', filialId],
    queryFn: () => api.get(`/dashboard${qs}`).then(r => r.data),
  })

  const { data: ultimas } = useQuery({
    queryKey: ['ultimasOS', filialId],
    queryFn: () =>
      api.get(`/ordem-servico?limit=5${filialId ? `&filial_id=${filialId}` : ''}`).then(r => r.data),
  })

  if (isLoading || !dash) {
    return <div className="text-ink-500 text-sm">Carregando…</div>
  }

  const variacao = Number(dash.cpk_variacao_pct || 0)
  const serie: { mes: string; valor: number }[] = (dash.serie_temporal_12m || []).slice(-12)
  const maxSerie = Math.max(...serie.map(s => s.valor), 1)
  const totalSerie = serie.reduce((s, x) => s + x.valor, 0)

  const cats: { tipo: string; valor: number }[] = (dash.distribuicao_tipo || []).slice(0, 5)
  const maxCat = Math.max(...cats.map(c => c.valor), 1)

  // pontos do chart SVG (área + linha + pontos vazados, padrão mockup)
  const W = 550
  const step = serie.length > 1 ? W / (serie.length - 1) : W
  const pts = serie.map((s, i) => ({
    x: 55 + i * step,
    y: 150 - (s.valor / maxSerie) * 105,
  }))
  const linePath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(0)},${p.y.toFixed(0)}`).join(' ')
  const areaPath = pts.length
    ? `M${pts[0].x.toFixed(0)},150 ` + pts.map(p => `L${p.x.toFixed(0)},${p.y.toFixed(0)}`).join(' ') + ` L${pts[pts.length - 1].x.toFixed(0)},150 Z`
    : ''

  return (
    <section>
      {/* ---- 4 KPIs ---- */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="card card-lift p-5">
          <div className="flex items-start justify-between">
            <div className="kpi-label">Custo por km</div>
            {variacao !== 0 && (
              <span className={`pill ${variacao < 0 ? 'pill-ok' : 'pill-err'}`}>
                <Icon name={variacao < 0 ? 'arrow-down' : 'arrow-up'} size={11} />
                {Math.abs(variacao)}%
              </span>
            )}
          </div>
          <div className={`kpi-value text-navy-900 mt-4 num ${String(dash.cpk_acumulado_ytd).length > 6 ? 'text-2xl' : 'text-4xl'}`}>
            {fmtBRL(dash.cpk_acumulado_ytd)}
            <span className="text-base text-ink-400 font-medium">/km</span>
          </div>
          <div className="text-xs text-ink-500 mt-2">
            {variacao === 0 ? 'sem baseline do mês anterior' : 'vs mês anterior'}
          </div>
        </div>

        <div className="card card-lift p-5">
          <div className="flex items-start justify-between">
            <div className="kpi-label">Custo do mês</div>
            <span className="pill pill-sky">{dash.os_no_mes} OS</span>
          </div>
          <div className="kpi-value text-navy-900 text-4xl mt-4 num">{fmtBRL(dash.custo_total_mes)}</div>
          <div className="text-xs text-ink-500 mt-2">ticket médio {fmtBRL(dash.ticket_medio)}</div>
        </div>

        <div className="card card-lift p-5">
          <div className="flex items-start justify-between">
            <div className="kpi-label">OS abertas</div>
            {dash.os_atrasadas > 0 && <span className="pill pill-err">{dash.os_atrasadas} atrasadas</span>}
          </div>
          <div className="kpi-value text-navy-900 text-4xl mt-4 num">{dash.os_abertas}</div>
          <div className="text-xs text-ink-500 mt-2">nas fases ativas</div>
        </div>

        <div className="card card-lift p-5">
          <div className="flex items-start justify-between">
            <div className="kpi-label">% com NF</div>
            <span className="pill pill-warn">meta 90%</span>
          </div>
          <div className="kpi-value text-navy-900 text-4xl mt-4 num">
            {Number(dash.pct_com_nf).toFixed(0)}
            <span className="text-2xl text-ink-400 font-medium">%</span>
          </div>
          <div className="text-xs text-ink-500 mt-2">das OS encerradas</div>
        </div>
      </div>

      {/* ---- Chart + Onde o dinheiro foi ---- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="card p-5 lg:col-span-2">
          <div className="flex items-baseline justify-between mb-6">
            <div>
              <h3 className="display text-base font-bold text-navy-900">Custo mensal</h3>
              <div className="text-xs text-ink-500 mt-0.5">últimos 12 meses</div>
            </div>
            <div className="text-xs text-ink-500 font-mono num">total: {fmtBRL(totalSerie)}</div>
          </div>
          {totalSerie > 0 ? (
            <svg viewBox="0 0 600 200" className="w-full h-52">
              <defs>
                <linearGradient id="dashGrad" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#74A9D7" stopOpacity=".35" />
                  <stop offset="100%" stopColor="#74A9D7" stopOpacity="0" />
                </linearGradient>
              </defs>
              <line x1="40" y1="45" x2="590" y2="45" stroke="#EEF3F7" strokeDasharray="2 3" />
              <line x1="40" y1="97" x2="590" y2="97" stroke="#EEF3F7" strokeDasharray="2 3" />
              <line x1="40" y1="150" x2="590" y2="150" stroke="#EEF3F7" />
              <text x="35" y="49" textAnchor="end" fontSize="10" fill="#93a7b6" fontFamily="JetBrains Mono">
                {fmtBRL(maxSerie)}
              </text>
              <text x="35" y="154" textAnchor="end" fontSize="10" fill="#93a7b6" fontFamily="JetBrains Mono">
                R$ 0
              </text>
              <path d={areaPath} fill="url(#dashGrad)" />
              <path d={linePath} fill="none" stroke="#0A3C5F" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              <g fill="#fff" stroke="#0A3C5F" strokeWidth="2">
                {pts.map((p, i) => (
                  <circle key={i} cx={p.x} cy={p.y} r={i === pts.length - 1 ? 5.5 : 4} />
                ))}
              </g>
              <g fontSize="10" fill="#62798c" textAnchor="middle" fontFamily="Inter">
                {serie.map((s, i) => (
                  <text key={s.mes} x={55 + i * step} y="175">
                    {s.mes.slice(5)}/{s.mes.slice(2, 4)}
                  </text>
                ))}
              </g>
            </svg>
          ) : (
            <div className="h-52 flex items-center justify-center text-ink-400 text-sm border border-dashed border-line rounded-xl">
              Sem dados no período
            </div>
          )}
        </div>

        <div className="card p-5">
          <h3 className="display text-base font-bold text-navy-900 mb-1">Onde o dinheiro foi</h3>
          <div className="text-xs text-ink-500 mb-5">principais categorias</div>
          {cats.length ? (
            <div className="space-y-4">
              {cats.map((c, i) => (
                <div key={c.tipo}>
                  <div className="flex justify-between text-sm mb-1.5">
                    <span>{c.tipo}</span>
                    <span className="font-mono num font-semibold">{fmtBRL(c.valor)}</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-sky-bg overflow-hidden">
                    <div
                      className={i < 2 ? 'h-full bg-navy-800' : 'h-full bg-sky-500'}
                      style={{ width: `${Math.max((c.valor / maxCat) * 100, 3)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty text-sm">Nenhuma OS encerrada no período.</div>
          )}
        </div>
      </div>

      {/* ---- Últimas OS ---- */}
      <div className="card overflow-hidden">
        <div className="px-6 py-4 flex items-center justify-between border-b border-line">
          <div>
            <h3 className="display text-base font-bold text-navy-900">Últimas ordens de serviço</h3>
            <div className="text-xs text-ink-500 mt-0.5">as 5 mais recentes</div>
          </div>
          <Link to="/os" className="text-sm text-sky-700 font-semibold flex items-center gap-1 hover:gap-2 transition-all">
            Ver todas <Icon name="chevron-right" size={14} />
          </Link>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] uppercase tracking-wider text-ink-500 bg-[#F8FBFD]">
              <th className="text-left px-6 py-3 font-semibold">OS</th>
              <th className="text-left py-3 font-semibold">Veículo</th>
              <th className="text-left py-3 font-semibold">Categoria</th>
              <th className="text-left py-3 font-semibold">Status</th>
              <th className="text-right px-6 py-3 font-semibold">Valor</th>
            </tr>
          </thead>
          <tbody>
            {(ultimas?.data || []).map((os: any) => (
              <tr key={os.id} className="row border-t border-line cursor-pointer" onClick={() => location.assign(`/os/${os.id}`)}>
                <td className="px-6 py-4 font-mono font-semibold text-navy-800">#{os.id}</td>
                <td className="py-4">
                  <div className="font-semibold">{os.veiculo_modelo || '—'}</div>
                  <div className="text-xs text-ink-500 font-mono">{os.veiculo_placa}</div>
                </td>
                <td className="py-4">
                  {os.categoria ? <span className="pill pill-sky">{os.categoria}</span> : <span className="text-ink-400">—</span>}
                </td>
                <td className="py-4"><StatusBadge status={os.status} /></td>
                <td className="px-6 py-4 text-right font-mono num font-semibold">{fmtBRL(os.valor_total)}</td>
              </tr>
            ))}
            {!(ultimas?.data || []).length && (
              <tr><td colSpan={5} className="empty">Nenhuma OS ainda.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
