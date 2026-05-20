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
// Para reativar a tela de login: definir VITE_AUTO_LOGIN=false no build.
const AUTO_LOGIN_DEMO = true
const AUTO_LOGIN_EMAIL = 'hudson@napel.local'
const AUTO_LOGIN_SENHA = 'password123'

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
      const token = tokenStore.get()
      // Tenta usar token existente
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
      // Sem token válido — auto-login se demo
      if (AUTO_LOGIN_DEMO) {
        try {
          const { token: t, user: u } = await autoLogin()
          tokenStore.set(t)
          setUser(u)
        } catch (e) {
          console.error('Auto-login falhou:', e)
        }
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
    if (AUTO_LOGIN_DEMO) {
      // Re-faz auto-login transparente
      try {
        const { token: t, user: u } = await autoLogin()
        tokenStore.set(t)
        setUser(u)
      } catch {
        window.location.href = '/login'
      }
    } else {
      window.location.href = '/login'
    }
  }

  return <Ctx.Provider value={{ user, loading, login, logout, trocarUsuario }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
