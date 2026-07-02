import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, tokenStore } from '../api/client'

export interface User {
  id: number
  email: string
  nome: string
  role: string
  filial_id: number | null
  telefone?: string
}

interface AuthCtx {
  user: User | null
  loading: boolean
  login: (email: string, senha: string) => Promise<void>
  logout: () => Promise<void>
  trocarUsuario: (email: string) => Promise<void>
}

const Ctx = createContext<AuthCtx>({} as AuthCtx)

// Modo demo: auto-login transparente como Hudson (admin global).
// SÓ ativa em modo standalone (fora do Clavis embarcado). Se estamos dentro
// de um iframe do Clavis, o SSO manda — nunca voltamos pra auto-login local
// porque isso confundiria "está logado como hudson@napel.local" quando o
// user real é renato@napel.com.br via SSO.
const AUTO_LOGIN_EMAIL = 'hudson@napel.local'
const AUTO_LOGIN_SENHA = 'password123'

function isEmbedded(): boolean {
  try { return window.self !== window.top } catch { return true }
}

async function autoLogin(): Promise<{ token: string; user: User }> {
  const r = await api.post('/auth/login', { email: AUTO_LOGIN_EMAIL, senha: AUTO_LOGIN_SENHA })
  return { token: r.data.access_token, user: r.data.user }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const boot = async () => {
      // 1) Captura JWT do hash fragment (redundância com main.tsx pra
      //    cobrir race condition onde ssoBootstrap perdeu o hash)
      const hash = window.location.hash || ''
      if (hash.includes('access_token=')) {
        const params = new URLSearchParams(hash.replace(/^#/, ''))
        const tok = params.get('access_token')
        if (tok) {
          tokenStore.set(tok)
          history.replaceState(null, '', window.location.pathname + window.location.search)
        }
      }

      // 2) Tenta usar token existente
      const token = tokenStore.get()
      if (token) {
        try {
          const r = await api.get<User>('/auth/me')
          setUser(r.data)
          setLoading(false)
          return
        } catch {
          tokenStore.clear()
        }
      }

      // 3) Embarcado no Clavis mas sem token/SSO válido → deixa cair na
      //    tela de erro específica em vez de tela de login (que confunde
      //    quem já está logado no Clavis).
      if (isEmbedded()) {
        setLoading(false)
        return
      }

      // 4) Standalone (demo VPS): auto-login como Hudson pra pilotagem sem senha
      try {
        const { token: t, user: u } = await autoLogin()
        tokenStore.set(t)
        setUser(u)
      } catch (e) {
        console.error('Auto-login falhou:', e)
      }
      setLoading(false)
    }
    boot()
  }, [])

  const login = async (email: string, senha: string) => {
    const r = await api.post('/auth/login', { email, senha })
    tokenStore.set(r.data.access_token)
    setUser(r.data.user)
    // Limpa cache do React Query — RBAC pode trazer dados diferentes pro novo user
    qc.clear()
  }

  // Troca rápida de usuário (pra testar RBAC) — sem precisar passar pela tela de login
  const trocarUsuario = async (email: string) => {
    await login(email, AUTO_LOGIN_SENHA)
  }

  const logout = async () => {
    try { await api.post('/auth/logout') } catch {}
    tokenStore.clear()
    setUser(null)
    qc.clear()
    if (isEmbedded()) {
      // Dentro do Clavis: não force login local — só reload pra pegar novo JWT
      window.location.reload()
      return
    }
    // Standalone (demo): auto-login como Hudson
    try {
      const { token: t, user: u } = await autoLogin()
      tokenStore.set(t)
      setUser(u)
    } catch {
      window.location.href = '/login'
    }
  }

  return <Ctx.Provider value={{ user, loading, login, logout, trocarUsuario }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
