import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { fmtDataHora, FilialChip } from '../components/Badges'
import { DataTable } from '../components/DataTable'
import { useFilial } from '../context/FilialContext'

/** Lista de checklists mensais (V2). */
export default function ChecklistsPage() {
  const { filialId } = useFilial()
  const nav = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['checklists', filialId],
    queryFn: () => {
      const p = new URLSearchParams()
      if (filialId) p.set('filial_id', String(filialId))
      p.set('limit', '100')
      return api.get('/checklist?' + p).then(r => r.data)
    },
  })

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <div>
          <div className="display text-lg font-bold text-navy-900">Checklists mensais</div>
          <div className="text-xs text-ink-500">{data?.total ?? '—'} registrados</div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <DataTable
          data={data?.data || []}
          loading={isLoading}
          rowKey={(c: any) => c.id}
          onRowClick={(c: any) => nav(`/veiculo/${c.veiculo_placa}`)}
          emptyMessage="Nenhum checklist ainda."
          defaultSort={{ key: 'data_checklist', dir: 'desc' }}
          columns={[
            {
              key: 'data_checklist', label: 'Data',
              accessor: (c: any) => c.data_checklist,
              cellClassName: 'font-mono text-xs text-ink-500',
              render: (c: any) => fmtDataHora(c.data_checklist),
            },
            {
              key: 'veiculo', label: 'Veículo',
              accessor: (c: any) => c.veiculo_placa || '', filter: true,
              render: (c: any) => (
                <>
                  <div className="font-semibold">{c.veiculo_modelo || '—'}</div>
                  <div className="text-xs text-ink-500 font-mono">{c.veiculo_placa}</div>
                </>
              ),
            },
            {
              key: 'filial_id', label: 'Filial',
              accessor: (c: any) => c.filial_id, filter: true,
              render: (c: any) => <FilialChip filialId={c.filial_id} />,
            },
            {
              key: 'tipo_veiculo', label: 'Tipo',
              accessor: (c: any) => c.tipo_veiculo, filter: true,
              render: (c: any) => <span className="pill pill-sky">{c.tipo_veiculo}</span>,
            },
            {
              key: 'km_veiculo', label: 'Km', align: 'right',
              accessor: (c: any) => Number(c.km_veiculo || 0),
              cellClassName: 'font-mono num',
              render: (c: any) => (c.km_veiculo || 0).toLocaleString('pt-BR'),
            },
            {
              key: 'total_ok', label: 'OK', align: 'center',
              accessor: (c: any) => Number(c.total_ok || 0),
              render: (c: any) => <span className="pill pill-ok">{c.total_ok}</span>,
            },
            {
              key: 'total_problemas', label: 'Problemas', align: 'center',
              accessor: (c: any) => Number(c.total_problemas || 0),
              render: (c: any) =>
                c.total_problemas > 0
                  ? <span className="pill pill-err">{c.total_problemas}</span>
                  : <span className="text-ink-400">—</span>,
            },
            {
              key: 'os_geradas', label: 'OS geradas', align: 'center',
              accessor: (c: any) => (c.os_geradas || []).length,
              render: (c: any) => {
                const n = (c.os_geradas || []).length
                return n > 0
                  ? <span className="pill pill-warn">{n}</span>
                  : <span className="text-ink-400">—</span>
              },
            },
          ]}
        />
      </div>
    </section>
  )
}
