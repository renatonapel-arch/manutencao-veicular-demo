import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { fmtBRL, fmtData, FilialChip, StatusBadge, TipoBadge } from '../../components/Badges'
import { useFilial } from '../../context/FilialContext'

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
      {/* CTA gigante */}
      <Link
        to="/os/nova"
        className="block w-full bg-naval text-white text-center rounded-xl py-5 font-semibold text-lg shadow-md hover:bg-noite transition-colors"
        style={{ minHeight: 60 }}
      >
        ➕ Nova OS
      </Link>

      {/* KPI cards (2 cols) */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white border border-border rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-ink-500">OS abertas</div>
          <div className="text-2xl font-bold mt-1 font-mono">{dash?.os_abertas ?? '—'}</div>
        </div>
        <div className="bg-white border border-border rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-ink-500">Atrasadas</div>
          <div className={`text-2xl font-bold mt-1 font-mono ${(dash?.os_atrasadas ?? 0) > 0 ? 'text-danger-fg' : ''}`}>
            {dash?.os_atrasadas ?? '—'}
          </div>
        </div>
        <div className="bg-white border border-border rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-ink-500">CPK acumulado</div>
          <div className="text-xl font-bold mt-1 font-mono text-naval">{dash ? fmtBRL(dash.cpk_acumulado_ytd) : '—'}</div>
        </div>
        <div className="bg-white border border-border rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-ink-500">Custo no mês</div>
          <div className="text-xl font-bold mt-1 font-mono">{dash ? fmtBRL(dash.custo_total_mes) : '—'}</div>
        </div>
      </div>

      {dash?.os_atrasadas > 0 && (
        <div className="bg-warn-bg border border-warn rounded-lg p-3 text-[13px] text-warn-fg flex items-start gap-2">
          <span className="text-lg">⚠️</span>
          <div className="flex-1">
            <b>{dash.os_atrasadas} OS atrasadas</b> abertas há mais de 5 dias.
            <Link to="/os?status=aberta" className="block mt-1 text-naval underline">Ver lista →</Link>
          </div>
        </div>
      )}

      {/* Últimas OS */}
      <div>
        <div className="flex justify-between items-center mb-2 px-1">
          <div className="font-semibold text-naval">Últimas OS {filialId ? '· filial atual' : ''}</div>
          <Link to="/os" className="text-xs text-naval underline">ver todas</Link>
        </div>
        <div className="space-y-2">
          {(ultimas?.data || []).map((os: any) => (
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
              <div className="font-mono text-sm">{os.veiculo_placa || `veic ${os.veiculo_id}`} <span className="text-ink-500">· {os.veiculo_modelo}</span></div>
              <div className="flex justify-between items-center mt-1 text-[11px] text-ink-500">
                <span>{os.descricao_problema?.slice(0, 50) || '—'}</span>
                <span className="font-mono">{fmtData(os.data_abertura)}</span>
              </div>
            </Link>
          ))}
          {(!ultimas || ultimas.data.length === 0) && (
            <div className="bg-white border border-border rounded-lg p-6 text-center text-ink-500 text-sm">
              Sem OS recentes
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
