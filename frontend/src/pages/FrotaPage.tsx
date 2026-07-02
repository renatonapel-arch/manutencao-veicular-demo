import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { fmtKm, FilialChip } from '../components/Badges'
import { DataTable } from '../components/DataTable'
import { Icon } from '../components/Icons'
import { useFilial } from '../context/FilialContext'

/** Frota — somente leitura, fonte: Cadastro Veicular (frota-demo). */
export default function FrotaPage() {
  const { filialId } = useFilial()
  const [q, setQ] = useState('')

  const { data: veiculos, isLoading } = useQuery({
    queryKey: ['frota', filialId, q],
    queryFn: () => {
      const p = new URLSearchParams()
      if (filialId) p.set('filial_id', String(filialId))
      if (q) p.set('q', q)
      return api.get('/veiculos?' + p).then(r => r.data)
    },
  })

  return (
    <section>
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <span className="pill pill-sky">
          <Icon name="refresh" size={11} /> Fonte: Cadastro Veicular
        </span>
        <span className="text-xs text-ink-500">
          Somente leitura · {veiculos?.length ?? 0} veículos ativos · manutenção não altera a frota
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-5">
        <div className="relative flex-1 max-w-md">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-400">
            <Icon name="search" size={16} />
          </span>
          <input
            className="input pl-10"
            placeholder="Buscar por placa ou modelo…"
            value={q}
            onChange={e => setQ(e.target.value)}
          />
        </div>
      </div>

      <div className="card overflow-hidden">
        <DataTable
          data={veiculos || []}
          loading={isLoading}
          rowKey={(v: any) => v.id}
          onRowClick={(v: any) => location.assign(`/veiculo/${v.placa}`)}
          emptyMessage="Frota vazia. Rode o sync no Admin."
          columns={[
            {
              key: 'placa', label: 'Placa',
              accessor: (v: any) => v.placa, filter: true,
              render: (v: any) => <span className="font-mono font-semibold text-navy-800">{v.placa}</span>,
            },
            {
              key: 'modelo', label: 'Modelo',
              accessor: (v: any) => v.modelo || '', filter: true,
              render: (v: any) => (
                <>
                  <div className="font-semibold">{v.modelo}</div>
                  {v.marca && <div className="text-xs text-ink-500">{v.marca}</div>}
                </>
              ),
            },
            {
              key: 'tipo', label: 'Tipo',
              accessor: (v: any) => v.tipo || '', filter: true,
              render: (v: any) => <span className="pill pill-gray">{v.tipo || '—'}</span>,
            },
            {
              key: 'filial_id', label: 'Filial',
              accessor: (v: any) => v.filial_id, filter: true,
              render: (v: any) => <FilialChip filialId={v.filial_id} />,
            },
            {
              key: 'km_atual', label: 'Km atual', align: 'right',
              accessor: (v: any) => Number(v.km_atual || 0),
              cellClassName: 'font-mono num',
              render: (v: any) => fmtKm(v.km_atual),
            },
            {
              key: 'vencimento_crlv', label: 'CRLV vence',
              accessor: (v: any) => v.vencimento_crlv || '', filter: true,
              cellClassName: 'font-mono text-xs text-ink-500',
              render: (v: any) => v.vencimento_crlv || '—',
            },
          ]}
        />
      </div>
    </section>
  )
}
