import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { fmtBRL, fmtData, FilialChip, StatusBadge, TipoBadge } from '../components/Badges'
import { useFilial } from '../context/FilialContext'

const STATUS_OPTS = [
  { v: '', l: 'Status: todos' },
  { v: 'rascunho', l: 'Rascunho' },
  { v: 'aberta', l: 'Aberta' },
  { v: 'em_triagem', l: 'Em triagem' },
  { v: 'aguardando_orcamento', l: 'Aguard. orçamento' },
  { v: 'aguardando_aprovacao', l: 'Aguard. aprovação' },
  { v: 'em_execucao', l: 'Em execução' },
  { v: 'aguardando_peca', l: 'Aguard. peça' },
  { v: 'encerrada', l: 'Encerrada' },
  { v: 'cancelada', l: 'Cancelada' },
]

const CATEGORIA_OPTS = [
  'Motor', 'Pneu', 'Pastilha / Lona', 'Relação', 'Lâmpadas',
  'Elétrica', 'Bateria', 'Empilhadeira', 'Embreagem', 'Outros',
]

export default function ListaOSPage() {
  const { filialId } = useFilial()
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [tipo, setTipo] = useState('')
  const [categoria, setCategoria] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 20

  const { data, isLoading } = useQuery({
    queryKey: ['os', { q, status, tipo, categoria, offset, filialId }],
    queryFn: () => {
      const params = new URLSearchParams()
      if (q) params.set('q', q)
      if (status) params.set('status', status)
      if (tipo) params.set('tipo', tipo)
      if (categoria) params.set('categoria', categoria)
      if (filialId) params.set('filial_id', String(filialId))
      params.set('limit', String(limit))
      params.set('offset', String(offset))
      return api.get('/ordem-servico?' + params).then(r => r.data)
    },
  })

  return (
    <section>
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="text-lg font-semibold text-naval">Ordens de Serviço</div>
          <div className="text-xs text-ink-500">{data?.total || 0} OS no total</div>
        </div>
        <Link to="/os/nova" className="bg-naval text-white px-3 py-1.5 rounded text-sm font-medium hover:bg-noite">+ Nova OS</Link>
      </div>

      <div className="bg-white border border-border rounded p-3 mb-3 flex gap-2 items-center flex-wrap text-xs">
        <input
          className="border border-border-strong rounded px-2 py-1 w-64"
          placeholder="🔍 Buscar descrição..."
          value={q}
          onChange={(e) => { setQ(e.target.value); setOffset(0) }}
        />
        <select className="border border-border-strong rounded px-2 py-1 bg-white"
                value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0) }}>
          {STATUS_OPTS.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
        </select>
        <select className="border border-border-strong rounded px-2 py-1 bg-white"
                value={tipo} onChange={(e) => { setTipo(e.target.value); setOffset(0) }}>
          <option value="">Tipo: todos</option>
          <option value="corretiva_manual">Corretiva</option>
          <option value="corretiva_checklist">Corretiva (chk)</option>
          <option value="preventiva_automatica">Preventiva</option>
          <option value="devolucao">Devolução</option>
          <option value="sinistro">Sinistro</option>
          <option value="recall">Recall</option>
        </select>
        <select className="border border-border-strong rounded px-2 py-1 bg-white"
                value={categoria} onChange={(e) => { setCategoria(e.target.value); setOffset(0) }}>
          <option value="">Categoria: todas</option>
          {CATEGORIA_OPTS.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <button className="text-ink-500 underline ml-auto" onClick={() => { setQ(''); setStatus(''); setTipo(''); setCategoria(''); setOffset(0) }}>Limpar</button>
      </div>

      <div className="bg-white border border-border rounded overflow-hidden">
        <table className="w-full text-[12px] dense">
          <thead className="text-ink-500 bg-ink-50 border-b border-border">
            <tr>
              <th className="text-left">Nº</th>
              <th className="text-left">Abertura</th>
              <th className="text-left">Veículo</th>
              <th className="text-left">Filial</th>
              <th className="text-left">Categoria</th>
              <th className="text-left">Tipo</th>
              <th className="text-left">Status</th>
              <th className="text-right">Valor</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={8} className="text-center text-ink-500 py-6">Carregando…</td></tr>}
            {!isLoading && (data?.data || []).length === 0 && (
              <tr><td colSpan={8} className="text-center text-ink-500 py-6">Nenhuma OS encontrada com os filtros aplicados.</td></tr>
            )}
            {(data?.data || []).map((os: any) => (
              <tr key={os.id} className="border-t border-border hover:bg-ink-50 cursor-pointer" onClick={() => location.assign(`/os/${os.id}`)}>
                <td><Link to={`/os/${os.id}`} className="font-mono text-naval">#{os.id}</Link></td>
                <td className="font-mono">{fmtData(os.data_abertura)}</td>
                <td><span className="font-mono">{os.veiculo_placa || `veic ${os.veiculo_id}`}</span> <span className="text-ink-500">· {os.veiculo_modelo || ''}</span></td>
                <td><FilialChip filialId={os.filial_id}/></td>
                <td>{os.categoria ? <span className="badge bg-info-bg text-info-fg">{os.categoria}</span> : <span className="text-ink-400">—</span>}</td>
                <td><TipoBadge tipo={os.tipo_os}/></td>
                <td><StatusBadge status={os.status}/></td>
                <td className="text-right font-medium font-mono">{fmtBRL(os.valor_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="bg-ink-50 px-3 py-2 text-[11px] text-ink-500 flex justify-between border-t border-border">
          <span>Mostrando {offset + 1}–{Math.min(offset + limit, data?.total || 0)} de {data?.total || 0}</span>
          <div className="flex gap-1">
            <button className="border border-border-strong bg-white rounded px-2 py-0.5"
                    disabled={offset === 0}
                    onClick={() => setOffset(Math.max(0, offset - limit))}>←</button>
            <span className="px-2 py-0.5 font-mono">{Math.floor(offset / limit) + 1}</span>
            <button className="border border-border-strong bg-white rounded px-2 py-0.5"
                    disabled={offset + limit >= (data?.total || 0)}
                    onClick={() => setOffset(offset + limit)}>→</button>
          </div>
        </div>
      </div>
    </section>
  )
}
