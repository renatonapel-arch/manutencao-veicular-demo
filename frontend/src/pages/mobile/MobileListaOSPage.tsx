import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { fmtBRL, fmtData, FilialChip, StatusBadge } from '../../components/Badges'
import { Icon } from '../../components/Icons'
import { useFilial } from '../../context/FilialContext'

const STATUS = [
  { v: '',                       l: 'Todas' },
  { v: 'aberta',                 l: 'Abertas' },
  { v: 'em_triagem',             l: 'Triagem' },
  { v: 'aguardando_orcamento',   l: 'Aguard. orçamento' },
  { v: 'aguardando_aprovacao',   l: 'Aguard. aprovação' },
  { v: 'em_execucao',            l: 'Em execução' },
  { v: 'aguardando_peca',        l: 'Aguard. peça' },
  { v: 'encerrada',              l: 'Encerradas' },
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
      {/* Chips de filtro (scroll horizontal sem barra) */}
      <div className="bg-white border-b border-line px-3 py-2.5 sticky top-0 z-10">
        <div className="chip-scroll flex gap-2 -mx-1 px-1">
          {STATUS.map(s => (
            <button
              key={s.v}
              onClick={() => setStatusF(s.v)}
              className={`shrink-0 px-3.5 py-2 rounded-full text-xs font-semibold border transition-colors ${
                statusF === s.v
                  ? 'bg-navy-900 text-white border-navy-900'
                  : 'bg-white text-ink-700 border-line'
              }`}
            >
              {s.l}
            </button>
          ))}
        </div>
        <div className="text-[11px] text-ink-500 mt-1.5 px-1">
          {data?.total ?? '—'} OS{statusF ? ` · filtro ativo` : ''}
        </div>
      </div>

      {/* Cards */}
      <div className="flex-1 px-3 py-3 overflow-y-auto">
        <div className="space-y-2">
          {(data?.data || []).map((os: any) => (
            <Link
              key={os.id}
              to={`/os/${os.id}`}
              className="block card-m active:bg-sky-bg/40"
            >
              <div className="flex justify-between items-start gap-2 mb-1.5">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="font-mono text-navy-800 font-semibold text-sm">#{os.id}</span>
                  <StatusBadge status={os.status} />
                  <FilialChip filialId={os.filial_id} />
                </div>
                <div className="font-semibold font-mono num text-sm text-navy-900 shrink-0">
                  {fmtBRL(os.valor_total)}
                </div>
              </div>
              <div className="font-semibold text-sm truncate">
                {os.veiculo_placa} <span className="text-ink-500 font-normal">· {os.veiculo_modelo || '—'}</span>
              </div>
              {os.oficina_nome && (
                <div className="text-[11px] text-ink-500 mt-1 flex items-center gap-1">
                  <Icon name="store" size={11} /> {os.oficina_nome}
                </div>
              )}
              <div className="flex justify-between items-center mt-1.5 text-[11px] text-ink-500 gap-2">
                <span className="truncate flex-1">{os.descricao_problema || '—'}</span>
                <span className="font-mono shrink-0">{fmtData(os.data_abertura)}</span>
              </div>
            </Link>
          ))}
          {(!data || data.data.length === 0) && (
            <div className="card-m empty py-14">
              <Icon name="wrench" size={40} />
              <div className="text-sm">Nenhuma OS com esse filtro.</div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
