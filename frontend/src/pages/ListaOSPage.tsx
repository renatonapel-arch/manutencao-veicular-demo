import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { fmtBRL, fmtData, FilialChip, StatusBadge, TipoBadge } from '../components/Badges'
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
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[760px]">
            <thead>
              <tr className="text-[11px] uppercase tracking-wider text-ink-500 bg-[#F8FBFD]">
                <th className="text-left px-5 py-3 font-semibold">OS</th>
                <th className="text-left py-3 font-semibold">Aberta em</th>
                <th className="text-left py-3 font-semibold">Veículo</th>
                <th className="text-left py-3 font-semibold">Filial</th>
                <th className="text-left py-3 font-semibold">Categoria</th>
                <th className="text-left py-3 font-semibold">Tipo</th>
                <th className="text-left py-3 font-semibold">Status</th>
                <th className="text-right px-5 py-3 font-semibold">Valor</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={8} className="empty">Carregando…</td></tr>
              )}
              {!isLoading && !(data?.data || []).length && (
                <tr>
                  <td colSpan={8} className="empty py-14">
                    <Icon name="wrench" size={44} />
                    <div className="text-sm">
                      Nenhuma OS com esses filtros.{' '}
                      <Link to="/os/nova" className="text-sky-700 font-semibold">Abrir uma ordem</Link>.
                    </div>
                  </td>
                </tr>
              )}
              {(data?.data || []).map((os: any) => (
                <tr
                  key={os.id}
                  className="row border-t border-line cursor-pointer"
                  onClick={() => location.assign(`/os/${os.id}`)}
                >
                  <td className="px-5 py-3.5 font-mono font-semibold text-navy-800">#{os.id}</td>
                  <td className="py-3.5 font-mono text-xs text-ink-500">{fmtData(os.data_abertura)}</td>
                  <td className="py-3.5">
                    <div className="font-semibold">{os.veiculo_modelo || '—'}</div>
                    <div className="text-xs text-ink-500 font-mono">{os.veiculo_placa}</div>
                  </td>
                  <td className="py-3.5"><FilialChip filialId={os.filial_id} /></td>
                  <td className="py-3.5">
                    {os.categoria
                      ? <span className="pill pill-sky">{os.categoria}</span>
                      : <span className="text-ink-400">—</span>}
                  </td>
                  <td className="py-3.5"><TipoBadge tipo={os.tipo_os} /></td>
                  <td className="py-3.5"><StatusBadge status={os.status} /></td>
                  <td className="px-5 py-3.5 text-right font-mono num font-semibold">{fmtBRL(os.valor_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
