import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { api } from '../../api/client'
import { fmtBRL, fmtDataHora, FilialChip, StatusBadge, TipoBadge } from '../../components/Badges'

/**
 * Detalhe mobile — mostra a OS e os botões da PRÓXIMA transição válida.
 * Cada transição = POST /ordem-servico/{id}/{acao} (não PATCH).
 */

const PROX_ACOES: Record<string, { acao: string; label: string; cor: string }> = {
  rascunho:              { acao: 'abrir',              label: 'Enviar OS',              cor: 'bg-naval text-white' },
  aberta:                { acao: 'triagem',            label: 'Iniciar triagem',        cor: 'bg-naval text-white' },
  em_triagem:            { acao: 'enviar-orcamento',   label: 'Pedir orçamento',        cor: 'bg-naval text-white' },
  aguardando_orcamento:  { acao: 'submeter-orcamento', label: 'Submeter orçamento',     cor: 'bg-naval text-white' },
  aguardando_aprovacao:  { acao: 'aprovar',            label: 'Aprovar orçamento',      cor: 'bg-success text-white' },
  em_execucao:           { acao: 'encerrar',           label: 'Encerrar OS',            cor: 'bg-success text-white' },
  aguardando_peca:       { acao: 'retomar-execucao',   label: 'Peça chegou · retomar',  cor: 'bg-naval text-white' },
}

