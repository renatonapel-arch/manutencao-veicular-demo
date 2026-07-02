import { Link } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import { Icon, type IconName } from '../../components/Icons'

function nomeFilial(fid: number | null | undefined) {
  const map: Record<number, string> = {
    1: 'Maringá (100)', 2: 'Ponta Grossa (700)', 3: 'LEM (900)',
  }
  return fid ? map[fid] || `Filial ${fid}` : 'Todas as filiais'
}

type Item = { to?: string; onClick?: () => void; icon: IconName; label: string; danger?: boolean }

export default function MobilePerfilPage() {
  const { user, logout } = useAuth()
  if (!user) return null

  const iniciais = user.nome.split(' ').slice(0, 2).map(s => s[0]).join('').toUpperCase()

  const shortcuts: Item[] = [
    { to: '/oficinas', icon: 'store',    label: 'Catálogo de oficinas' },
    { to: '/planos',   icon: 'calendar', label: 'Planos preventivos' },
    { to: '/frota',    icon: 'car',      label: 'Frota (leitura)' },
  ]
  const conta: Item[] = [
    { to: '/login',    icon: 'refresh', label: 'Trocar de usuário' },
    { onClick: logout, icon: 'logout',  label: 'Sair', danger: true },
  ]

  return (
    <section className="px-4 py-5 space-y-4">
      {/* Card do usuário */}
      <div className="card-m text-center py-6">
        <div className="w-16 h-16 rounded-full bg-navy-800 text-white flex items-center justify-center text-xl font-bold mx-auto mb-3 font-mono">
          {iniciais}
        </div>
        <div className="display font-bold text-lg text-navy-900">{user.nome}</div>
        <div className="text-xs text-ink-500 font-mono">{user.email}</div>
        <div className="mt-3 flex justify-center gap-1.5 flex-wrap">
          <span className="pill pill-sky">{user.role}</span>
          <span className="pill pill-gray">{nomeFilial(user.filial_id)}</span>
        </div>
      </div>

      {/* Atalhos */}
      <div className="card-m p-0 overflow-hidden divide-y divide-line">
        {shortcuts.map(s => (
          <Link
            key={s.label}
            to={s.to!}
            className="flex items-center gap-3 px-4 py-3.5 active:bg-sky-bg/40 min-h-[52px]"
          >
            <span className="w-9 h-9 rounded-lg bg-sky-bg text-sky-700 flex items-center justify-center">
              <Icon name={s.icon} size={16} />
            </span>
            <span className="text-sm font-medium flex-1">{s.label}</span>
            <Icon name="chevron-right" size={14} />
          </Link>
        ))}
      </div>

      {/* Conta */}
      <div className="card-m p-0 overflow-hidden divide-y divide-line">
        {conta.map(s => {
          const inner = (
            <>
              <span className={`w-9 h-9 rounded-lg flex items-center justify-center ${s.danger ? 'bg-err-bg text-err-fg' : 'bg-sky-bg text-sky-700'}`}>
                <Icon name={s.icon} size={16} />
              </span>
              <span className={`text-sm font-medium flex-1 ${s.danger ? 'text-err-fg' : ''}`}>{s.label}</span>
              <Icon name="chevron-right" size={14} />
            </>
          )
          return s.onClick ? (
            <button key={s.label} onClick={s.onClick}
                    className="w-full flex items-center gap-3 px-4 py-3.5 active:bg-sky-bg/40 min-h-[52px]">
              {inner}
            </button>
          ) : (
            <Link key={s.label} to={s.to!}
                  className="flex items-center gap-3 px-4 py-3.5 active:bg-sky-bg/40 min-h-[52px]">
              {inner}
            </Link>
          )
        })}
      </div>

      <div className="text-[10px] text-ink-400 text-center pt-2">
        Clavis · Manutenção Veicular · demo
      </div>
    </section>
  )
}
