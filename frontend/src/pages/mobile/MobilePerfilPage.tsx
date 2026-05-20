import { Link } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'

export default function MobilePerfilPage() {
  const { user, logout } = useAuth()
  if (!user) return null
  const initials = user.nome.split(' ').slice(0, 2).map(s => s[0]).join('').toUpperCase()
  const filialNome = user.filial_id === 1 ? 'Maringá (100)' : user.filial_id === 2 ? 'Ponta Grossa (700)' : user.filial_id === 3 ? 'LEM (900)' : 'Todas as filiais'

  return (
    <section className="px-4 py-6 space-y-4">
      <div className="bg-white border border-border rounded-lg p-5 text-center">
        <div className="w-20 h-20 rounded-full bg-naval text-white flex items-center justify-center text-2xl font-semibold mx-auto mb-3">
          {initials}
        </div>
        <div className="font-semibold text-lg">{user.nome}</div>
        <div className="text-sm text-ink-500 font-mono">{user.email}</div>
        <div className="mt-3 flex justify-center gap-2 flex-wrap">
          <span className="badge bg-naval text-white">{user.role}</span>
          <span className="badge bg-gelo text-naval">{filialNome}</span>
        </div>
      </div>

      <div className="bg-white border border-border rounded-lg divide-y divide-border">
        <Link to="/oficinas" className="flex items-center justify-between px-4 py-3 active:bg-ink-50">
          <span className="text-sm">🏪 Catálogo de oficinas</span>
          <span className="text-ink-400">›</span>
        </Link>
        <Link to="/planos" className="flex items-center justify-between px-4 py-3 active:bg-ink-50">
          <span className="text-sm">📅 Planos preventivos</span>
          <span className="text-ink-400">›</span>
        </Link>
        <Link to="/mobile" className="flex items-center justify-between px-4 py-3 active:bg-ink-50">
          <span className="text-sm">📱 Preview PWA (devs)</span>
          <span className="text-ink-400">›</span>
        </Link>
      </div>

      <div className="bg-white border border-border rounded-lg divide-y divide-border">
        <Link to="/login" className="flex items-center justify-between px-4 py-3 active:bg-ink-50">
          <span className="text-sm">🔄 Trocar usuário</span>
          <span className="text-ink-400">›</span>
        </Link>
        <button onClick={logout} className="w-full flex items-center justify-between px-4 py-3 active:bg-ink-50 text-danger-fg">
          <span className="text-sm">🚪 Sair</span>
          <span>›</span>
        </button>
      </div>

      <div className="text-[10px] text-ink-400 text-center pt-2">
        Clavis · Manutenção Veicular · demo VPS
      </div>
    </section>
  )
}
