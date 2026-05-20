import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from './AuthContext'

const USUARIOS_DEMO = [
  { email: 'hudson@napel.local', role: 'admin' },
  { email: 'responsavel@maringa.local', role: 'filial_responsavel · 100' },
  { email: 'responsavel@pg.local', role: 'filial_responsavel · 700' },
  { email: 'responsavel@leme.local', role: 'filial_responsavel · 900' },
  { email: 'motorista@mobile.local', role: 'motorista' },
  { email: 'admin@oficinas.local', role: 'admin_oficinas' },
]

export default function LoginPage() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('hudson@napel.local')
  const [senha, setSenha] = useState('password123')
  const [erro, setErro] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErro('')
    setSubmitting(true)
    try {
      await login(email, senha)
      nav('/dashboard')
    } catch (err: any) {
      setErro(err.response?.data?.detail || 'Falha no login')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-noite p-4">
      <div className="bg-white rounded-xl shadow-lg w-full max-w-md p-8">
        <div className="text-center mb-6">
          <div className="text-xs tracking-widest text-ink-500">CLAVIS · NAPEL</div>
          <h1 className="text-2xl font-bold text-naval mt-1">Manutenção Veicular</h1>
          <div className="text-xs text-ink-500 mt-1">Demo VPS · DS Napel v1.0</div>
        </div>

        <form onSubmit={onSubmit} className="space-y-3">
          <div>
            <label className="text-[11px] text-ink-500">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-border-strong rounded text-sm font-mono"
              required
              autoFocus
            />
          </div>
          <div>
            <label className="text-[11px] text-ink-500">Senha</label>
            <input
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              className="w-full px-3 py-2 border border-border-strong rounded text-sm font-mono"
              required
            />
          </div>
          {erro && (
            <div className="bg-danger-bg border border-danger text-danger-fg text-sm rounded p-2">{erro}</div>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-naval text-white py-2.5 rounded font-medium hover:bg-noite disabled:opacity-50"
          >
            {submitting ? 'Entrando...' : 'Entrar'}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-border">
          <div className="text-[10px] uppercase tracking-wider text-ink-500 mb-2">Usuários seed (senha: password123)</div>
          <div className="space-y-1">
            {USUARIOS_DEMO.map(u => (
              <button
                key={u.email}
                type="button"
                onClick={() => { setEmail(u.email); setSenha('password123') }}
                className="w-full text-left text-xs px-2 py-1.5 rounded hover:bg-gelo flex justify-between"
              >
                <span className="font-mono text-ink-700">{u.email}</span>
                <span className="text-ink-500">{u.role}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
