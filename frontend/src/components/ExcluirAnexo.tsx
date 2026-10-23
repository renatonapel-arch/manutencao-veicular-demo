import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

/**
 * Excluir foto/NF anexada por engano (#0269). Confirmação NA PRÓPRIA tela: window.confirm()
 * é bloqueado dentro do iframe do Clavis. Exclusão suave no servidor (arquivo fica guardado,
 * registro no histórico); OS encerrada/cancelada é recusada lá.
 */
export function useExcluirAnexo(osId: string | number | undefined) {
  const qc = useQueryClient()
  const [alvo, setAlvo] = useState<{ id: number; tipo: string } | null>(null)
  const mut = useMutation({
    mutationFn: (anexoId: number) => api.delete(`/upload/os/${osId}/anexos/${anexoId}`).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries(); setAlvo(null) },
  })
  const nome = alvo?.tipo === 'nf' ? 'a NF' : 'a foto'

  const modal = alvo && (
    <div className="fixed inset-0 bg-[rgba(2,15,26,.7)] flex items-center justify-center z-50 p-4"
         onClick={(e) => { if (e.target === e.currentTarget && !mut.isPending) setAlvo(null) }}>
      <div className="bg-nv-surface ring-1 ring-nv-border-strong rounded-lg max-w-sm w-full p-5 space-y-3">
        <div className="text-lg font-semibold text-nv-primary">Excluir {nome}?</div>
        <div className="text-[13px] text-nv-soft">
          Ela some desta OS. Fica registrado no histórico quem excluiu.
        </div>
        {mut.isError && (
          <div className="text-xs text-nv-danger-text bg-nv-danger-bg rounded px-3 py-2">
            {(mut.error as any)?.response?.data?.detail || 'Erro ao excluir. Tente de novo.'}
          </div>
        )}
        <div className="flex gap-2 justify-end pt-1">
          <button type="button" onClick={() => setAlvo(null)} disabled={mut.isPending}
                  className="border border-nv-border-strong px-3 py-1.5 rounded text-sm">Voltar</button>
          <button type="button" onClick={() => mut.mutate(alvo.id)} disabled={mut.isPending}
                  className="bg-nv-danger text-nv-bg px-3 py-1.5 rounded text-sm font-medium disabled:opacity-50">
            {mut.isPending ? 'Excluindo…' : 'Excluir'}
          </button>
        </div>
      </div>
    </div>
  )

  return { pedir: (a: { id: number; tipo: string }) => { mut.reset(); setAlvo(a) }, modal }
}
