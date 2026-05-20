import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const NAV = [
  { to: '/dashboard', icon: '🏠', label: 'Home' },
  { to: '/os',        icon: '🔧', label: 'OS' },
  { to: '/os/nova',   icon: '➕', label: 'Nova',  primary: true },
  { to: '/alertas',   icon: '📲', label: 'Alertas' },
  { to: '/perfil',    icon: '👤', label: 'Perfil' },
]

const titulos: Record<string, string> = {
  '/dashboard': 'Minha frota',
  '/os': 'Ordens de Serviço',
  '/os/nova': 'Nova OS',
  '/planos': 'Preventivas',
  '/oficinas': 'Oficinas',
  '/alertas': 'Alertas',
  '/perfil': 'Perfil',
}

export default function MobileLayout() {
  const { user } = useAuth()
  const loc = useLocation()
  const nav = useNavigate()

  let titulo = titulos[loc.pathname] || ''
  if (loc.pathname.startsWith('/os/') && loc.pathname !== '/os/nova') titulo = 'Detalhe da OS'
  if (loc.pathname.startsWith('/veiculo/')) titulo = 'Veículo'

  const podeVoltar = loc.pathname !== '/dashboard' && loc.pathname !== '/'

  return (
    <div className="flex flex-col h-screen w-screen bg-page-bg overflow-hidden">
      {/* Header naval */}
      <header className="bg-naval text-white flex-shrink-0 sticky top-0 z-20">
        <div className="flex items-center px-3 py-3 gap-3" style={{ paddingTop: 'max(0.75rem, env(safe-area-inset-top))' }}>
          {podeVoltar ? (
            <button onClick={() => nav(-1)} className="text-2xl leading-none w-9 h-9 -ml-1 flex items-center justify-center">←</button>
          ) : (
            <div className="w-9 h-9 flex items-center justify-center text-lg">🔧</div>
          )}
          <div className="flex-1 min-w-0">
            <div className="text-[10px] text-ceu-claro uppercase tracking-wider truncate">Clavis · Manutenção</div>
            <div className="font-semibold truncate">{titulo}</div>
          </div>
          {!podeVoltar && (
            <div className="text-right text-[10px] leading-tight">
              <div className="text-ceu-claro">Olá,</div>
              <div className="font-medium text-white truncate max-w-[100px]">{user?.nome.split(' ')[0]}</div>
            </div>
          )}
        </div>
      </header>

      {/* Conteúdo */}
      <main className="flex-1 overflow-y-auto pb-20">
        <Outlet />
      </main>

      {/* Bottom nav */}
      <nav
        className="bg-white border-t border-border flex items-stretch flex-shrink-0 fixed bottom-0 left-0 right-0 z-20"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        {NAV.map(n => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.to === '/dashboard' || n.to === '/os/nova'}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center py-2 gap-0.5 transition-colors ${
                n.primary
                  ? isActive
                    ? 'text-white'
                    : 'text-white'
                  : isActive
                    ? 'text-naval'
                    : 'text-ink-400'
              }`
            }
            style={n.primary ? { background: '#113C58' } : {}}
          >
            <span className={n.primary ? 'text-2xl' : 'text-xl'}>{n.icon}</span>
            <span className={`text-[10px] font-medium ${n.primary ? 'text-white' : ''}`}>{n.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
