import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { fmtBRL } from '../../components/Badges'

interface Item {
  tipo_item: 'peca' | 'servico' | 'ajuste'
  descricao: string
  quantidade: number
  valor_unitario: number
  garantia_dias: number
}

function uuid4(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

const PASSOS = ['Veículo', 'Oficina', 'Itens', 'Anexos', 'Revisar']

export default function MobileNovaOSPage() {
  const nav = useNavigate()
  const [passo, setPasso] = useState(0)
  const [veiculoId, setVeiculoId] = useState<number | ''>('')
  const [oficinaId, setOficinaId] = useState<number | ''>('')
  const [tipoOs, setTipoOs] = useState<'corretiva_manual' | 'preventiva_automatica'>('corretiva_manual')
  const [descricao, setDescricao] = useState('')
  const [km, setKm] = useState<number>(0)
  const [itens, setItens] = useState<Item[]>([{ tipo_item: 'peca', descricao: '', quantidade: 1, valor_unitario: 0, garantia_dias: 30 }])
  const [erro, setErro] = useState('')

  const { data: veiculos } = useQuery({
    queryKey: ['m-veiculos-form'],
    queryFn: () => api.get('/veiculos').then(r => r.data),
  })
  const { data: oficinas } = useQuery({
    queryKey: ['m-oficinas-form'],
    queryFn: () => api.get('/oficinas').then(r => r.data),
  })

  const veiculoSel = (veiculos || []).find((v: any) => v.id === veiculoId)
  const oficinaSel = (oficinas || []).find((o: any) => o.id === oficinaId)
  const subtotal = itens.reduce((s, it) => s + (it.valor_unitario || 0) * (it.quantidade || 1), 0)

  const onSelectVeiculo = (id: number) => {
    setVeiculoId(id)
    const v = (veiculos || []).find((x: any) => x.id === id)
    if (v && km === 0) setKm(v.km_atual || 0)
  }

  const addItem = () => setItens([...itens, { tipo_item: 'peca', descricao: '', quantidade: 1, valor_unitario: 0, garantia_dias: 30 }])
  const remItem = (i: number) => setItens(itens.filter((_, idx) => idx !== i))
  const updItem = (i: number, p: Partial<Item>) => setItens(itens.map((it, idx) => idx === i ? { ...it, ...p } : it))

  const createMut = useMutation({
    mutationFn: () => {
      const payload = {
        request_id: uuid4(),
        veiculo_id: Number(veiculoId),
        tipo_os: tipoOs,
        oficina_id: oficinaId ? Number(oficinaId) : null,
        km_veiculo: Number(km),
        descricao_problema: descricao || null,
        itens: itens.filter(it => it.descricao && it.valor_unitario > 0).map(it => ({
          tipo_item: it.tipo_item, descricao: it.descricao, quantidade: it.quantidade,
          valor_unitario: it.valor_unitario, garantia_dias: it.garantia_dias,
        })),
      }
      return api.post('/ordem-servico', payload, { headers: { 'Idempotency-Key': payload.request_id } }).then(r => r.data)
    },
    onSuccess: (data) => nav(`/os/${data.id}`),
    onError: (e: any) => setErro(e.response?.data?.detail || 'Erro ao criar OS'),
  })

  const podeAvancar = () => {
    if (passo === 0) return !!veiculoId && km > 0
    if (passo === 1) return !!oficinaId
    if (passo === 2) return itens.some(it => it.descricao && it.valor_unitario > 0)
    return true
  }

  return (
    <section className="flex flex-col h-full">
      {/* Stepper */}
      <div className="bg-white border-b border-border px-3 py-3 sticky top-0 z-10">
        <div className="flex items-center gap-1">
          {PASSOS.map((p, i) => (
            <div key={i} className="flex items-center flex-1 last:flex-initial">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-medium ${
                i < passo ? 'bg-success text-white' : i === passo ? 'bg-naval text-white' : 'bg-ink-200 text-ink-500'
              }`}>{i < passo ? '✓' : i + 1}</div>
              {i < PASSOS.length - 1 && <div className={`h-0.5 flex-1 ${i < passo ? 'bg-success' : 'bg-ink-200'}`}/>}
            </div>
          ))}
        </div>
        <div className="flex justify-between text-[9px] text-ink-500 mt-1.5">
          {PASSOS.map((p, i) => (
            <span key={i} className={i === passo ? 'text-naval font-semibold' : ''}>{p}</span>
          ))}
        </div>
      </div>

      {/* Conteúdo */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-3">
        {/* Passo 0 — veículo */}
        {passo === 0 && (
          <>
            <div className="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Veículo</div>
            <select
              value={veiculoId}
              onChange={(e) => onSelectVeiculo(Number(e.target.value))}
              className="w-full px-3 py-3 border border-border-strong rounded-lg bg-white"
              style={{ minHeight: 48 }}
            >
              <option value="">— escolha o veículo —</option>
              {(veiculos || []).map((v: any) => (
                <option key={v.id} value={v.id}>{v.placa} · {v.modelo}</option>
              ))}
            </select>
            {veiculoSel && (
              <div className="bg-gelo border border-ceu-claro rounded-lg p-3 text-sm">
                <div className="text-[10px] uppercase text-naval">KM atual (Patrimonial)</div>
                <div className="font-mono text-lg">{veiculoSel.km_atual.toLocaleString('pt-BR')}</div>
                <div className="text-[10px] uppercase text-naval mt-2">Filial</div>
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
                className="w-full px-3 py-2 border border-border-strong rounded-lg h-24 text-sm"
              />
            </div>
            <div className="flex gap-2">
              <button onClick={() => setTipoOs('corretiva_manual')} className={`flex-1 py-3 rounded-lg border-2 font-medium ${tipoOs === 'corretiva_manual' ? 'border-danger bg-danger-bg text-danger-fg' : 'border-border text-ink-500'}`} style={{ minHeight: 48 }}>
                Corretiva
              </button>
              <button onClick={() => setTipoOs('preventiva_automatica')} className={`flex-1 py-3 rounded-lg border-2 font-medium ${tipoOs === 'preventiva_automatica' ? 'border-success bg-success-bg text-success-fg' : 'border-border text-ink-500'}`} style={{ minHeight: 48 }}>
                Preventiva
              </button>
            </div>
          </>
        )}

        {/* Passo 1 — oficina */}
        {passo === 1 && (
          <>
            <div className="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Oficina</div>
            <div className="text-[11px] text-ink-500">Catálogo padronizado · texto livre <b className="text-danger-fg">bloqueado</b></div>
            <div className="space-y-2">
              {(oficinas || []).map((o: any) => (
                <button
                  key={o.id}
                  onClick={() => setOficinaId(o.id)}
                  className={`w-full text-left p-3 border-2 rounded-lg ${oficinaId === o.id ? 'border-naval bg-gelo' : 'border-border bg-white'}`}
                  style={{ minHeight: 64 }}
                >
                  <div className="font-medium">{o.nome}</div>
                  <div className="text-xs text-ink-500">{o.cidade}/{o.uf} · ★ {o.avaliacao || '—'} · ticket médio {fmtBRL(o.valor_servico_padrao)}</div>
                </button>
              ))}
            </div>
          </>
        )}

        {/* Passo 2 — itens */}
        {passo === 2 && (
          <>
            <div className="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Itens (peças + serviços)</div>
            <div className="space-y-2">
              {itens.map((it, i) => (
                <div key={i} className="bg-white border-2 border-border-strong rounded-lg p-3 space-y-2">
                  <div className="flex justify-between items-start">
                    <select
                      value={it.tipo_item}
                      onChange={(e) => updItem(i, { tipo_item: e.target.value as any })}
                      className="px-2 py-1.5 border border-border rounded bg-white text-xs"
                    >
                      <option value="peca">Peça</option>
                      <option value="servico">Serviço</option>
                      <option value="ajuste">Ajuste</option>
                    </select>
                    {itens.length > 1 && <button onClick={() => remItem(i)} className="text-danger text-lg">🗑</button>}
                  </div>
                  <input
                    type="text"
                    placeholder="Ex: Junta cabeçote"
                    value={it.descricao}
                    onChange={(e) => updItem(i, { descricao: e.target.value })}
                    className="w-full px-3 py-2 border border-border rounded text-sm"
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-ink-500">Qtd</label>
                      <input type="number" value={it.quantidade} onChange={(e) => updItem(i, { quantidade: Number(e.target.value) })} className="w-full px-2 py-1.5 border border-border rounded font-mono text-right" step="0.01"/>
                    </div>
                    <div>
                      <label className="text-[10px] text-ink-500">Valor unit. (R$)</label>
                      <input type="number" value={it.valor_unitario} onChange={(e) => updItem(i, { valor_unitario: Number(e.target.value) })} className="w-full px-2 py-1.5 border border-border rounded font-mono text-right" step="0.01"/>
                    </div>
                  </div>
                  <div className="text-right text-sm">
                    <span className="text-ink-500">Subtotal: </span>
                    <span className="font-mono font-medium text-naval">{fmtBRL((it.valor_unitario || 0) * (it.quantidade || 1))}</span>
                  </div>
                </div>
              ))}
              <button
                onClick={addItem}
                className="w-full border-2 border-dashed border-ink-300 text-naval rounded-lg py-3 font-medium"
                style={{ minHeight: 48 }}
              >
                + Adicionar item
              </button>
              <div className="bg-naval text-white rounded-lg p-3 flex justify-between items-center">
                <span className="text-xs uppercase tracking-wider">Total</span>
                <span className="font-mono text-lg font-semibold">{fmtBRL(subtotal)}</span>
              </div>
            </div>
          </>
        )}

        {/* Passo 3 — anexos (placeholder) */}
        {passo === 3 && (
          <>
            <div className="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Anexos</div>
            <div className="bg-warn-bg border border-warn rounded-lg p-3 text-[12px] text-warn-fg">
              ⚠️ Anexos (foto + NF) só podem ser enviados <b>depois</b> que a OS for criada.
              Aqui você revisa os dados e cria como rascunho — a próxima tela vai pedir foto + NF.
            </div>
            <div className="bg-white border border-border rounded-lg p-3">
              <div className="text-sm font-medium mb-2">📷 Foto do hodômetro</div>
              <div className="text-xs text-ink-500">Pelo menos 1 foto obrigatória pra encerrar a OS.</div>
            </div>
            <div className="bg-white border border-border rounded-lg p-3">
              <div className="text-sm font-medium mb-2">📄 NF da oficina</div>
              <div className="text-xs text-ink-500">Obrigatória pra encerrar — backend bloqueia HTTP 400 sem NF anexada.</div>
            </div>
          </>
        )}

        {/* Passo 4 — revisar */}
        {passo === 4 && (
          <>
            <div className="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Confirmar criação</div>
            <div className="bg-white border border-border rounded-lg divide-y divide-border">
              <div className="px-3 py-2 flex justify-between">
                <span className="text-[11px] text-ink-500">Veículo</span>
                <span className="font-mono text-sm font-medium">{veiculoSel?.placa} · {veiculoSel?.modelo}</span>
              </div>
              <div className="px-3 py-2 flex justify-between">
                <span className="text-[11px] text-ink-500">KM lido</span>
                <span className="font-mono text-sm">{km.toLocaleString('pt-BR')}</span>
              </div>
              <div className="px-3 py-2 flex justify-between">
                <span className="text-[11px] text-ink-500">Tipo</span>
                <span className="text-sm">{tipoOs === 'corretiva_manual' ? 'Corretiva' : 'Preventiva'}</span>
              </div>
              <div className="px-3 py-2 flex justify-between">
                <span className="text-[11px] text-ink-500">Oficina</span>
                <span className="text-sm text-right">{oficinaSel?.nome}</span>
              </div>
              <div className="px-3 py-2 flex justify-between">
                <span className="text-[11px] text-ink-500">Itens</span>
                <span className="text-sm">{itens.filter(it => it.descricao).length}</span>
              </div>
              <div className="px-3 py-2 flex justify-between bg-gelo">
                <span className="text-sm font-medium text-naval">Total</span>
                <span className="font-mono text-lg font-semibold text-naval">{fmtBRL(subtotal)}</span>
              </div>
            </div>
            {erro && <div className="bg-danger-bg border border-danger text-danger-fg rounded p-2 text-sm">{erro}</div>}
          </>
        )}
      </div>

      {/* Bottom CTA */}
      <div className="bg-white border-t border-border p-3 flex gap-2 sticky bottom-16 z-10" style={{ marginBottom: 'env(safe-area-inset-bottom)' }}>
        {passo > 0 && (
          <button onClick={() => setPasso(passo - 1)} className="flex-1 border border-border-strong text-naval rounded-lg font-medium" style={{ minHeight: 48 }}>
            Voltar
          </button>
        )}
        {passo < PASSOS.length - 1 ? (
          <button
            onClick={() => setPasso(passo + 1)}
            disabled={!podeAvancar()}
            className={`flex-1 rounded-lg font-semibold ${podeAvancar() ? 'bg-naval text-white' : 'bg-ink-200 text-ink-500'}`}
            style={{ minHeight: 48 }}
          >
            Próximo →
          </button>
        ) : (
          <button
            onClick={() => createMut.mutate()}
            disabled={createMut.isPending}
            className="flex-1 bg-success text-white rounded-lg font-semibold"
            style={{ minHeight: 48 }}
          >
            {createMut.isPending ? 'Criando...' : 'Criar OS ✓'}
          </button>
        )}
      </div>
    </section>
  )
}
