import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { fmtDataHora } from '../components/Badges'
import { DataTable } from '../components/DataTable'
import EmptyState from '../components/EmptyState'
import { useFilial } from '../context/FilialContext'

export default function AlertasPage() {
  const { filialId } = useFilial()
  const [statusFiltro, setStatusFiltro] = useState('')

  const { data: alertas } = useQuery({
    queryKey: ['alertas', statusFiltro, filialId],
    queryFn: () => {
      const p = new URLSearchParams()
      if (statusFiltro) p.set('status', statusFiltro)
      if (filialId) p.set('filial_id', String(filialId))
      return api.get('/alertas' + (p.toString() ? '?' + p : '')).then(r => r.data)
    },
  })
  const { data: stats } = useQuery({
    queryKey: ['alertas-stats', filialId],
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
        <div className="card overflow-hidden">
          <DataTable
            data={alertas || []}
            rowKey={(a: any) => a.id}
            emptyMessage="Nenhum alerta no período."
            defaultSort={{ key: 'created_at', dir: 'desc' }}
            columns={[
              {
                key: 'created_at', label: 'Data/Hora',
                accessor: (a: any) => a.created_at,
                cellClassName: 'font-mono text-xs',
                render: (a: any) => fmtDataHora(a.created_at),
              },
              {
                key: 'os_id', label: 'OS',
                accessor: (a: any) => a.os_id || 0, filter: true,
                cellClassName: 'font-mono',
                render: (a: any) => a.os_id ? `#${a.os_id}` : '—',
              },
              {
                key: 'template_name', label: 'Template',
                accessor: (a: any) => a.template_name || '', filter: true,
                render: (a: any) => a.template_name,
              },
              {
                key: 'telefone', label: 'Telefone',
                accessor: (a: any) => a.telefone || '', filter: true,
                cellClassName: 'font-mono',
                render: (a: any) => a.telefone,
              },
              {
                key: 'status', label: 'Status',
                accessor: (a: any) => a.status, filter: true,
                render: (a: any) => (
                  <span className={`pill ${a.status === 'sent' ? 'pill-ok' : a.status === 'failed' ? 'pill-err' : 'pill-warn'}`}>
                    {a.status}
                  </span>
                ),
              },
              {
                key: 'retry_count', label: 'Retry', align: 'center',
                accessor: (a: any) => Number(a.retry_count || 0),
                cellClassName: 'font-mono num',
                render: (a: any) => a.retry_count,
              },
            ]}
          />
        </div>
      )}
    </section>
  )
}
