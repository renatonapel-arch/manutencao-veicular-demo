import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
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
}

const Ctx = createContext<AuthCtx>({} as AuthCtx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = tokenStore.get()
    if (!token) { setLoading(false); return }
    api.get<User>('/auth/me')
      .then((r) => setUser(r.data))
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false))
  }, [])

  const login = async (email: string, senha: string) => {
    const r = await api.post('/auth/login', { email, senha })
    tokenStore.set(r.data.access_token)
    setUser(r.data.user)
  }

  const logout = async () => {
    try { await api.post('/auth/logout') } catch {}
    tokenStore.clear()
    setUser(null)
    window.location.href = '/login'
  }

  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
