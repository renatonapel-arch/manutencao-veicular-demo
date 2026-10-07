import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from './AuthContext'

const CLAVIS_URL = 'https://clavis.napel.com.br/patrimonio/manutencao'

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
  // Formulário de demo só se o backend liberar o login local (dev/demo). null =
  // ainda perguntando; erro = trata como desligado (fecha por padrão).
  const [loginLocal, setLoginLocal] = useState<boolean | null>(null)

  useEffect(() => {
    api.get('/auth/config').then((r) => setLoginLocal(!!r.data.local_login)).catch(() => setLoginLocal(false))
  }, [])

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

  if (loginLocal === null) return <div className="min-h-screen bg-nv-bg" />

  if (!loginLocal) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-nv-bg p-4">
        <div className="bg-nv-surface rounded-xl shadow-lg w-full max-w-md p-8 text-center space-y-4">
          <div className="text-xs tracking-widest text-nv-soft">CLAVIS · NAPEL</div>
          <h1 className="text-2xl font-bold text-nv-ink">Manutenção Veicular</h1>
          <p className="text-sm text-nv-soft">
            O acesso é pelo Clavis. Abra o Clavis, entre com o seu usuário e vá em Patrimônio › Manutenção Veicular.
          </p>
          <a href={CLAVIS_URL} target="_blank" rel="noreferrer"
             className="inline-block w-full bg-nv-primary text-nv-bg py-2.5 rounded font-medium hover:bg-nv-primary-hover">
            Abrir o Clavis
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-nv-bg p-4">
      <div className="bg-nv-surface rounded-xl shadow-lg w-full max-w-md p-8">
        <div className="text-center mb-6">
          <div className="text-xs tracking-widest text-nv-soft">CLAVIS · NAPEL</div>
          <h1 className="text-2xl font-bold text-nv-ink mt-1">Manutenção Veicular</h1>
          <div className="text-xs text-nv-soft mt-1">Demo VPS · DS Napel v1.0</div>
        </div>

        <form onSubmit={onSubmit} className="space-y-3">
          <div>
            <label className="text-[11px] text-nv-soft">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-nv-border-strong rounded text-sm font-mono"
              required
              autoFocus
            />
          </div>
          <div>
            <label className="text-[11px] text-nv-soft">Senha</label>
            <input
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              className="w-full px-3 py-2 border border-nv-border-strong rounded text-sm font-mono"
              required
            />
          </div>
          {erro && (
            <div className="bg-nv-danger-bg border border-nv-danger text-nv-danger-text text-sm rounded p-2">{erro}</div>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-nv-primary text-nv-bg py-2.5 rounded font-medium hover:bg-nv-primary-hover disabled:bg-nv-surface-2 disabled:text-nv-soft"
          >
            {submitting ? 'Entrando...' : 'Entrar'}
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-nv-border-strong">
          <div className="text-[10px] uppercase tracking-wider text-nv-soft mb-2">Usuários seed (senha: password123)</div>
          <div className="space-y-1">
            {USUARIOS_DEMO.map(u => (
              <button
                key={u.email}
                type="button"
                onClick={() => { setEmail(u.email); setSenha('password123') }}
                className="w-full text-left text-xs px-2 py-1.5 rounded hover:bg-nv-surface-2 flex justify-between"
              >
                <span className="font-mono text-nv-soft">{u.email}</span>
                <span className="text-nv-soft">{u.role}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
