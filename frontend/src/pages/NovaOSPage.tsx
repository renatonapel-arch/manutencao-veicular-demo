import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { FilialChip } from '../components/Badges'

function uuid4(): string {
  // RFC4122 v4 simples (não-crypto, ok pra demo)
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/**
 * Nova OS — só a etapa de quem RELATA o problema (motorista/solicitante).
 * Escolher oficina e lançar itens/orçamento é responsabilidade de quem faz
 * a triagem, dentro do Detalhe da OS — separado a pedido do Hudson (#0145):
 * a tela antiga misturava "abrir OS" com "negociação financeira e escolha
 * de oficina" num fluxo só, sem salvar nada até o fim.
 */
export default function NovaOSPage() {
  const nav = useNavigate()
  const qc = useQueryClient()
  const { data: veiculos } = useQuery({
    queryKey: ['veiculos-form'],
    queryFn: () => api.get('/veiculos').then(r => r.data),
  })

  const [veiculoId, setVeiculoId] = useState<number | ''>('')
  const [tipoOs, setTipoOs] = useState<'corretiva_manual' | 'preventiva_automatica'>('corretiva_manual')
  const [categoria, setCategoria] = useState<string>('')
  const [urgencia, setUrgencia] = useState<string>('')
  const [descricao, setDescricao] = useState('')
  const [km, setKm] = useState<number>(0)
  const [erro, setErro] = useState('')

  const veiculoSel = (veiculos || []).find((v: any) => v.id === veiculoId)

  // Quando seleciona veículo, sugere o km atual
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
        categoria: categoria || null,
        urgencia: urgencia || null,
        km_veiculo: Number(km),
        descricao_problema: descricao || null,
      }, {
        headers: { 'Idempotency-Key': request_id },
      }).then(r => r.data)
      // Nasce "rascunho" — já abre em seguida pra virar aviso pro gestor
      // (dispara WhatsApp) em vez de ficar parada sem ninguém saber.
      return api.post(`/ordem-servico/${criada.id}/abrir`).then(r => r.data)
    },
    onSuccess: (data) => {
      qc.invalidateQueries()  // refaz Dashboard, listas, etc.
      nav(`/os/${data.id}`)
    },
    onError: (e: any) => {
      setErro(e.response?.data?.detail || 'Erro ao abrir OS')
    },
  })

  const podeSalvar = veiculoId && km > 0 && descricao

  return (
    <section className="max-w-3xl">
      <div className="flex items-center gap-3 mb-3">
        <Link to="/os" className="text-nv-soft hover:text-nv-primary">← Voltar</Link>
        <div className="text-lg font-semibold text-nv-primary">Nova Ordem de Serviço</div>
      </div>

      <div className="space-y-3">
        {/* Veículo + filial + km */}
        <div className="card p-5">
          <div className="kpi-label mb-3">1 · Veículo</div>
          <div className="grid grid-cols-3 gap-3 text-[12px]">
            <div className="col-span-2">
              <label className="text-[11px] text-nv-soft">Veículo <span className="text-nv-danger-text">*</span></label>
              <select
                value={veiculoId}
                onChange={(e) => onSelectVeiculo(Number(e.target.value))}
                className="w-full px-2 py-1.5 border border-nv-border-strong rounded bg-nv-surface"
              >
                <option value="">— selecione —</option>
                {(veiculos || []).map((v: any) => (
                  <option key={v.id} value={v.id}>
                    {v.placa} · {v.modelo}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[11px] text-nv-soft">Filial</label>
              <div className="px-2 py-1.5 border border-nv-border-strong rounded bg-nv-bg">
                {veiculoSel ? <FilialChip filialId={veiculoSel.filial_id}/> : <span className="text-nv-soft">—</span>}
              </div>
            </div>
            <div>
              <label className="text-[11px] text-nv-soft">KM atual (API) <span className="text-nv-soft">readonly</span></label>
              <input
                type="text"
                readOnly
                value={veiculoSel?.km_atual?.toLocaleString('pt-BR') || ''}
                className="w-full px-2 py-1.5 border border-nv-border-strong rounded bg-nv-bg font-mono text-nv-soft"
              />
            </div>
            <div>
              <label className="text-[11px] text-nv-soft">KM lido <span className="text-nv-danger-text">*</span></label>
              <input
                type="number"
                value={km}
                onChange={(e) => setKm(Number(e.target.value))}
                className="w-full px-2 py-1.5 border border-nv-border-strong rounded font-mono"
              />
            </div>
            <div>
              <label className="text-[11px] text-nv-soft">Vencimento CRLV</label>
              <div className="px-2 py-1.5 border border-nv-border-strong rounded bg-nv-bg font-mono text-nv-success">
                {veiculoSel?.vencimento_crlv || '—'}
              </div>
            </div>
          </div>
        </div>

        {/* Tipo & motivo */}
        <div className="card p-5">
          <div className="kpi-label mb-3">2 · Tipo &amp; motivo</div>
          <div className="flex gap-3 mb-2">
            <label className={`flex items-center gap-1.5 text-[12px] border rounded px-3 py-1.5 cursor-pointer ${tipoOs === 'corretiva_manual' ? 'bg-nv-danger-bg border-nv-danger' : 'bg-nv-surface border-nv-border-strong'}`}>
              <input type="radio" name="tipo" checked={tipoOs === 'corretiva_manual'} onChange={() => setTipoOs('corretiva_manual')}/>
              <span className="badge tp-corretiva">Corretiva</span>
              <span className="text-nv-soft">— problema reportado</span>
            </label>
            <label className={`flex items-center gap-1.5 text-[12px] border rounded px-3 py-1.5 cursor-pointer ${tipoOs === 'preventiva_automatica' ? 'bg-nv-success-bg border-nv-success' : 'bg-nv-surface border-nv-border-strong'}`}>
              <input type="radio" name="tipo" checked={tipoOs === 'preventiva_automatica'} onChange={() => setTipoOs('preventiva_automatica')}/>
              <span className="badge tp-preventiva">Preventiva</span>
              <span className="text-nv-soft">— manual</span>
            </label>
          </div>
          <textarea
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            placeholder="Descreva o problema reportado..."
            className="w-full border border-nv-border-strong rounded px-2 py-1.5 text-[12px] h-20"
          />

          {/* Categoria (campo Tipo do Pipefy) */}
          <div className="mt-3">
            <label className="text-[11px] text-nv-soft block mb-1">Categoria do serviço <span className="text-nv-soft">(alimenta o dashboard)</span></label>
            <div className="flex flex-wrap gap-1.5">
              {['Motor', 'Pneu', 'Pastilha / Lona', 'Relação', 'Lâmpadas', 'Elétrica', 'Bateria', 'Embreagem', 'Empilhadeira', 'Outros'].map(c => (
                <button
                  key={c} type="button"
                  onClick={() => setCategoria(categoria === c ? '' : c)}
                  className={`px-2.5 py-1 rounded-full text-[11px] border ${categoria === c ? 'bg-nv-primary text-nv-bg border-nv-primary' : 'bg-nv-surface border-nv-border-strong text-nv-soft hover:border-nv-primary'}`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          {/* Urgência */}
          <div className="mt-3">
            <label className="text-[11px] text-nv-soft block mb-1">Urgência</label>
            <div className="flex flex-wrap gap-1.5">
              {[
                { v: 'parado',          l: 'Parado — precisa guincho',   tone: 'err'  },
                { v: 'roda_com_reparo', l: 'Roda mas precisa reparo',    tone: 'warn' },
                { v: 'cosmetico',       l: 'Cosmético — pode aguardar',  tone: 'ok'   },
              ].map(u => (
                <button
                  key={u.v} type="button"
                  onClick={() => setUrgencia(urgencia === u.v ? '' : u.v)}
                  className={`chip ${urgencia === u.v ? 'chip-on' : ''}`}
                >
                  <span className={`inline-block w-2 h-2 rounded-full mr-1.5 ${
                    u.tone === 'err' ? 'bg-nv-danger' : u.tone === 'warn' ? 'bg-nv-warn' : 'bg-nv-success'
                  }`} />
                  {u.l}
                </button>
              ))}
            </div>
          </div>
        </div>

        {erro && (
          <div className="bg-nv-danger-bg border border-nv-danger text-nv-danger-text rounded p-2 text-sm">{erro}</div>
        )}

        {/* Ações */}
        <div className="flex justify-end gap-2">
          <Link to="/os" className="border border-nv-border-strong bg-transparent text-nv-ink px-4 py-2 rounded text-sm">Cancelar</Link>
          <button
            onClick={() => createMut.mutate()}
            disabled={!podeSalvar || createMut.isPending}
            className={`px-4 py-2 rounded text-sm font-medium ${podeSalvar && !createMut.isPending ? 'bg-nv-primary text-nv-bg hover:bg-nv-primary-hover' : 'bg-nv-surface-2 text-nv-soft cursor-not-allowed'}`}
          >
            {createMut.isPending ? 'Abrindo...' : 'Abrir Ordem de Serviço'}
          </button>
        </div>

        <div className="text-[11px] text-nv-soft text-center">
          Ao abrir, o responsável da filial recebe um aviso e escolhe a oficina, faz o orçamento e conduz o resto do processo.
        </div>
      </div>
    </section>
  )
}
