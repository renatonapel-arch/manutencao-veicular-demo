import { createContext, useContext, useState, ReactNode } from 'react'

interface FilialCtx {
  filialId: number | null  // null = todas as filiais
  setFilialId: (id: number | null) => void
}

const Ctx = createContext<FilialCtx>({ filialId: null, setFilialId: () => {} })

export function FilialProvider({ children }: { children: ReactNode }) {
  const [filialId, setFilialId] = useState<number | null>(null)
  return <Ctx.Provider value={{ filialId, setFilialId }}>{children}</Ctx.Provider>
}

export const useFilial = () => useContext(Ctx)
