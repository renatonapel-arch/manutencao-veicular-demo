import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { fmtBRL, fmtData, FilialChip } from '../components/Badges'
import { Icon } from '../components/Icons'
import { useFilial } from '../context/FilialContext'

/** Fila do gestor — OS em aguardando_aprovacao, com Aprovar / Reprovar / 2º orçamento.
 *  Card no formato do mockup aprovado. */
export default function AprovacoesPage() {
  const { filialId } = useFilial()
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['aprovacoes', filialId],
    queryFn: () => {
      const p = new URLSearchParams({ status: 'aguardando_aprovacao', limit: '50' })
      if (filialId) p.set('filial_id', String(filialId))
      return api.get('/ordem-servico?' + p).then(r => r.data)
    },
  })

  const acaoMut = useMutation({
    mutationFn: ({ id, acao, motivo }: { id: number; acao: string; motivo?: string }) => {
      const qs = motivo ? `?motivo=${encodeURIComponent(motivo)}` : ''
      return api.post(`/ordem-servico/${id}/${acao}${qs}`).then(r => r.data)
    },
    onSuccess: () => qc.invalidateQueries(),
    onError: (e: any) => alert(e.response?.data?.detail || 'Erro'),
  })

  const executar = (id: number, acao: string, precisaMotivo = false) => {
    let motivo: string | undefined
    if (precisaMotivo) {
      motivo = window.prompt('Motivo (obrigatório):') || undefined
      if (!motivo) return
    }
    acaoMut.mutate({ id, acao, motivo })
  }

  const fila = data?.data || []

  if (isLoading) return <div className="text-ink-500 text-sm">Carregando…</div>

  return (
    <section>
      {fila.length === 0 ? (
        <div className="card p-6">
          <div className="empty py-14">
            <Icon name="check-square" size={44} />
            <div className="text-sm">Fila vazia. Nada esperando aprovação.</div>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {fila.map((os: any) => (
            <div key={os.id} className="card p-5">
              <div className="border border-warn/20 bg-warn-bg/30 rounded-xl p-5 flex flex-wrap items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-warn/20 flex items-center justify-center text-warn-fg">
                  <Icon name="alert" size={22} />
                </div>
                <div className="flex-1 min-w-[240px]">
                  <div className="flex items-center gap-2 flex-wrap">
                    <a href={`/os/${os.id}`} className="font-mono font-semibold text-navy-800 hover:underline">OS #{os.id}</a>
                    <span className="pill pill-warn">Aguardando aprovação</span>
                    {os.categoria && <span className="pill pill-sky">{os.categoria}</span>}
                    <FilialChip filialId={os.filial_id} />
                  </div>
                  <div className="text-sm mt-1">
                    <span className="font-semibold">{os.veiculo_modelo || '—'}</span>
                    <span className="text-ink-500 font-mono"> · {os.veiculo_placa}</span>
                    <span className="text-ink-500"> · {os.descricao_problema || 'sem descrição'}</span>
                  </div>
                  <div className="text-xs text-ink-500 mt-1">
                    aberta em {fmtData(os.data_abertura)} · oficina: {os.oficina_nome || '—'}
                  </div>
                </div>
                <div className="text-right">
                  <div className="display text-lg font-extrabold text-navy-900 num">{fmtBRL(os.valor_total)}</div>
                  <div className="flex gap-2 mt-2 flex-wrap justify-end">
                    <button className="btn btn-err" disabled={acaoMut.isPending}
                            onClick={() => executar(os.id, 'reprovar', true)}>
                      Reprovar
                    </button>
                    <button className="btn btn-outline" disabled={acaoMut.isPending}
                            onClick={() => executar(os.id, 'pedir-2o-orcamento', true)}>
                      Pedir 2º orçamento
                    </button>
                    <button className="btn btn-ok" disabled={acaoMut.isPending}
                            onClick={() => executar(os.id, 'aprovar')}>
                      <Icon name="check" size={14} /> Aprovar
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
