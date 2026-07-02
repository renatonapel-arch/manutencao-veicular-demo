import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { fmtBRL, fmtData, FilialChip, StatusBadge, TipoBadge } from '../components/Badges'
import { DataTable } from '../components/DataTable'
import { Icon } from '../components/Icons'
import { useFilial } from '../context/FilialContext'

/** Lista de OS — layout do mockup: busca + Nova OS, tabs de status, tabela em card. */

const TABS = [
  { v: '', l: 'Todas' },
  { v: 'rascunho', l: 'Rascunho' },
  { v: 'aberta', l: 'Aberta' },
  { v: 'em_triagem', l: 'Em triagem' },
  { v: 'aguardando_orcamento', l: 'Aguard. orçamento' },
  { v: 'aguardando_aprovacao', l: 'Aguard. aprovação' },
  { v: 'em_execucao', l: 'Em execução' },
  { v: 'aguardando_peca', l: 'Aguard. peça' },
  { v: 'encerrada', l: 'Concluída' },
  { v: 'cancelada', l: 'Cancelada' },
]

const CATEGORIAS = [
  'Motor', 'Pneu', 'Pastilha / Lona', 'Relação', 'Lâmpadas',
  'Elétrica', 'Bateria', 'Empilhadeira', 'Embreagem', 'Outros',
]

export default function ListaOSPage() {
  const { filialId } = useFilial()
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [categoria, setCategoria] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 20

  const { data, isLoading } = useQuery({
    queryKey: ['os', { q, status, categoria, offset, filialId }],
    queryFn: () => {
      const params = new URLSearchParams()
      if (q) params.set('q', q)
      if (status) params.set('status', status)
      if (categoria) params.set('categoria', categoria)
      if (filialId) params.set('filial_id', String(filialId))
      params.set('limit', String(limit))
      params.set('offset', String(offset))
      return api.get('/ordem-servico?' + params).then(r => r.data)
    },
  })

  const trocarTab = (v: string) => { setStatus(v); setOffset(0) }

  return (
    <section>
      {/* Toolbar: busca + categoria + Nova OS */}
      <div className="flex flex-wrap items-center gap-3 mb-5">
        <div className="relative flex-1 max-w-md min-w-[220px]">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-400">
            <Icon name="search" size={16} />
          </span>
          <input
            className="input pl-10"
            placeholder="Buscar por problema…"
            value={q}
            onChange={e => { setQ(e.target.value); setOffset(0) }}
          />
        </div>
        <select
          className="select" style={{ width: 'auto' }}
          value={categoria}
          onChange={e => { setCategoria(e.target.value); setOffset(0) }}
        >
          <option value="">Categoria: todas</option>
          {CATEGORIAS.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <div className="flex-1" />
        <Link to="/os/nova" className="btn btn-primary">
          <Icon name="plus" size={14} /> Nova OS
        </Link>
      </div>

      {/* Tabs de status */}
      <div className="flex flex-wrap items-center border-b border-line gap-1 mb-4 overflow-x-auto">
        {TABS.map(t => (
          <div
            key={t.v}
            className={`tab ${status === t.v ? 'on' : ''}`}
            onClick={() => trocarTab(t.v)}
          >
            {t.l}
            {t.v === '' && data?.total != null && (
              <span className="pill pill-sky ml-1.5">{data.total}</span>
            )}
          </div>
        ))}
      </div>

      {/* Tabela */}
      <div className="card overflow-hidden">
        <DataTable
          data={data?.data || []}
          loading={isLoading}
          rowKey={(os: any) => os.id}
          onRowClick={(os: any) => location.assign(`/os/${os.id}`)}
          emptyMessage="Nenhuma OS com esses filtros."
          columns={[
            {
              key: 'id', label: 'OS',
              accessor: (o: any) => o.id, filter: true,
              render: (o: any) => <span className="font-mono font-semibold text-navy-800">#{o.id}</span>,
            },
            {
              key: 'data_abertura', label: 'Aberta em',
              accessor: (o: any) => o.data_abertura,
              render: (o: any) => <span className="font-mono text-xs text-ink-500">{fmtData(o.data_abertura)}</span>,
            },
            {
              key: 'veiculo', label: 'Veículo',
              accessor: (o: any) => o.veiculo_placa || o.veiculo_modelo || '',
              filter: (o: any, q: string) =>
                (o.veiculo_placa || '').toLowerCase().includes(q) ||
                (o.veiculo_modelo || '').toLowerCase().includes(q),
              render: (o: any) => (
                <>
                  <div className="font-semibold">{o.veiculo_modelo || '—'}</div>
                  <div className="text-xs text-ink-500 font-mono">{o.veiculo_placa}</div>
                </>
              ),
            },
            {
              key: 'filial_id', label: 'Filial',
              accessor: (o: any) => o.filial_id, filter: true,
              render: (o: any) => <FilialChip filialId={o.filial_id} />,
            },
            {
              key: 'categoria', label: 'Categoria',
              accessor: (o: any) => o.categoria || '', filter: true,
              render: (o: any) => o.categoria
                ? <span className="pill pill-sky">{o.categoria}</span>
                : <span className="text-ink-400">—</span>,
            },
            {
              key: 'tipo_os', label: 'Tipo',
              accessor: (o: any) => o.tipo_os || '', filter: true,
              render: (o: any) => <TipoBadge tipo={o.tipo_os} />,
            },
            {
              key: 'status', label: 'Status',
              accessor: (o: any) => o.status, filter: true,
              render: (o: any) => <StatusBadge status={o.status} />,
            },
            {
              key: 'valor_total', label: 'Valor', align: 'right',
              accessor: (o: any) => Number(o.valor_total || 0), filter: true,
              cellClassName: 'font-mono num font-semibold',
              render: (o: any) => fmtBRL(o.valor_total),
            },
          ]}
        />
        <div className="px-5 py-3 border-t border-line bg-[#F8FBFD] flex items-center justify-between text-xs text-ink-500">
          <span>
            {data?.total
              ? `${offset + 1}–${Math.min(offset + limit, data.total)} de ${data.total} ordens`
              : '0 ordens'}
          </span>
          <div className="flex items-center gap-1">
            <button
              className="w-8 h-8 rounded-lg hover:bg-white flex items-center justify-center disabled:opacity-40"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - limit))}
            >
              <Icon name="chevron-left" size={14} />
            </button>
            <span className="px-3 font-mono font-semibold text-navy-800">
              {Math.floor(offset / limit) + 1}
            </span>
            <button
              className="w-8 h-8 rounded-lg hover:bg-white flex items-center justify-center disabled:opacity-40"
              disabled={offset + limit >= (data?.total || 0)}
              onClick={() => setOffset(offset + limit)}
            >
              <Icon name="chevron-right" size={14} />
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
