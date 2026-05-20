import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { fmtBRL, fmtData, FilialChip, StatusBadge } from '../../components/Badges'
import { useFilial } from '../../context/FilialContext'

const STATUS = [
  { v: '', l: 'Todas' },
  { v: 'aberta', l: 'Abertas' },
  { v: 'aguardando_anexos', l: 'Aguard. NF' },
  { v: 'em_execucao', l: 'Em execução' },
  { v: 'encerrada', l: 'Encerradas' },
]

export default function MobileListaOSPage() {
  const { filialId } = useFilial()
  const [statusF, setStatusF] = useState('')

  const { data } = useQuery({
    queryKey: ['m-os', statusF, filialId],
    queryFn: () => {
      const p = new URLSearchParams()
      if (statusF) p.set('status', statusF)
      if (filialId) p.set('filial_id', String(filialId))
      p.set('limit', '30')
      return api.get('/ordem-servico?' + p).then(r => r.data)
    },
  })

  return (
    <section className="flex flex-col h-full">
      {/* Filtros chips */}
      <div className="bg-white border-b border-border px-3 py-2 sticky top-0 z-10">
        <div className="flex gap-2 overflow-x-auto -mx-1 px-1">
          {STATUS.map(s => (
            <button
              key={s.v}
              onClick={() => setStatusF(s.v)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-medium border ${
                statusF === s.v
                  ? 'bg-naval text-white border-naval'
                  : 'bg-white text-ink-700 border-border'
              }`}
            >
              {s.l}
            </button>
          ))}
        </div>
        <div className="text-[10px] text-ink-500 mt-2 px-1">
          {data?.total ?? '—'} OS{statusF ? ` · filtro: ${STATUS.find(s => s.v === statusF)?.l}` : ''}
        </div>
      </div>

      {/* Cards */}
      <div className="flex-1 px-3 py-3 space-y-2 overflow-y-auto">
        {(data?.data || []).map((os: any) => (
          <Link
            key={os.id}
            to={`/os/${os.id}`}
            className="block bg-white border border-border rounded-lg p-3 active:bg-ink-50"
          >
            <div className="flex justify-between items-start gap-2 mb-1">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="font-mono text-naval font-semibold">#{os.id}</span>
                <StatusBadge status={os.status}/>
                <FilialChip filialId={os.filial_id}/>
              </div>
              <div className="font-semibold font-mono text-sm">{fmtBRL(os.valor_total)}</div>
            </div>
            <div className="font-mono text-sm">{os.veiculo_placa || `veic ${os.veiculo_id}`} <span className="text-ink-500 font-sans">· {os.veiculo_modelo}</span></div>
            {os.oficina_nome && <div className="text-[11px] text-ink-500">🏪 {os.oficina_nome}</div>}
            <div className="flex justify-between items-center mt-1.5 text-[11px] text-ink-500">
              <span className="truncate flex-1 pr-2">{os.descricao_problema || '—'}</span>
              <span className="font-mono flex-shrink-0">{fmtData(os.data_abertura)}</span>
            </div>
          </Link>
        ))}
        {(!data || data.data.length === 0) && (
          <div className="bg-white border border-border rounded-lg p-8 text-center text-ink-500 text-sm">
            Nenhuma OS com esse filtro
          </div>
        )}
      </div>
    </section>
  )
}
