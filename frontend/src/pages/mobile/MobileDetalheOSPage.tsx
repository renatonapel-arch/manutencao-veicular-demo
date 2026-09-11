import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { api } from '../../api/client'
import { fmtBRL, fmtDataHora, FilialChip, StatusBadge, TipoBadge } from '../../components/Badges'

/**
 * Detalhe mobile — mostra a OS e os botões da PRÓXIMA transição válida.
 * Cada transição = POST /ordem-servico/{id}/{acao} (não PATCH).
 *
 * #0150: faltava aqui (só existia no desktop) — ver foto anexada de
 * verdade, escolher/trocar oficina, e lançar itens/valores. Sem isso o
 * Hudson não conseguia negociar OS pelo celular.
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

const NOVO_ITEM_VAZIO = { tipo_item: 'peca', descricao: '', quantidade: 1, valor_unitario: 0 }

export default function MobileDetalheOSPage() {
  const { id } = useParams()
  const qc = useQueryClient()
  const [novoItem, setNovoItem] = useState<any>(NOVO_ITEM_VAZIO)
  const [mostrarForm, setMostrarForm] = useState(false)

  const { data: os, isLoading } = useQuery({
    queryKey: ['os', id],
    queryFn: () => api.get(`/ordem-servico/${id}`).then(r => r.data),
  })

  const { data: oficinas } = useQuery({
    queryKey: ['oficinas-form'],
    queryFn: () => api.get('/oficinas').then(r => r.data),
  })

  const transicionar = useMutation({
    mutationFn: (acao: string) =>
      api.post(`/ordem-servico/${id}/${acao}`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries(),
    onError: (e: any) => alert(e.response?.data?.detail || 'Erro na transição'),
  })

  const patchMut = useMutation({
    mutationFn: (payload: any) => api.patch(`/ordem-servico/${id}`, payload).then(r => r.data),
    onSuccess: () => qc.invalidateQueries(),
    onError: (e: any) => alert(e.response?.data?.detail || 'Erro ao atualizar'),
  })

  const addItemMut = useMutation({
    mutationFn: (item: any) => api.post(`/ordem-servico/${id}/itens`, item).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries()
      setNovoItem(NOVO_ITEM_VAZIO)
      setMostrarForm(false)
    },
    onError: (e: any) => alert(e.response?.data?.detail || 'Erro ao adicionar item'),
  })

  const delItemMut = useMutation({
    mutationFn: (itemId: number) => api.delete(`/ordem-servico/${id}/itens/${itemId}`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries(),
    onError: (e: any) => alert(e.response?.data?.detail || 'Erro ao remover item'),
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
  const podeAcao = PROX_ACOES[os.status]
  const podeNegociar = !['encerrada', 'cancelada'].includes(os.status)
  const podeAdicionarItem = novoItem.descricao && novoItem.valor_unitario > 0

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

      {/* Oficina — editável enquanto a OS não fechou (negociação do gestor) */}
      <div className="bg-white border border-line rounded-lg p-3">
        <div className="text-[10px] uppercase tracking-wider text-ink-500 mb-1">Oficina</div>
        {podeNegociar ? (
          <select
            value={os.oficina_id || ''}
            onChange={(e) => patchMut.mutate({ oficina_id: e.target.value ? Number(e.target.value) : null })}
            className="w-full px-3 py-2.5 border border-line rounded-lg bg-white text-sm"
            disabled={patchMut.isPending}
          >
            <option value="">— escolher oficina —</option>
            {(oficinas || []).map((o: any) => (
              <option key={o.id} value={o.id}>{o.nome} ({o.cidade}/{o.uf})</option>
            ))}
          </select>
        ) : (
          <div className="font-medium">{os.oficina?.nome || '—'}</div>
        )}
      </div>

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
            <div className="text-right flex-shrink-0 flex items-start gap-2">
              <div>
                <div className="text-[10px] text-ink-500 font-mono">{Number(it.quantidade)}×</div>
                <div className="font-mono font-medium num">{fmtBRL(it.subtotal)}</div>
              </div>
              {podeNegociar && (
                <button
                  onClick={() => delItemMut.mutate(it.id)}
                  disabled={delItemMut.isPending}
                  className="text-err-fg text-xs px-1"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        ))}
        <div className="px-3 py-2 bg-sky-bg flex justify-between items-center font-semibold border-t border-line">
          <span className="text-xs uppercase text-ink-500">Total</span>
          <span className="font-mono text-base text-navy-800 num">{fmtBRL(os.valor_total)}</span>
        </div>

        {podeNegociar && (
          <div className="p-3 border-t border-line">
            {!mostrarForm ? (
              <button
                onClick={() => setMostrarForm(true)}
                className="w-full border-2 border-dashed border-line rounded-lg py-2.5 text-sm font-medium text-navy-800 active:bg-sky-bg"
              >
                + Adicionar item
              </button>
            ) : (
              <div className="space-y-2">
                <div className="flex gap-2">
                  <select
                    value={novoItem.tipo_item}
                    onChange={(e) => setNovoItem({ ...novoItem, tipo_item: e.target.value })}
                    className="px-2 py-2 border border-line rounded-lg bg-white text-xs"
                  >
                    <option value="peca">Peça</option>
                    <option value="servico">Serviço</option>
                    <option value="ajuste">Ajuste</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Descrição"
                    value={novoItem.descricao}
                    onChange={(e) => setNovoItem({ ...novoItem, descricao: e.target.value })}
                    className="flex-1 px-3 py-2 border border-line rounded-lg text-sm"
                  />
                </div>
                <div className="flex gap-2">
                  <input
                    type="number"
                    placeholder="Qtd"
                    value={novoItem.quantidade}
                    onChange={(e) => setNovoItem({ ...novoItem, quantidade: Number(e.target.value) })}
                    className="w-20 px-2 py-2 border border-line rounded-lg font-mono text-right text-sm"
                    step="0.01"
                  />
                  <input
                    type="number"
                    placeholder="Valor unit."
                    value={novoItem.valor_unitario}
                    onChange={(e) => setNovoItem({ ...novoItem, valor_unitario: Number(e.target.value) })}
                    className="flex-1 px-2 py-2 border border-line rounded-lg font-mono text-right text-sm"
                    step="0.01"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setMostrarForm(false)}
                    className="flex-1 border border-line rounded-lg py-2 text-sm text-ink-500"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={() => addItemMut.mutate(novoItem)}
                    disabled={!podeAdicionarItem || addItemMut.isPending}
                    className={`flex-1 rounded-lg py-2 text-sm font-medium text-white ${podeAdicionarItem && !addItemMut.isPending ? 'bg-naval' : 'bg-ink-300'}`}
                  >
                    {addItemMut.isPending ? 'Salvando…' : 'Adicionar'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
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
              <a key={a.id} href={a.arquivo_url} target="_blank" rel="noreferrer"
                 className="aspect-square rounded-lg overflow-hidden block border border-line">
                <img src={a.arquivo_url} alt="Foto anexada" className="w-full h-full object-cover" />
              </a>
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
          {temNF && (
            <a
              href={(os.anexos || []).find((a: any) => a.tipo === 'nf')?.arquivo_url}
              target="_blank" rel="noreferrer"
              className="block w-full border-2 rounded-lg py-4 flex flex-col items-center mb-1.5 border-ok bg-ok-bg/20 active:bg-ok-bg/40"
            >
              <span className="font-medium text-sm text-navy-800">Ver NF anexada</span>
            </a>
          )}
          <label className={`block w-full border-2 border-dashed rounded-lg ${temNF ? 'py-2' : 'py-5'} flex flex-col items-center cursor-pointer active:bg-sky-bg border-line`}>
            <span className={`font-medium text-navy-800 ${temNF ? 'text-xs' : 'text-sm'}`}>{temNF ? 'Substituir NF' : '+ Anexar NF'}</span>
            {!temNF && <span className="text-[10px] text-ink-400">PDF · JPG · ≤20MB</span>}
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
