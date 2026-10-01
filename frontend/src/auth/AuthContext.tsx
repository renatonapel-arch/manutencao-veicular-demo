import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, isEmbedded, tokenStore } from '../api/client'

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

      // 3) Sem sessão válida: acabou o auto-login como Hudson (admin sem senha —
      //    achado de segurança de 01/10/2026). Embarcado no Clavis cai no card de
      //    "Sessão expirada"; fora dele o RequireAuth manda pra /login, que só
      //    mostra o formulário se o backend liberar o login local.
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
    window.location.href = '/login'
  }

  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
