import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const FILIAIS = [
  { id: 0, label: 'Todas as filiais' },
  { id: 1, label: 'Maringá (100)' },
  { id: 2, label: 'Ponta Grossa (700)' },
  { id: 3, label: 'LEM (900)' },
]

const NAV = [
  { to: '/dashboard',   label: 'Dashboard',          icon: '📊' },
  { to: '/os',          label: 'Ordens de Serviço',  icon: '🔧' },
  { to: '/planos',      label: 'Planos preventivos', icon: '📅' },
  { to: '/oficinas',    label: 'Oficinas',           icon: '🏪' },
  { to: '/alertas',     label: 'Alertas WhatsApp',   icon: '📲' },
  { to: '/mobile',      label: 'PWA motorista',      icon: '📱' },
]

const breadcrumbs: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/os': 'Ordens de Serviço',
  '/planos': 'Planos preventivos',
  '/oficinas': 'Catálogo de oficinas',
  '/alertas': 'Alertas WhatsApp',
  '/mobile': 'PWA do motorista',
}

export default function Layout() {
  const { user, logout } = useAuth()
  const loc = useLocation()
  const breadcrumb = breadcrumbs[loc.pathname]
    || (loc.pathname.startsWith('/os/') ? 'Detalhe da OS' : '')
    || (loc.pathname.startsWith('/veiculo/') ? 'Timeline do veículo' : '')

  const initials = user?.nome.split(' ').slice(0, 2).map(s => s[0]).join('').toUpperCase() || 'U'

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 bg-noite text-ink-300 flex flex-col flex-shrink-0">
        <div className="p-3 border-b border-ink-700">
          <div className="text-[10px] tracking-widest text-ink-400 uppercase">CLAVIS</div>
          <div className="font-semibold text-white text-base">Napel</div>
        </div>
        <nav className="flex-1 overflow-y-auto p-2 text-[13px] space-y-0.5">
          <div className="px-2 py-1 text-[10px] tracking-widest text-ink-500 uppercase">Frota</div>
          <a className="nav-item block px-2 py-1.5 rounded cursor-default opacity-60">📋 Controle Patrimonial</a>
          <a className="nav-item block px-2 py-1.5 rounded cursor-default opacity-60">🛢️ Troca de Óleo</a>
          <div className="nav-item active block px-2 py-1.5 rounded">🔧 Manutenção Veicular</div>

          <div className="ml-3 mt-1 space-y-0.5 border-l border-ink-700 pl-2 text-[12px]">
            {NAV.map(n => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  `nav-sub block px-2 py-1 rounded cursor-pointer ${isActive ? 'active' : 'hover:text-white'}`
                }
              >
                {n.icon} {n.label}
              </NavLink>
            ))}
          </div>
        </nav>
        <div className="p-3 text-xs border-t border-ink-700 flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-naval text-white flex items-center justify-center text-[11px] font-medium">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-white truncate">{user?.nome}</div>
            <div className="text-ink-500 text-[10px] truncate">{user?.role} {user?.filial_id ? `· ${user.filial_id}` : ''}</div>
          </div>
          <button
            onClick={logout}
            className="text-ink-400 hover:text-white text-[11px] underline"
            title="Logout"
          >
            sair
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white border-b border-border px-5 py-2 flex justify-between items-center flex-shrink-0">
          <div className="text-[13px]">
            <span className="text-ink-400">Manutenção Veicular</span>
            <span className="mx-2 text-ink-300">/</span>
            <span className="font-medium text-ink-900">{breadcrumb}</span>
          </div>
          <div className="flex gap-2 items-center text-[13px]">
            <select className="border border-border rounded px-2 py-1 bg-white text-xs" disabled={user?.role !== 'admin'}>
              {FILIAIS.map(f => <option key={f.id}>{f.label}</option>)}
            </select>
            <span className="text-[10px] text-ink-500 font-mono">v0.1.0-demo</span>
          </div>
        </header>

        <div className="bg-gelo border-b border-border px-5 py-1.5 text-[11px] text-naval flex items-center gap-2">
          <span className="font-semibold">📖 Glossário:</span>
          <span><b>Ordem de Serviço</b> (UI) ≡ <span className="font-mono">os_manutencao</span> (schema)</span>
          <span className="text-ink-500">— não confundir com OS Pipefy legado</span>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
