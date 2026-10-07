import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { fmtBRL, fmtDataHora, FilialChip, SourceBadge, StatusBadge, TipoBadge } from '../components/Badges'
import { Icon, type IconName } from '../components/Icons'

const SOURCE_STYLE: Record<string, { icon: IconName; wrap: string }> = {
  os_manutencao: { icon: 'wrench',       wrap: 'bg-nv-surface-2 text-nv-primary' },
  troca_oleo:    { icon: 'thermometer',  wrap: 'bg-nv-surface-2 text-nv-primary' },
  checklist_v2:  { icon: 'check-square', wrap: 'bg-nv-success-bg text-nv-success' },
  patrimonial:   { icon: 'doc',          wrap: 'bg-nv-bg text-nv-soft' },
}

function VehicleIcon({ tipo }: { tipo?: string }) {
  const map: Record<string, IconName> = { moto: 'car', empilhadeira: 'car' }
  return (
    <div className="w-12 h-12 rounded-xl bg-nv-surface-2 text-nv-primary flex items-center justify-center">
      <Icon name={map[tipo || ''] || 'car'} size={22} />
    </div>
  )
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
        <div className="display text-lg font-bold text-nv-ink mb-3">Selecione um veículo</div>
        <div className="card p-5">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {(veiculos || []).map((v: any) => (
              <Link key={v.id} to={`/veiculo/${v.placa}`}
                    className="border border-nv-border rounded-xl p-3 hover:border-nv-primary hover:bg-nv-surface-2 transition-colors">
                <div className="font-mono text-nv-primary font-semibold">{v.placa}</div>
                <div className="text-xs text-nv-soft truncate">{v.modelo}</div>
                <div className="mt-2"><FilialChip filialId={v.filial_id}/></div>
              </Link>
            ))}
          </div>
        </div>
      </section>
    )
  }

  return (
    <section>
      <div className="card p-5 mb-5">
        <div className="flex items-start gap-4">
          <VehicleIcon tipo={veic.tipo} />
          <div className="flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <div className="display font-mono text-xl font-bold text-nv-ink">{veic.placa}</div>
              <FilialChip filialId={veic.filial_id}/>
              {veic.tipo && <span className="pill pill-sky">{veic.tipo}</span>}
            </div>
            <div className="text-sm text-nv-soft mt-0.5">
              {veic.modelo} {veic.ano ? `· ${veic.ano}` : ''}
            </div>
            <div className="text-xs text-nv-soft mt-0.5">
              Responsável: {veic.responsavel_atual || '—'}
            </div>
          </div>
        </div>

        {timeline && (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mt-5 pt-5 border-t border-nv-border">
            <div>
              <div className="kpi-label">KM atual</div>
              <div className="text-lg font-bold font-mono num text-nv-ink mt-1">
                {(veic.km_atual || 0).toLocaleString('pt-BR')}
              </div>
            </div>
            <div>
              <div className="kpi-label">CRLV</div>
              <div className="text-lg font-bold font-mono num text-nv-success mt-1">{veic.vencimento_crlv || '—'}</div>
            </div>
            <div>
              <div className="kpi-label">Total OS</div>
              <div className="text-lg font-bold font-mono num text-nv-ink mt-1">{timeline.total_os}</div>
            </div>
            <div>
              <div className="kpi-label">Custo 12m</div>
              <div className="text-lg font-bold font-mono num text-nv-ink mt-1">{fmtBRL(timeline.custo_12m)}</div>
            </div>
            <div>
              <div className="kpi-label">CPK</div>
              <div className="text-lg font-bold font-mono num text-nv-warn mt-1">{fmtBRL(timeline.cpk)}/km</div>
            </div>
          </div>
        )}
      </div>

      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="display text-base font-bold text-nv-ink">Histórico unificado</h3>
            <div className="text-xs text-nv-soft mt-0.5">3 fontes · manutenção, trocas de óleo, checklists</div>
          </div>
          {timeline?.items?.length ? (
            <span className="pill pill-sky">{timeline.items.length} eventos</span>
          ) : null}
        </div>

        {timeline?.warnings?.length > 0 && (
          <div className="mb-4 space-y-1.5">
            {timeline.warnings.map((w: string, i: number) => (
              <div key={i} className="text-xs text-nv-warn bg-nv-warn-bg border border-nv-warn rounded-lg px-3 py-1.5 flex items-center gap-2">
                <Icon name="alert" size={14} /> {w}
              </div>
            ))}
          </div>
        )}

        {!(timeline?.items || []).length && (
          <div className="empty py-14">
            <Icon name="clock" size={44} />
            <div className="text-sm">Sem eventos registrados neste veículo.</div>
          </div>
        )}

        <div className="tl">
          {(timeline?.items || []).map((item: any, i: number) => {
            const s = SOURCE_STYLE[item.tipo] || SOURCE_STYLE.patrimonial
            return (
              <div key={i} className="tl-row">
                <div className={`tl-icon ${s.wrap}`}>
                  <Icon name={s.icon} size={16} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <SourceBadge source={item.tipo}/>
                    {item.subtipo && <TipoBadge tipo={item.subtipo}/>}
                    {item.status && item.tipo === 'os_manutencao' && <StatusBadge status={item.status}/>}
                    {item.ref_id && <span className="font-mono text-[11px] text-nv-soft">#{item.ref_id}</span>}
                  </div>
                  <div className="font-semibold text-sm mt-1 truncate">{item.titulo}</div>
                  {item.descricao && (
                    <div className="text-xs text-nv-soft truncate">{item.descricao}</div>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <div className="text-[11px] text-nv-soft font-mono">{fmtDataHora(item.data)}</div>
                  {item.valor && <div className="font-mono num font-bold text-sm text-nv-ink">{fmtBRL(item.valor)}</div>}
                  {item.economia && (
                    <div className="text-[11px] text-nv-success flex items-center gap-1 justify-end">
                      <Icon name="check" size={11}/> economia {fmtBRL(item.economia)}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
