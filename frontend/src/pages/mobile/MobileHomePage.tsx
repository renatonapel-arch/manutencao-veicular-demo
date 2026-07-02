import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { fmtBRL, fmtData, FilialChip, StatusBadge } from '../../components/Badges'
import { Icon } from '../../components/Icons'
import { useFilial } from '../../context/FilialContext'

/** Home mobile — CTA + 4 KPIs em grid 2×2 + últimas OS. */
export default function MobileHomePage() {
  const { user } = useAuth()
  const { filialId } = useFilial()
  const qs = filialId ? `?filial_id=${filialId}` : ''

  const { data: dash } = useQuery({
    queryKey: ['m-dashboard', filialId],
    queryFn: () => api.get(`/dashboard${qs}`).then(r => r.data),
  })
  const { data: ultimas } = useQuery({
    queryKey: ['m-ultimas-os', filialId],
    queryFn: () => api.get(`/ordem-servico?limit=5${filialId ? `&filial_id=${filialId}` : ''}`).then(r => r.data),
  })

  return (
    <section className="px-4 py-4 space-y-4">
      {/* CTA principal */}
      <Link
        to="/os/nova"
        className="btn btn-primary btn-lg w-full justify-center text-base"
      >
        <Icon name="plus" size={18} /> Nova OS
      </Link>

      {/* KPIs 2×2 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="card-m">
          <div className="kpi-label">OS abertas</div>
          <div className="text-2xl font-bold mt-2 font-mono num text-navy-900">{dash?.os_abertas ?? '—'}</div>
        </div>
        <div className="card-m">
          <div className="kpi-label">Atrasadas</div>
          <div className={`text-2xl font-bold mt-2 font-mono num ${(dash?.os_atrasadas ?? 0) > 0 ? 'text-err-fg' : 'text-navy-900'}`}>
            {dash?.os_atrasadas ?? '—'}
          </div>
        </div>
        <div className="card-m">
          <div className="kpi-label">CPK</div>
          <div className="text-lg font-bold mt-2 font-mono num text-navy-900">
            {dash ? fmtBRL(dash.cpk_acumulado_ytd) : '—'}
            <span className="text-xs text-ink-400 font-medium">/km</span>
          </div>
        </div>
        <div className="card-m">
          <div className="kpi-label">Custo do mês</div>
          <div className="text-lg font-bold mt-2 font-mono num text-navy-900">
            {dash ? fmtBRL(dash.custo_total_mes) : '—'}
          </div>
        </div>
      </div>

      {(dash?.os_atrasadas ?? 0) > 0 && (
        <Link to="/os?status=aberta" className="flex items-start gap-2 bg-warn-bg border border-warn rounded-xl p-3 text-warn-fg active:opacity-80">
          <Icon name="alert" size={18} />
          <div className="flex-1 text-sm">
            <b>{dash!.os_atrasadas} OS atrasadas</b> abertas há mais de 5 dias.
            <span className="block text-xs text-navy-800 font-semibold mt-0.5">Ver lista →</span>
          </div>
        </Link>
      )}

      {/* Últimas OS */}
      <div>
        <div className="flex items-center justify-between mb-2 px-1">
          <div className="display font-bold text-navy-900 text-sm">Últimas OS</div>
          <Link to="/os" className="text-xs text-sky-700 font-semibold flex items-center gap-1">
            ver todas <Icon name="chevron-right" size={12} />
          </Link>
        </div>

        <div className="space-y-2">
          {(ultimas?.data || []).map((os: any) => (
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
              <div className="flex justify-between items-center mt-1 text-[11px] text-ink-500 gap-2">
                <span className="truncate flex-1">{os.descricao_problema || '—'}</span>
                <span className="font-mono shrink-0">{fmtData(os.data_abertura)}</span>
              </div>
            </Link>
          ))}
          {(!ultimas || ultimas.data.length === 0) && (
            <div className="card-m empty py-10">
              <Icon name="wrench" size={36} />
              <div className="text-sm">Sem OS recentes.</div>
            </div>
          )}
        </div>
      </div>

      <div className="text-[10px] text-ink-400 text-center pt-2">
        {user?.role === 'admin' ? 'Vendo todas as filiais' : `Filial ${user?.filial_id} · RBAC ativo`}
      </div>
    </section>
  )
}
