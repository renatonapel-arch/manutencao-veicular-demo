import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useFilial } from '../context/FilialContext'
import { Icon } from './Icons'

const FILIAIS = [
  { id: 0, label: 'Todas as filiais' },
  { id: 1, label: 'Maringá (100)' },
  { id: 2, label: 'Ponta Grossa (200)' },
  { id: 3, label: 'Londrina (300)' },
  { id: 4, label: 'Andaluzia (700)' },
]

type NavItem = { to: string; label: string; icon: string; badge?: number }
type NavGroup = { group: string; items: NavItem[] }

/** Sidebar do mockup aprovado — grupos Operação/Cadastros/Comunicação/Dev. */
function useNav(): NavGroup[] {
  const { data } = useQuery({
    queryKey: ['aprovacoes-badge'],
    queryFn: () =>
      api.get('/ordem-servico?status=aguardando_aprovacao&limit=1').then(r => r.data.total ?? 0),
    refetchInterval: 60_000,
  })
  const nAprov: number = data || 0
  return [
    {
      group: 'Operação',
      items: [
        { to: '/dashboard', label: 'Visão geral', icon: 'grid' },
        { to: '/os', label: 'Ordens de serviço', icon: 'wrench' },
        { to: '/aprovacoes', label: 'Aprovações', icon: 'check-square', badge: nAprov },
        { to: '/planos', label: 'Preventivas', icon: 'calendar' },
      ],
    },
    {
      group: 'Cadastros',
      items: [
        { to: '/oficinas', label: 'Oficinas', icon: 'store' },
        { to: '/frota', label: 'Frota (leitura)', icon: 'car' },
      ],
    },
    {
      group: 'Comunicação',
      items: [{ to: '/alertas', label: 'Alertas', icon: 'bell' }],
    },
    {
      group: 'Dev',
      items: [{ to: '/mobile', label: 'Preview mobile', icon: 'phone' }],
    },
  ]
}

const TITULOS: Record<string, [string, string]> = {
  '/dashboard': ['Visão geral', 'Manutenção da frota'],
  '/os': ['Operação › Ordens', 'Ordens de serviço'],
  '/os/nova': ['Operação › Ordens › Nova', 'Abrir nova ordem'],
  '/aprovacoes': ['Operação › Aprovações', 'Aprovações pendentes'],
  '/planos': ['Operação › Preventivas', 'Manutenção preventiva'],
  '/oficinas': ['Cadastros › Oficinas', 'Catálogo de oficinas'],
  '/frota': ['Cadastros › Frota', 'Frota (somente leitura)'],
  '/alertas': ['Comunicação › Alertas', 'Alertas'],
  '/mobile': ['Dev › Preview', 'PWA do motorista'],
}

function tituloDa(pathname: string): [string, string] {
  if (TITULOS[pathname]) return TITULOS[pathname]
  if (pathname.startsWith('/os/')) return ['Operação › Ordens', 'Detalhe da ordem']
  if (pathname.startsWith('/veiculo/')) return ['Cadastros › Frota › Ficha', 'Ficha do veículo']
  return ['', 'Manutenção Veicular']
}

export default function Layout() {
  const { user, logout } = useAuth()
  const { filialId, setFilialId } = useFilial()
  const loc = useLocation()
  const nav = useNav()
  const [crumb, titulo] = tituloDa(loc.pathname)

  const inicial = (user?.nome || 'U').charAt(0).toUpperCase()

  return (
    <div className="flex h-screen overflow-hidden bg-page-bg">
      {/* ============ SIDEBAR (mockup: navy-950, grupos) ============ */}
      <aside className="w-56 bg-navy-950 flex flex-col flex-shrink-0">
        <div className="px-5 py-5 border-b border-navy-800">
          <div className="text-[10px] tracking-[.22em] text-sky-500/70 font-semibold">CLAVIS</div>
          <div className="display text-white text-lg font-extrabold mt-0.5">Manutenção</div>
          <div className="text-sky-400/80 text-xs">Napel · frota</div>
        </div>

        <nav className="flex-1 overflow-y-auto p-3">
          {nav.map(g => (
            <div key={g.group}>
              <div className="side-group">{g.group}</div>
              {g.items.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => `side-item ${isActive ? 'active' : ''}`}
                >
                  <Icon name={item.icon} size={15} />
                  {item.label}
                  {item.badge ? <span className="side-badge">{item.badge}</span> : null}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="p-3 border-t border-navy-800 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-sky-500/20 text-white flex items-center justify-center text-xs font-bold">
            {inicial}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-white text-sm font-semibold truncate">{user?.nome}</div>
            <div className="text-sky-400/70 text-[11px] truncate">{user?.role}</div>
          </div>
          <button onClick={logout} className="text-sky-400/70 hover:text-white" title="Sair">
            <Icon name="logout" size={16} />
          </button>
        </div>
      </aside>

      {/* ============ MAIN ============ */}
      <main className="flex-1 overflow-auto">
        <header className="sticky top-0 z-10 bg-white/85 backdrop-blur border-b border-line px-8 py-4 flex items-center justify-between gap-4">
          <div className="min-w-0">
            <div className="text-xs text-ink-500 truncate">{crumb}</div>
            <h1 className="display text-2xl font-extrabold text-navy-900 mt-0.5 truncate">{titulo}</h1>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <select
              className="select"
              style={{ width: 'auto', paddingRight: '2.2rem' }}
              disabled={user?.role !== 'admin'}
              value={filialId ?? 0}
              onChange={e => setFilialId(Number(e.target.value) || null)}
              title={user?.role !== 'admin' ? 'Travado na sua filial (RBAC)' : 'Filtra todas as telas'}
            >
              {FILIAIS.map(f => (
                <option key={f.id} value={f.id}>{f.label}</option>
              ))}
            </select>
          </div>
        </header>

        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
