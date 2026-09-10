import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'

function uuid4(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/**
 * Nova OS (mobile) — só a etapa de quem RELATA o problema. Escolher
 * oficina e lançar itens é do gestor, na tela de Detalhe — separado a
 * pedido do Hudson (#0145): a tela antiga misturava tudo num fluxo
 * corrido de 4 passos que não salvava nada até o fim.
 */
export default function MobileNovaOSPage() {
  const nav = useNavigate()
  const qc = useQueryClient()
  const [veiculoId, setVeiculoId] = useState<number | ''>('')
  const [tipoOs, setTipoOs] = useState<'corretiva_manual' | 'preventiva_automatica'>('corretiva_manual')
  const [descricao, setDescricao] = useState('')
  const [km, setKm] = useState<number>(0)
  const [erro, setErro] = useState('')

  const { data: veiculos } = useQuery({
    queryKey: ['m-veiculos-form'],
    queryFn: () => api.get('/veiculos').then(r => r.data),
  })

  const veiculoSel = (veiculos || []).find((v: any) => v.id === veiculoId)

  const onSelectVeiculo = (id: number) => {
    setVeiculoId(id)
    const v = (veiculos || []).find((x: any) => x.id === id)
    if (v && km === 0) setKm(v.km_atual || 0)
  }

  const createMut = useMutation({
    mutationFn: async () => {
      const request_id = uuid4()
      const criada = await api.post('/ordem-servico', {
        request_id,
        veiculo_id: Number(veiculoId),
        tipo_os: tipoOs,
        km_veiculo: Number(km),
        descricao_problema: descricao || null,
      }, { headers: { 'Idempotency-Key': request_id } }).then(r => r.data)
      // Já abre em seguida — vira aviso pro gestor (WhatsApp) em vez de
      // ficar parada sem ninguém saber.
      return api.post(`/ordem-servico/${criada.id}/abrir`).then(r => r.data)
    },
    onSuccess: (data) => {
      qc.invalidateQueries()
      nav(`/os/${data.id}`)
    },
    onError: (e: any) => setErro(e.response?.data?.detail || 'Erro ao abrir OS'),
  })

  const podeSalvar = !!veiculoId && km > 0 && !!descricao

  return (
    <section className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-3">
        <div className="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Veículo</div>
        <select
          value={veiculoId}
          onChange={(e) => onSelectVeiculo(Number(e.target.value))}
          className="w-full px-3 py-3 border border-line rounded-lg bg-white"
          style={{ minHeight: 48 }}
        >
          <option value="">— escolha o veículo —</option>
          {(veiculos || []).map((v: any) => (
            <option key={v.id} value={v.id}>{v.placa} · {v.modelo}</option>
          ))}
        </select>
        {veiculoSel && (
          <div className="bg-sky-bg border border-sky-500 rounded-lg p-3 text-sm">
            <div className="text-[10px] uppercase text-navy-800">KM atual (Patrimonial)</div>
            <div className="font-mono text-lg">{veiculoSel.km_atual.toLocaleString('pt-BR')}</div>
            <div className="text-[10px] uppercase text-navy-800 mt-2">Filial</div>
            <div>{veiculoSel.filial_id === 1 ? 'Maringá (100)' : veiculoSel.filial_id === 2 ? 'Ponta Grossa (700)' : 'LEM (900)'}</div>
          </div>
        )}
        <div>
          <label className="text-[11px] text-ink-500 block mb-1">KM lido agora *</label>
          <input
            type="number"
            value={km}
            onChange={(e) => setKm(Number(e.target.value))}
            className="w-full px-3 py-3 border-2 border-warn rounded-lg font-mono text-lg bg-warn-bg/30"
            style={{ minHeight: 48 }}
          />
        </div>
        <div>
          <label className="text-[11px] text-ink-500 block mb-1">Motivo</label>
          <textarea
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            placeholder="Ex: vazamento de óleo no motor"
            className="w-full px-3 py-2 border border-line rounded-lg h-24 text-sm"
          />
        </div>
        <div className="flex gap-2">
          <button onClick={() => setTipoOs('corretiva_manual')} className={`flex-1 py-3 rounded-lg border-2 font-medium ${tipoOs === 'corretiva_manual' ? 'border-err bg-err-bg text-err-fg' : 'border-line text-ink-500'}`} style={{ minHeight: 48 }}>
            Corretiva
          </button>
          <button onClick={() => setTipoOs('preventiva_automatica')} className={`flex-1 py-3 rounded-lg border-2 font-medium ${tipoOs === 'preventiva_automatica' ? 'border-ok bg-ok-bg text-ok-fg' : 'border-line text-ink-500'}`} style={{ minHeight: 48 }}>
            Preventiva
          </button>
        </div>

        {erro && <div className="bg-err-bg border border-err text-err-fg rounded p-2 text-sm">{erro}</div>}

        <div className="text-[11px] text-ink-500 text-center pt-1">
          Ao abrir, o responsável da filial recebe um aviso e cuida da oficina e do orçamento.
        </div>
      </div>

      <div className="bg-white border-t border-line p-3 sticky bottom-16 z-10" style={{ marginBottom: 'env(safe-area-inset-bottom)' }}>
        <button
          onClick={() => createMut.mutate()}
          disabled={!podeSalvar || createMut.isPending}
          className={`w-full rounded-lg font-semibold py-3 ${podeSalvar && !createMut.isPending ? 'bg-ok text-white' : 'bg-ink-200 text-ink-500'}`}
          style={{ minHeight: 48 }}
        >
          {createMut.isPending ? 'Abrindo...' : 'Abrir Ordem de Serviço'}
        </button>
      </div>
    </section>
  )
}
