import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Icon, type IconName } from './Icons'

const NAV: { to: string; icon: IconName; label: string; primary?: boolean }[] = [
  { to: '/dashboard', icon: 'grid',    label: 'Início' },
  { to: '/os',        icon: 'wrench',  label: 'OS' },
  { to: '/os/nova',   icon: 'plus',    label: 'Nova',  primary: true },
  { to: '/alertas',   icon: 'bell',    label: 'Alertas' },
  { to: '/perfil',    icon: 'user',    label: 'Perfil' },
]

const titulos: Record<string, string> = {
  '/dashboard':      'Minha frota',
  '/os':             'Ordens de Serviço',
  '/os/nova':        'Nova OS',
  '/planos':         'Preventivas',
  '/oficinas':       'Oficinas',
  '/alertas':        'Alertas',
  '/perfil':         'Perfil',
  '/checklist/novo': 'Novo checklist',
  '/checklists':     'Checklists',
  '/frota':          'Frota',
  '/aprovacoes':     'Aprovações',
}

export default function MobileLayout() {
  const { user } = useAuth()
  const loc = useLocation()
  const nav = useNavigate()

  let titulo = titulos[loc.pathname] || ''
  if (loc.pathname.startsWith('/os/') && loc.pathname !== '/os/nova') titulo = 'Detalhe da OS'
  if (loc.pathname.startsWith('/veiculo/')) titulo = 'Ficha do veículo'

  const podeVoltar = loc.pathname !== '/dashboard' && loc.pathname !== '/'

  return (
    <div className="flex flex-col h-[100svh] w-screen bg-page overflow-hidden">
      {/* Header navy */}
      <header
        className="bg-navy-950 text-white flex-shrink-0 sticky top-0 z-20"
        style={{ paddingTop: 'env(safe-area-inset-top)' }}
      >
        <div className="flex items-center px-3 py-3 gap-2">
          {podeVoltar ? (
            <button
              onClick={() => nav(-1)}
              className="w-10 h-10 -ml-1 flex items-center justify-center rounded-lg active:bg-white/10"
              aria-label="Voltar"
            >
              <Icon name="chevron-left" size={22} />
            </button>
          ) : (
            <div className="w-10 h-10 flex items-center justify-center rounded-lg bg-white/10 text-sky-300">
              <Icon name="wrench" size={18} />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div className="text-[10px] text-sky-300 uppercase tracking-wider">Clavis · Manutenção</div>
            <div className="display font-bold truncate text-[17px]">{titulo}</div>
          </div>
          {!podeVoltar && user && (
            <div className="text-right text-[10px] leading-tight max-w-[110px]">
              <div className="text-sky-300">Olá,</div>
              <div className="font-medium text-white truncate">{user.nome.split(' ')[0]}</div>
            </div>
          )}
        </div>
      </header>

      {/* Conteúdo */}
      <main className="flex-1 overflow-y-auto pb-[84px]">
        <Outlet />
      </main>

      {/* Bottom nav */}
      <nav
        className="bg-white border-t border-line flex items-stretch fixed bottom-0 left-0 right-0 z-20"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        {NAV.map(n => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.to === '/dashboard' || n.to === '/os/nova'}
            className={({ isActive }) =>
              `bnav-item ${n.primary ? 'primary' : ''} ${isActive ? 'active' : ''}`
            }
          >
            <Icon name={n.icon} size={n.primary ? 22 : 20} />
            <span className="text-[10px] font-semibold">{n.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
