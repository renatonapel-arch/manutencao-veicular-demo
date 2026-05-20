import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { fmtDataHora } from '../components/Badges'
import EmptyState from '../components/EmptyState'

export default function AlertasPage() {
  const [statusFiltro, setStatusFiltro] = useState('')
  const { data: alertas } = useQuery({
    queryKey: ['alertas', statusFiltro],
    queryFn: () => api.get('/alertas' + (statusFiltro ? `?status=${statusFiltro}` : '')).then(r => r.data),
  })
  const { data: stats } = useQuery({
    queryKey: ['alertas-stats'],
    queryFn: () => api.get('/alertas/stats').then(r => r.data),
  })

  const isDLQ = statusFiltro === 'dlq'

  return (
    <section>
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="text-lg font-semibold text-naval">Alertas WhatsApp</div>
          <div className="text-xs text-ink-500">Histórico Evolution + envio manual · DLQ monitorada</div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3 mb-3">
        <div className="kpi-card"><div className="text-[10px] uppercase text-ink-500">Enviados hoje</div><div className="text-xl font-semibold font-mono">{stats?.enviados_hoje ?? 0}</div></div>
        <div className="kpi-card"><div className="text-[10px] uppercase text-ink-500">Pendentes</div><div className="text-xl font-semibold font-mono text-warn-fg">{stats?.pendentes ?? 0}</div></div>
        <div className="kpi-card"><div className="text-[10px] uppercase text-ink-500">Falhas (24h)</div><div className="text-xl font-semibold font-mono text-danger-fg">{stats?.falhas_24h ?? 0}</div></div>
        <div className="kpi-card border-danger"><div className="text-[10px] uppercase text-danger-fg">DLQ</div><div className={`text-xl font-semibold font-mono ${(stats?.dlq ?? 0) === 0 ? 'text-success-fg' : 'text-danger-fg'}`}>{stats?.dlq ?? 0}</div></div>
      </div>

      <div className="bg-white border border-border rounded p-3 mb-3">
        <select value={statusFiltro} onChange={(e) => setStatusFiltro(e.target.value)}
                className="border border-border-strong rounded px-2 py-1 bg-white text-xs">
          <option value="">Status: todos</option>
          <option value="sent">Enviado</option>
          <option value="pending">Pendente</option>
          <option value="failed">Falha</option>
          <option value="dlq">DLQ (vazio — bom sinal)</option>
        </select>
      </div>

      {isDLQ && (alertas?.length || 0) === 0 ? (
        <EmptyState
          titulo="Nada na fila de mortos"
          descricao="Nenhum alerta foi para DLQ — todos os envios entregues ou em retry saudável. Esse é o bom estado vazio."
          cta={<button onClick={() => setStatusFiltro('')} className="text-xs text-naval underline">Voltar à listagem</button>}
        />
      ) : (
        <div className="bg-white border border-border rounded overflow-hidden">
          <table className="w-full text-[12px] dense">
            <thead className="bg-ink-50 text-ink-500 border-b border-border">
              <tr>
                <th className="text-left">Data/Hora</th>
                <th className="text-left">OS</th>
                <th className="text-left">Template</th>
                <th className="text-left">Telefone</th>
                <th>Status</th>
                <th className="text-center">Retry</th>
              </tr>
            </thead>
            <tbody>
              {(alertas || []).length === 0 && (
                <tr><td colSpan={6} className="text-center text-ink-500 py-6">Nenhum alerta no período.</td></tr>
              )}
              {(alertas || []).map((a: any) => (
                <tr key={a.id} className="border-t border-border hover:bg-ink-50">
                  <td className="font-mono">{fmtDataHora(a.created_at)}</td>
                  <td className="font-mono">{a.os_id ? `#${a.os_id}` : '—'}</td>
                  <td>{a.template_name}</td>
                  <td className="font-mono">{a.telefone}</td>
                  <td><span className={`badge ${a.status === 'sent' ? 'bg-success-bg text-success-fg' : a.status === 'failed' ? 'bg-danger-bg text-danger-fg' : 'bg-warn-bg text-warn-fg'}`}>{a.status}</span></td>
                  <td className="text-center font-mono">{a.retry_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
