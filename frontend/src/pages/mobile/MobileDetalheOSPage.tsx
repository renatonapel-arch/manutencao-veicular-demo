import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { api } from '../../api/client'
import { fmtBRL, fmtDataHora, FilialChip, StatusBadge, TipoBadge } from '../../components/Badges'

export default function MobileDetalheOSPage() {
  const { id } = useParams()
  const qc = useQueryClient()

  const { data: os, isLoading } = useQuery({
    queryKey: ['os', id],
    queryFn: () => api.get(`/ordem-servico/${id}`).then(r => r.data),
  })

  const patch = useMutation({
    mutationFn: (payload: any) => api.patch(`/ordem-servico/${id}`, payload).then(r => r.data),
    onSuccess: () => qc.invalidateQueries(),
    onError: (e: any) => alert(e.response?.data?.detail || 'Erro'),
  })

  const upload = useMutation({
    mutationFn: ({ tipo, file }: { tipo: string, file: File }) => {
      const f = new FormData()
      f.append('tipo', tipo)
      f.append('arquivo', file)
      return api.post(`/upload/os/${id}/anexos`, f, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }).then(r => r.data)
    },
    onSuccess: () => qc.invalidateQueries(),
    onError: (e: any) => alert(e.response?.data?.detail || 'Erro upload'),
  })

  if (isLoading || !os) return <div className="p-6 text-ink-500 text-center">Carregando OS…</div>

  const temNF = (os.anexos || []).some((a: any) => a.tipo === 'nf')
  const temFoto = (os.anexos || []).some((a: any) => a.tipo.startsWith('foto'))
  const podeEncerrar = temNF && temFoto && (os.itens || []).length > 0

  return (
    <section className="px-3 py-3 space-y-3">
      {/* Header da OS */}
      <div className="bg-white border border-border rounded-lg p-3">
        <div className="flex items-center gap-2 flex-wrap mb-2">
          <span className="font-mono text-lg font-semibold text-naval">OS #{os.id}</span>
          <StatusBadge status={os.status}/>
          <TipoBadge tipo={os.tipo_os}/>
        </div>
        <div className="font-mono text-base font-medium">{os.veiculo?.placa} · {os.veiculo?.modelo}</div>
        <div className="text-xs text-ink-500 mt-1 flex items-center gap-2 flex-wrap">
          <FilialChip filialId={os.filial_id}/>
          <span>KM {os.km_veiculo.toLocaleString('pt-BR')}</span>
          <span>· {fmtDataHora(os.data_abertura)}</span>
        </div>
      </div>

      {/* Descrição */}
      {os.descricao_problema && (
        <div className="bg-white border border-border rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-ink-500 mb-1">Problema</div>
          <div className="text-[13px]">{os.descricao_problema}</div>
        </div>
      )}

      {/* Oficina */}
      {os.oficina && (
        <div className="bg-white border border-border rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-ink-500 mb-1">Oficina</div>
          <div className="font-medium">{os.oficina.nome}</div>
          {os.oficina.cidade && <div className="text-xs text-ink-500">{os.oficina.cidade}/{os.oficina.uf}</div>}
        </div>
      )}

      {/* Itens */}
      <div className="bg-white border border-border rounded-lg overflow-hidden">
        <div className="px-3 py-2 border-b border-border bg-ink-50 text-[10px] uppercase tracking-wider text-ink-500">
          Itens · {(os.itens || []).length}
        </div>
        {(os.itens || []).map((it: any) => (
          <div key={it.id} className="px-3 py-2 border-b border-border last:border-b-0 flex justify-between items-start gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="badge bg-info-bg text-info-fg">{it.tipo_item}</span>
                {it.sige_sku && <span className="font-mono text-[10px] text-ink-500">{it.sige_sku}</span>}
              </div>
              <div className="text-sm mt-0.5">{it.descricao}</div>
              {it.economia_napel && <div className="text-[10px] text-success-fg">💡 −{fmtBRL(it.economia_napel)} vs mercado</div>}
            </div>
            <div className="text-right flex-shrink-0">
              <div className="text-[10px] text-ink-500 font-mono">{Number(it.quantidade)}×</div>
              <div className="font-mono font-medium">{fmtBRL(it.subtotal)}</div>
            </div>
          </div>
        ))}
        <div className="px-3 py-2 bg-ink-50 flex justify-between items-center font-semibold border-t border-border">
          <span className="text-xs uppercase text-ink-500">Total</span>
          <span className="font-mono text-base text-naval">{fmtBRL(os.valor_total)}</span>
        </div>
      </div>

      {/* Anexos */}
      <div className="bg-white border border-border rounded-lg p-3">
        <div className="text-[10px] uppercase tracking-wider text-ink-500 mb-2">Anexos</div>

        {/* Fotos */}
        <div className="mb-3">
          <div className="text-xs font-medium mb-1.5">
            📷 Fotos <span className={temFoto ? 'text-success-fg' : 'text-ink-400'}>({(os.anexos || []).filter((a: any) => a.tipo.startsWith('foto')).length})</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {(os.anexos || []).filter((a: any) => a.tipo.startsWith('foto')).map((a: any) => (
              <div key={a.id} className="aspect-square bg-ink-200 rounded-lg flex items-center justify-center text-3xl">📷</div>
            ))}
            <label className="aspect-square border-2 border-dashed border-ink-300 rounded-lg flex flex-col items-center justify-center text-ink-500 text-[10px] active:bg-gelo" style={{ minHeight: 80 }}>
              <span className="text-2xl">📷</span>Câmera
              <input
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate({ tipo: 'foto_hodometro', file: f }) }}
              />
            </label>
          </div>
        </div>

        {/* NF */}
        <div>
          <div className={`text-xs font-medium mb-1.5 ${temNF ? 'text-success-fg' : 'text-danger-fg'}`}>
            📄 NF <span className="font-normal">{temNF ? '· anexada ✓' : '· obrigatória pra encerrar'}</span>
          </div>
          <label className={`block w-full border-2 border-dashed rounded-lg py-5 flex flex-col items-center cursor-pointer active:bg-gelo ${temNF ? 'border-success bg-success-bg/20' : 'border-danger bg-danger-bg/20'}`}>
            <span className="text-3xl">📄</span>
            <span className="font-medium text-sm mt-1">{temNF ? 'NF anexada' : 'Anexar NF'}</span>
            <span className="text-[10px] text-ink-400">PDF · JPG · ≤20MB</span>
            <input
              type="file"
              accept="image/*,application/pdf"
              className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate({ tipo: 'nf', file: f }) }}
            />
          </label>
        </div>

        {upload.isPending && <div className="text-xs text-warn-fg mt-2 text-center">⏳ Enviando…</div>}
      </div>

      {/* Validação encerrar */}
      <div className="bg-white border border-border rounded-lg p-3">
        <div className="text-[10px] uppercase tracking-wider text-ink-500 mb-2">Pra encerrar</div>
        <div className="space-y-1.5 text-sm">
          <div className={`flex items-center gap-2 ${temFoto ? 'text-success-fg' : 'text-ink-400'}`}>{temFoto ? '✓' : '✗'} Pelo menos 1 foto</div>
          <div className={`flex items-center gap-2 ${temNF ? 'text-success-fg' : 'text-danger-fg'}`}>{temNF ? '✓' : '✗'} NF anexada</div>
          <div className={`flex items-center gap-2 ${(os.itens || []).length > 0 ? 'text-success-fg' : 'text-danger-fg'}`}>{(os.itens || []).length > 0 ? '✓' : '✗'} Pelo menos 1 item</div>
        </div>
      </div>

      {/* Ação principal */}
      <div className="space-y-2 pb-4">
        {os.status === 'aguardando_anexos' && podeEncerrar && (
          <button
            onClick={() => patch.mutate({ status: 'em_execucao' })}
            className="w-full bg-warn text-white py-3 rounded-lg font-semibold active:opacity-90"
            style={{ minHeight: 48 }}
          >
            ▶ Marcar em execução
          </button>
        )}
        {os.status === 'em_execucao' && podeEncerrar && (
          <button
            onClick={() => patch.mutate({ status: 'encerrada' })}
            className="w-full bg-success text-white py-3 rounded-lg font-semibold active:opacity-90"
            style={{ minHeight: 48 }}
          >
            🔒 Encerrar OS
          </button>
        )}
        {os.status === 'rascunho' && (
          <button
            onClick={() => patch.mutate({ status: 'aberta' })}
            className="w-full bg-naval text-white py-3 rounded-lg font-semibold active:opacity-90"
            style={{ minHeight: 48 }}
          >
            📤 Enviar OS
          </button>
        )}
      </div>
    </section>
  )
}
