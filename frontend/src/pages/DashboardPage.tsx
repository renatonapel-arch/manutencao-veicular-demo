import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { fmtBRL, FilialChip, StatusBadge, TipoBadge } from '../components/Badges'
import { useFilial } from '../context/FilialContext'

export default function DashboardPage() {
  const { filialId } = useFilial()
  const qs = filialId ? `?filial_id=${filialId}` : ''

  const { data: dash } = useQuery({
    queryKey: ['dashboard', filialId],
    queryFn: () => api.get(`/dashboard${qs}`).then(r => r.data),
  })

  const { data: ultimasOS } = useQuery({
    queryKey: ['ultimasOS', filialId],
    queryFn: () => api.get(`/ordem-servico?limit=7${filialId ? `&filial_id=${filialId}` : ''}`).then(r => r.data),
  })

  if (!dash) return <div className="text-ink-500">Carregando dashboard…</div>

  return (
    <section>
      {/* Toolbar */}
      <div className="flex justify-between items-center mb-3">
        <div className="flex gap-1 border border-border rounded bg-white">
          <button className="px-3 py-1 bg-naval text-white text-xs rounded-l">30d</button>
          <button className="px-3 py-1 text-xs">90d</button>
          <button className="px-3 py-1 text-xs">12m</button>
          <button className="px-3 py-1 text-xs">YTD</button>
        </div>
        <div className="flex gap-2">
          <button className="border border-border bg-white rounded px-3 py-1 text-xs">📥 PDF</button>
          <button className="border border-border bg-white rounded px-3 py-1 text-xs">📊 Excel</button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-3 mb-3">
        <div className="kpi-card">
          <div className="text-[10px] uppercase tracking-wider text-ink-500">CPK acumulado</div>
          <div className="text-2xl font-bold mt-1 font-mono text-naval">{fmtBRL(dash.cpk_acumulado_ytd)}<span className="text-sm font-normal text-ink-400">/km</span></div>
          <div className="text-[11px] text-success-fg mt-1">▼ {dash.cpk_variacao_pct}% vs mês anterior</div>
        </div>
        <div className="kpi-card">
          <div className="text-[10px] uppercase tracking-wider text-ink-500">Custo total no mês</div>
          <div className="text-2xl font-bold mt-1 font-mono text-naval">{fmtBRL(dash.custo_total_mes)}</div>
          <div className="text-[11px] text-ink-500 mt-1">{dash.os_no_mes} OS · ticket {fmtBRL(dash.ticket_medio)}</div>
        </div>
        <div className="kpi-card">
          <div className="text-[10px] uppercase tracking-wider text-ink-500">% Preventivas no prazo</div>
          <div className="text-2xl font-bold mt-1 font-mono text-warn-fg">{dash.pct_preventiva_no_prazo}%</div>
          <div className="text-[11px] text-ink-500 mt-1">meta ≥80%</div>
        </div>
        <div className="kpi-card">
          <div className="text-[10px] uppercase tracking-wider text-ink-500">% OS com NF</div>
          <div className="text-2xl font-bold mt-1 font-mono text-danger-fg">{dash.pct_com_nf}%</div>
          <div className="text-[11px] text-ink-500 mt-1">meta ≥90%</div>
        </div>
      </div>

      {/* KPI Linha 2 */}
      <div className="grid grid-cols-4 gap-3 mb-3">
        <div className="kpi-card"><div className="text-[10px] uppercase text-ink-500">OS abertas</div><div className="text-lg font-semibold font-mono">{dash.os_abertas}</div></div>
        <div className="kpi-card"><div className="text-[10px] uppercase text-ink-500">OS atrasadas (&gt;5d)</div><div className="text-lg font-semibold font-mono text-danger-fg">{dash.os_atrasadas}</div></div>
        <div className="kpi-card"><div className="text-[10px] uppercase text-ink-500">Ticket médio</div><div className="text-lg font-semibold font-mono">{fmtBRL(dash.ticket_medio)}</div></div>
        <div className="kpi-card"><div className="text-[10px] uppercase text-ink-500">Maior OS do mês</div><div className="text-lg font-semibold font-mono">{fmtBRL(dash.maior_os_mes)}</div></div>
      </div>

      {/* Evolução mensal CPK */}
      {(() => {
        const serie = dash.serie_temporal_12m || []
        if (serie.length < 2) return null
        const max = Math.max(...serie.map((s: any) => s.valor || 0), 1)
        const points = serie.map((s: any, i: number) => {
          const x = 40 + (i * 550 / Math.max(serie.length - 1, 1))
          const y = 140 - ((s.valor || 0) / max) * 110
          return `${x.toFixed(1)},${y.toFixed(1)}`
        }).join(' ')
        return (
          <div className="bg-white border border-border rounded p-3 mb-3">
            <div className="flex justify-between items-center mb-2">
              <div className="text-[13px] font-medium text-naval">Evolução mensal — custo total (últimos 12 meses)</div>
              <div className="text-[10px] text-ink-500 font-mono">máx: {fmtBRL(max)}</div>
            </div>
            <svg viewBox="0 0 600 170" className="w-full h-40">
              <line x1="40" y1="20" x2="40" y2="140" stroke="#D6E7F1"/>
              <line x1="40" y1="140" x2="590" y2="140" stroke="#D6E7F1"/>
              <text x="6" y="25" fill="#7DA4C6" fontSize="9" fontFamily="JetBrains Mono">{fmtBRL(max)}</text>
              <text x="6" y="85" fill="#7DA4C6" fontSize="9" fontFamily="JetBrains Mono">{fmtBRL(max/2)}</text>
              <text x="6" y="142" fill="#7DA4C6" fontSize="9" fontFamily="JetBrains Mono">R$ 0</text>
              <polyline points={points} stroke="#113C58" fill="none" strokeWidth="2.5"/>
              {serie.map((s: any, i: number) => {
                const x = 40 + (i * 550 / Math.max(serie.length - 1, 1))
                const y = 140 - ((s.valor || 0) / max) * 110
                return (
                  <g key={i}>
                    <circle cx={x} cy={y} r="3" fill="#113C58"/>
                    <text x={x} y="158" fill="#7DA4C6" fontSize="9" textAnchor="middle">
                      {(s.mes || '').slice(5)}/{(s.mes || '').slice(2,4)}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>
        )
      })()}

      {/* Distribuição + Top */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="bg-white border border-border rounded p-3">
          <div className="text-[13px] font-medium text-naval mb-2">Distribuição por tipo</div>
          <div className="space-y-1.5 text-[11px]">
            {(dash.distribuicao_tipo || []).slice(0, 8).map((d: any, i: number) => {
              const total = (dash.distribuicao_tipo || []).reduce((s: number, x: any) => s + (x.valor || 0), 0) || 1
              const pct = ((d.valor || 0) / total) * 100
              const cores = ['bg-danger', 'bg-warn', 'bg-ink-400', 'bg-naval', 'bg-ceu', 'bg-success', 'bg-ink-500', 'bg-noite']
              return (
                <div key={i} className="flex items-center gap-2">
                  <span className="w-24 truncate">{d.tipo}</span>
                  <div className="flex-1 bg-ink-100 h-3 rounded overflow-hidden">
                    <div className={`h-3 ${cores[i % cores.length]}`} style={{ width: `${Math.min(pct, 100)}%` }}/>
                  </div>
                  <span className="w-16 text-right font-medium font-mono">{fmtBRL(d.valor)}</span>
                </div>
              )
            })}
          </div>
        </div>

        <div className="bg-white border border-border rounded p-3">
          <div className="text-[13px] font-medium text-naval mb-2">Top 5 oficinas</div>
          <table className="w-full text-[12px] dense">
            <tbody>
              {(dash.top_oficinas || []).map((o: any, i: number) => (
                <tr key={i} className="border-t border-border">
                  <td className="font-medium">{o.nome}</td>
                  <td className="text-ink-500">{o.count} OS</td>
                  <td className="text-right font-medium font-mono">{fmtBRL(o.custo_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top Veículos */}
      <div className="bg-white border border-border rounded p-3 mb-3">
        <div className="text-[13px] font-medium text-naval mb-2">Top 5 veículos por custo</div>
        <table className="w-full text-[12px] dense">
          <tbody>
            {(dash.top_veiculos || []).map((v: any, i: number) => (
              <tr key={i} className="border-t border-border hover:bg-ink-50 cursor-pointer">
                <td className="font-mono">{v.placa}</td>
                <td className="text-ink-500">{v.modelo}</td>
                <td><FilialChip filialId={v.filial_id}/></td>
                <td className="text-right font-mono">{v.count} OS</td>
                <td className="text-right font-medium font-mono">{fmtBRL(v.custo_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Últimas OS */}
      <div className="bg-white border border-border rounded p-3">
        <div className="flex justify-between items-center mb-2">
          <div className="text-[13px] font-medium text-naval">Últimas Ordens de Serviço</div>
          <Link to="/os" className="text-xs text-naval hover:underline">Ver todas →</Link>
        </div>
        <table className="w-full text-[12px] dense">
          <thead className="text-ink-500 bg-ink-50 border-y border-border">
            <tr>
              <th className="text-left">Nº</th>
              <th className="text-left">Veículo</th>
              <th className="text-left">Filial</th>
              <th className="text-left">Tipo</th>
              <th className="text-left">Status</th>
              <th className="text-right">Valor</th>
            </tr>
          </thead>
          <tbody>
            {(ultimasOS?.data || []).map((os: any) => (
              <tr key={os.id} className="border-t border-border hover:bg-ink-50 cursor-pointer" onClick={() => location.assign(`/os/${os.id}`)}>
                <td><Link to={`/os/${os.id}`} className="font-mono text-naval">#{os.id}</Link></td>
                <td><span className="font-mono">{os.veiculo_placa || `veic ${os.veiculo_id}`}</span> <span className="text-ink-500">· {os.veiculo_modelo || ''}</span></td>
                <td><FilialChip filialId={os.filial_id}/></td>
                <td><TipoBadge tipo={os.tipo_os}/></td>
                <td><StatusBadge status={os.status}/></td>
                <td className="text-right font-medium font-mono">{fmtBRL(os.valor_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