export default function MobileDetalheOSPage() {
  const { id } = useParams()
  const qc = useQueryClient()

  const { data: os, isLoading } = useQuery({
    queryKey: ['os', id],
    queryFn: () => api.get(`/ordem-servico/${id}`).then(r => r.data),
  })

  const transicionar = useMutation({
    mutationFn: (acao: string) =>
      api.post(`/ordem-servico/${id}/${acao}`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries(),
    onError: (e: any) => alert(e.response?.data?.detail || 'Erro na transição'),
  })

  const upload = useMutation({
    mutationFn: ({ tipo, file }: { tipo: string; file: File }) => {
      const f = new FormData()
      f.append('tipo', tipo)
      f.append('arquivo', file)
      return api.post(`/upload/os/${id}/anexos`, f, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then(r => r.data)
    },
    onSuccess: () => qc.invalidateQueries(),
    onError: (e: any) => alert(e.response?.data?.detail || 'Erro upload'),
  })

  if (isLoading || !os) return <div className="p-6 text-ink-500 text-center">Carregando OS…</div>

  const temNF   = (os.anexos || []).some((a: any) => a.tipo === 'nf')
  const temFoto = (os.anexos || []).some((a: any) => a.tipo?.startsWith('foto'))
  const temItem = (os.itens || []).length > 0
  const podeAcao = PROX_ACOES[os.status]

  // Regras de bloqueio: encerrar precisa foto + NF; abrir precisa nada
  const bloqueado = (() => {
    if (os.status === 'em_execucao' && (!temNF || !temFoto)) return 'Anexe foto e NF antes de encerrar.'
    return null
  })()

  return (
    <section className="px-3 py-3 space-y-3">
      {/* Header */}
      <div className="bg-white border border-line rounded-lg p-3">
        <div className="flex items-center gap-2 flex-wrap mb-2">
          <span className="font-mono text-lg font-semibold text-navy-800">OS #{os.id}</span>
          <StatusBadge status={os.status} />
          <TipoBadge tipo={os.tipo_os} />
        </div>
        <div className="font-mono text-base font-medium">
          {os.veiculo?.placa} · {os.veiculo?.modelo}
        </div>
        <div className="text-xs text-ink-500 mt-1 flex items-center gap-2 flex-wrap">
          <FilialChip filialId={os.filial_id} />
          <span>KM {os.km_veiculo?.toLocaleString('pt-BR')}</span>
          <span>· {fmtDataHora(os.data_abertura)}</span>
        </div>
      </div>

      {/* Descrição */}
      {os.descricao_problema && (
        <div className="bg-white border border-line rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-ink-500 mb-1">Problema</div>
          <div className="text-[13px]">{os.descricao_problema}</div>
        </div>
      )}

      {/* Oficina */}
      {os.oficina && (
        <div className="bg-white border border-line rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-ink-500 mb-1">Oficina</div>
          <div className="font-medium">{os.oficina.nome}</div>
          {os.oficina.cidade && <div className="text-xs text-ink-500">{os.oficina.cidade}</div>}
        </div>
      )}

      {/* Itens */}
      <div className="bg-white border border-line rounded-lg overflow-hidden">
        <div className="px-3 py-2 border-b border-line bg-sky-bg text-[10px] uppercase tracking-wider text-ink-500">
          Itens · {(os.itens || []).length}
        </div>
        {(os.itens || []).map((it: any) => (
          <div key={it.id} className="px-3 py-2 border-b border-line last:border-b-0 flex justify-between items-start gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="pill pill-sky">{it.tipo_item}</span>
              </div>
              <div className="text-sm mt-0.5">{it.descricao}</div>
            </div>
            <div className="text-right flex-shrink-0">
              <div className="text-[10px] text-ink-500 font-mono">{Number(it.quantidade)}×</div>
              <div className="font-mono font-medium num">{fmtBRL(it.subtotal)}</div>
            </div>
          </div>
        ))}
        <div className="px-3 py-2 bg-sky-bg flex justify-between items-center font-semibold border-t border-line">
          <span className="text-xs uppercase text-ink-500">Total</span>
          <span className="font-mono text-base text-navy-800 num">{fmtBRL(os.valor_total)}</span>
        </div>
      </div>

      {/* Anexos — sempre disponíveis após a criação */}
      <div className="bg-white border border-line rounded-lg p-3">
        <div className="text-[10px] uppercase tracking-wider text-ink-500 mb-2">Anexos</div>

        {/* Fotos */}
        <div className="mb-3">
          <div className="text-xs font-medium mb-1.5">
            Fotos <span className={temFoto ? 'text-ok-fg' : 'text-ink-400'}>
              ({(os.anexos || []).filter((a: any) => a.tipo?.startsWith('foto')).length})
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {(os.anexos || []).filter((a: any) => a.tipo?.startsWith('foto')).map((a: any) => (
              <div key={a.id} className="aspect-square bg-sky-bg rounded-lg flex items-center justify-center text-navy-800 text-xs">
                foto #{a.id}
              </div>
            ))}
            <label className="aspect-square border-2 border-dashed border-line rounded-lg flex flex-col items-center justify-center text-ink-500 text-[11px] active:bg-sky-bg cursor-pointer" style={{ minHeight: 80 }}>
              <span className="font-semibold text-sm text-navy-800">+ Câmera</span>
              <input
                type="file" accept="image/*" capture="environment"
                className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate({ tipo: 'foto_problema', file: f }) }}
              />
            </label>
          </div>
        </div>

        {/* NF */}
        <div>
          <div className={`text-xs font-medium mb-1.5 ${temNF ? 'text-ok-fg' : 'text-ink-500'}`}>
            NF {temNF ? '· anexada' : '· obrigatória pra encerrar'}
          </div>
          <label className={`block w-full border-2 border-dashed rounded-lg py-5 flex flex-col items-center cursor-pointer active:bg-sky-bg ${temNF ? 'border-ok bg-ok-bg/20' : 'border-line'}`}>
            <span className="font-medium text-sm text-navy-800">{temNF ? 'NF anexada' : '+ Anexar NF'}</span>
            <span className="text-[10px] text-ink-400">PDF · JPG · ≤20MB</span>
            <input
              type="file" accept="image/*,application/pdf"
              className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate({ tipo: 'nf', file: f }) }}
            />
          </label>
        </div>

        {upload.isPending && <div className="text-xs text-warn-fg mt-2 text-center">Enviando…</div>}
      </div>

      {/* Ação principal (só se houver próxima transição válida) */}
      {podeAcao && (
        <div className="pb-4 space-y-2">
          {bloqueado && (
            <div className="text-xs text-err-fg bg-err-bg border border-err rounded-lg px-3 py-2 text-center">
              {bloqueado}
            </div>
          )}
          <button
            onClick={() => transicionar.mutate(podeAcao.acao)}
            disabled={transicionar.isPending || !!bloqueado}
            className={`w-full py-3 rounded-lg font-semibold active:opacity-90 disabled:opacity-40 ${podeAcao.cor}`}
            style={{ minHeight: 48 }}
          >
            {transicionar.isPending ? 'Enviando…' : podeAcao.label}
          </button>
        </div>
      )}
    </section>
  )
}
