import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'

interface FilialCtx {
  filialId: number | null  // null = todas as filiais
  setFilialId: (id: number | null) => void
}

const Ctx = createContext<FilialCtx>({ filialId: null, setFilialId: () => {} })

export function FilialProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [filialId, setFilialId] = useState<number | null>(null)

  // Quando troca de user, reseta o filtro
  useEffect(() => {
    setFilialId(null)
  }, [user?.id])

  return <Ctx.Provider value={{ filialId, setFilialId }}>{children}</Ctx.Provider>
}

export const useFilial = () => useContext(Ctx)
