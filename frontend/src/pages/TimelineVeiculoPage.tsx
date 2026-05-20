import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { fmtBRL, fmtDataHora, FilialChip, SourceBadge, StatusBadge, TipoBadge } from '../components/Badges'

const SOURCE_BORDERS: Record<string, string> = {
  os_manutencao: 'border-naval',
  troca_oleo: 'border-ink-400',
  checklist_v2: 'border-success',
  patrimonial: 'border-ink-500',
}

const SOURCE_EMOJI: Record<string, string> = {
  os_manutencao: '🔧',
  troca_oleo: '🛢️',
  checklist_v2: '✅',
  patrimonial: '📋',
}

export default function TimelineVeiculoPage() {
  const { placa } = useParams()
  const { data: veiculos } = useQuery({
    queryKey: ['veiculos-list'],
    queryFn: () => api.get('/veiculos').then(r => r.data),
  })
  const veic = (veiculos || []).find((v: any) => v.placa === placa)
  const { data: timeline } = useQuery({
    queryKey: ['timeline', veic?.id],
    queryFn: () => api.get(`/veiculos/${veic.id}/timeline`).then(r => r.data),
    enabled: !!veic?.id,
  })

  if (!veic) {
    return (
      <section>
        <div className="text-lg font-semibold text-naval mb-3">Selecione um veículo</div>
        <div className="bg-white border border-border rounded p-3">
          <div className="grid grid-cols-3 gap-2">
            {(veiculos || []).map((v: any) => (
              <Link key={v.id} to={`/veiculo/${v.placa}`} className="border border-border rounded p-3 hover:bg-gelo">
                <div className="font-mono text-naval font-semibold">{v.placa}</div>
                <div className="text-xs text-ink-500">{v.modelo}</div>
                <div className="text-[11px] mt-1"><FilialChip filialId={v.filial_id}/></div>
              </Link>
            ))}
          </div>
        </div>
      </section>
    )
  }

  return (
    <section>
      <div className="bg-white border border-border rounded p-3 mb-3">
        <div className="flex justify-between items-start gap-4">
          <div className="flex items-center gap-3">
            <div className="text-3xl">{veic.tipo === 'moto' ? '🏍️' : veic.tipo === 'empilhadeira' ? '🚜' : '🚗'}</div>
            <div>
              <div className="flex items-center gap-2">
                <div className="font-mono text-lg font-semibold text-naval">{veic.placa}</div>
                <FilialChip filialId={veic.filial_id}/>
              </div>
              <div className="text-sm text-ink-700">{veic.modelo} {veic.ano ? `· ${veic.ano}` : ''}</div>
              <div className="text-[11px] text-ink-400">Responsável: {veic.responsavel_atual || '—'}</div>
            </div>
          </div>
        </div>
        {timeline && (
          <div className="grid grid-cols-5 gap-3 mt-3 pt-3 border-t border-border">
            <div><div className="text-[10px] uppercase text-ink-500">KM atual</div><div className="text-base font-semibold font-mono">{veic.km_atual.toLocaleString('pt-BR')}</div></div>
            <div><div className="text-[10px] uppercase text-ink-500">CRLV</div><div className="text-base font-semibold text-success-fg font-mono">{veic.vencimento_crlv || '—'}</div></div>
            <div><div className="text-[10px] uppercase text-ink-500">Total OS</div><div className="text-base font-semibold font-mono">{timeline.total_os}</div></div>
            <div><div className="text-[10px] uppercase text-ink-500">Custo 12m</div><div className="text-base font-semibold font-mono">{fmtBRL(timeline.custo_12m)}</div></div>
            <div><div className="text-[10px] uppercase text-ink-500">CPK</div><div className="text-base font-semibold text-warn-fg font-mono">{fmtBRL(timeline.cpk)}/km</div></div>
          </div>
        )}
      </div>

      <div className="bg-white border border-border rounded p-3">
        <div className="text-[13px] font-medium text-naval mb-2">Histórico unificado · 3 fontes</div>
        {timeline?.warnings?.length > 0 && (
          <div className="mb-2 space-y-1">
            {timeline.warnings.map((w: string, i: number) => (
              <div key={i} className="text-[11px] text-warn-fg bg-warn-bg/50 border border-warn rounded px-2 py-1">⚠ {w}</div>
            ))}
          </div>
        )}
        <div className="space-y-2">
          {(timeline?.items || []).map((item: any, i: number) => (
            <div key={i} className={`flex gap-3 p-2 rounded hover:bg-ink-50 border-l-4 ${SOURCE_BORDERS[item.tipo] || 'border-ink-300'}`}>
              <div className="text-2xl">{SOURCE_EMOJI[item.tipo] || '•'}</div>
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <SourceBadge source={item.tipo}/>
                  {item.subtipo && <TipoBadge tipo={item.subtipo}/>}
                  {item.status && item.tipo === 'os_manutencao' && <StatusBadge status={item.status}/>}
                  {item.ref_id && <span className="font-mono text-[11px] text-ink-500">#{item.ref_id}</span>}
                </div>
                <div className="font-medium text-[13px] mt-0.5">{item.titulo}</div>
                <div className="text-[11px] text-ink-500">{item.descricao || ''}</div>
              </div>
              <div className="text-right">
                <div className="text-[10px] text-ink-500 font-mono">{fmtDataHora(item.data)}</div>
                {item.valor && <div className="font-semibold text-[13px] font-mono">{fmtBRL(item.valor)}</div>}
                {item.economia && <div className="text-[10px] text-success-fg">💡 economia {fmtBRL(item.economia)}</div>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
