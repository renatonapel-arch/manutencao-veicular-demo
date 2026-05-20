import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { fmtBRL, FilialChip } from '../components/Badges'

interface Item {
  tipo_item: 'peca' | 'servico' | 'ajuste'
  descricao: string
  sige_sku?: string
  quantidade: number
  valor_unitario: number
  garantia_dias: number
}

function uuid4(): string {
  // RFC4122 v4 simples (não-crypto, ok pra demo)
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

export default function NovaOSPage() {
  const nav = useNavigate()
  const { data: veiculos } = useQuery({
    queryKey: ['veiculos-form'],
    queryFn: () => api.get('/veiculos').then(r => r.data),
  })
  const { data: oficinas } = useQuery({
    queryKey: ['oficinas-form'],
    queryFn: () => api.get('/oficinas').then(r => r.data),
  })

  const [veiculoId, setVeiculoId] = useState<number | ''>('')
  const [oficinaId, setOficinaId] = useState<number | ''>('')
  const [tipoOs, setTipoOs] = useState<'corretiva_manual' | 'preventiva_automatica'>('corretiva_manual')
  const [descricao, setDescricao] = useState('')
  const [km, setKm] = useState<number>(0)
  const [dataAgendada, setDataAgendada] = useState<string>('')
  const [itens, setItens] = useState<Item[]>([
    { tipo_item: 'peca', descricao: '', quantidade: 1, valor_unitario: 0, garantia_dias: 30 },
  ])
  const [erro, setErro] = useState('')

  const veiculoSel = (veiculos || []).find((v: any) => v.id === veiculoId)

  // Quando seleciona veículo, sugere o km atual
  const onSelectVeiculo = (id: number) => {
    setVeiculoId(id)
    const v = (veiculos || []).find((x: any) => x.id === id)
    if (v && km === 0) setKm(v.km_atual || 0)
  }

  const addItem = () => {
    setItens([...itens, { tipo_item: 'peca', descricao: '', quantidade: 1, valor_unitario: 0, garantia_dias: 30 }])
  }
  const removeItem = (i: number) => setItens(itens.filter((_, idx) => idx !== i))
  const updateItem = (i: number, patch: Partial<Item>) => {
    setItens(itens.map((it, idx) => idx === i ? { ...it, ...patch } : it))
  }

  const subtotal = itens.reduce((s, it) => s + (it.valor_unitario || 0) * (it.quantidade || 1), 0)

  const createMut = useMutation({
    mutationFn: () => {
      const payload = {
        request_id: uuid4(),
        veiculo_id: Number(veiculoId),
        tipo_os: tipoOs,
        oficina_id: oficinaId ? Number(oficinaId) : null,
        km_veiculo: Number(km),
        descricao_problema: descricao || null,
        data_agendada: dataAgendada || null,
        itens: itens
          .filter(it => it.descricao && it.valor_unitario > 0)
          .map(it => ({
            tipo_item: it.tipo_item,
            descricao: it.descricao,
            sige_sku: it.sige_sku || null,
            quantidade: it.quantidade,
            valor_unitario: it.valor_unitario,
            garantia_dias: it.garantia_dias,
          })),
      }
      return api.post('/ordem-servico', payload, {
        headers: { 'Idempotency-Key': payload.request_id }
      }).then(r => r.data)
    },
    onSuccess: (data) => {
      nav(`/os/${data.id}`)
    },
    onError: (e: any) => {
      setErro(e.response?.data?.detail || 'Erro ao criar OS')
    },
  })

  const podeSalvar = veiculoId && oficinaId && descricao && itens.some(it => it.descricao && it.valor_unitario > 0)

  return (
    <section className="max-w-5xl">
      <div className="flex items-center gap-3 mb-3">
        <Link to="/os" className="text-ink-400 hover:text-naval">← Voltar</Link>
        <div className="text-lg font-semibold text-naval">Nova Ordem de Serviço</div>
      </div>

      <div className="space-y-3">
        {/* Veículo + filial + km */}
        <div className="bg-white border border-border rounded p-3">
          <div className="text-[11px] uppercase tracking-wider text-ink-500 mb-2 font-medium">1 · Veículo</div>
          <div className="grid grid-cols-3 gap-3 text-[12px]">
            <div className="col-span-2">
              <label className="text-[11px] text-ink-500">Veículo <span className="text-danger">*</span></label>
              <select
                value={veiculoId}
                onChange={(e) => onSelectVeiculo(Number(e.target.value))}
                className="w-full px-2 py-1.5 border border-border-strong rounded bg-white"
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
              <label className="text-[11px] text-ink-500">Filial</label>
              <div className="px-2 py-1.5 border border-border rounded bg-ink-50">
                {veiculoSel ? <FilialChip filialId={veiculoSel.filial_id}/> : <span className="text-ink-400">—</span>}
              </div>
            </div>
            <div>
              <label className="text-[11px] text-ink-500">KM atual (API) <span className="text-ink-400">readonly</span></label>
              <input
                type="text"
                readOnly
                value={veiculoSel?.km_atual?.toLocaleString('pt-BR') || ''}
                className="w-full px-2 py-1.5 border border-border rounded bg-ink-50 font-mono text-ink-500"
              />
            </div>
            <div>
              <label className="text-[11px] text-ink-500">KM lido <span className="text-danger">*</span></label>
              <input
                type="number"
                value={km}
                onChange={(e) => setKm(Number(e.target.value))}
                className="w-full px-2 py-1.5 border border-border-strong rounded font-mono"
              />
            </div>
            <div>
              <label className="text-[11px] text-ink-500">Vencimento CRLV</label>
              <div className="px-2 py-1.5 border border-border rounded bg-ink-50 font-mono text-success-fg">
                {veiculoSel?.vencimento_crlv || '—'}
              </div>
            </div>
          </div>
        </div>

        {/* Tipo */}
        <div className="bg-white border border-border rounded p-3">
          <div className="text-[11px] uppercase tracking-wider text-ink-500 mb-2 font-medium">2 · Tipo &amp; motivo</div>
          <div className="flex gap-3 mb-2">
            <label className={`flex items-center gap-1.5 text-[12px] border rounded px-3 py-1.5 cursor-pointer ${tipoOs === 'corretiva_manual' ? 'bg-danger-bg border-danger' : 'bg-white border-border-strong'}`}>
              <input type="radio" name="tipo" checked={tipoOs === 'corretiva_manual'} onChange={() => setTipoOs('corretiva_manual')}/>
              <span className="badge tp-corretiva">Corretiva</span>
              <span className="text-ink-500">— problema reportado</span>
            </label>
            <label className={`flex items-center gap-1.5 text-[12px] border rounded px-3 py-1.5 cursor-pointer ${tipoOs === 'preventiva_automatica' ? 'bg-success-bg border-success' : 'bg-white border-border-strong'}`}>
              <input type="radio" name="tipo" checked={tipoOs === 'preventiva_automatica'} onChange={() => setTipoOs('preventiva_automatica')}/>
              <span className="badge tp-preventiva">Preventiva</span>
              <span className="text-ink-500">— manual</span>
            </label>
          </div>
          <textarea
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            placeholder="Descreva o problema reportado..."
            className="w-full border border-border-strong rounded px-2 py-1.5 text-[12px] h-20"
          />
        </div>

        {/* Oficina */}
        <div className="bg-white border border-border rounded p-3">
          <div className="text-[11px] uppercase tracking-wider text-ink-500 mb-2 font-medium">3 · Oficina &amp; agenda</div>
          <div className="grid grid-cols-3 gap-3 text-[12px]">
            <div className="col-span-2">
              <label className="text-[11px] text-ink-500">Oficina <span className="text-danger">*</span></label>
              <select
                value={oficinaId}
                onChange={(e) => setOficinaId(Number(e.target.value))}
                className="w-full px-2 py-1.5 border border-border-strong rounded bg-white"
              >
                <option value="">— catálogo padronizado, texto livre bloqueado —</option>
                {(oficinas || []).map((o: any) => (
                  <option key={o.id} value={o.id}>
                    {o.nome} ({o.cidade}/{o.uf}) · ★ {o.avaliacao || '—'}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[11px] text-ink-500">Data agendada</label>
              <input
                type="date"
                value={dataAgendada}
                onChange={(e) => setDataAgendada(e.target.value)}
                className="w-full px-2 py-1.5 border border-border-strong rounded font-mono"
              />
            </div>
          </div>
        </div>

        {/* Itens */}
        <div className="bg-white border border-border rounded p-3">
          <div className="flex justify-between items-center mb-2">
            <div className="text-[11px] uppercase tracking-wider text-ink-500 font-medium">4 · Itens (peças e serviços)</div>
            <button onClick={addItem} className="text-xs bg-ink-100 hover:bg-ink-200 px-2 py-1 rounded">+ Adicionar item</button>
          </div>
          <table className="w-full text-[12px] dense">
            <thead className="bg-ink-50 text-ink-500 border-y border-border">
              <tr>
                <th className="text-left w-20">Tipo</th>
                <th className="text-left">Descrição</th>
                <th className="text-left w-24">SKU SIGE</th>
                <th className="text-right w-16">Qtd</th>
                <th className="text-right w-24">Valor unit.</th>
                <th className="text-right w-24">Subtotal</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {itens.map((it, i) => (
                <tr key={i} className="border-t border-border">
                  <td>
                    <select
                      value={it.tipo_item}
                      onChange={(e) => updateItem(i, { tipo_item: e.target.value as Item['tipo_item'] })}
                      className="border border-border rounded px-1 py-0.5 bg-white w-full text-[11px]"
                    >
                      <option value="peca">Peça</option>
                      <option value="servico">Serviço</option>
                      <option value="ajuste">Ajuste</option>
                    </select>
                  </td>
                  <td>
                    <input
                      type="text"
                      value={it.descricao}
                      onChange={(e) => updateItem(i, { descricao: e.target.value })}
                      placeholder="Ex: Junta cabeçote / Mão de obra"
                      className="w-full px-2 py-1 border border-border rounded"
                    />
                  </td>
                  <td>
                    <input
                      type="text"
                      value={it.sige_sku || ''}
                      onChange={(e) => updateItem(i, { sige_sku: e.target.value })}
                      placeholder="opcional"
                      className="w-full px-2 py-1 border border-border rounded font-mono text-[11px]"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      value={it.quantidade}
                      onChange={(e) => updateItem(i, { quantidade: Number(e.target.value) })}
                      className="w-full px-2 py-1 border border-border rounded font-mono text-right"
                      step="0.01"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      value={it.valor_unitario}
                      onChange={(e) => updateItem(i, { valor_unitario: Number(e.target.value) })}
                      className="w-full px-2 py-1 border border-border rounded font-mono text-right"
                      step="0.01"
                    />
                  </td>
                  <td className="text-right font-medium font-mono">
                    {fmtBRL((it.valor_unitario || 0) * (it.quantidade || 1))}
                  </td>
                  <td className="text-center">
                    {itens.length > 1 && (
                      <button onClick={() => removeItem(i)} className="text-danger hover:text-danger-fg">🗑</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="border-t-2 border-border-strong">
              <tr className="font-semibold bg-ink-50">
                <td colSpan={5} className="text-right pr-2">Subtotal</td>
                <td className="text-right text-base font-mono text-naval">{fmtBRL(subtotal)}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>

        {erro && (
          <div className="bg-danger-bg border border-danger text-danger-fg rounded p-2 text-sm">{erro}</div>
        )}

        {/* Ações */}
        <div className="flex justify-end gap-2">
          <Link to="/os" className="border border-border-strong bg-white px-4 py-2 rounded text-sm">Cancelar</Link>
          <button
            onClick={() => createMut.mutate()}
            disabled={!podeSalvar || createMut.isPending}
            className={`px-4 py-2 rounded text-sm font-medium text-white ${podeSalvar && !createMut.isPending ? 'bg-naval hover:bg-noite' : 'bg-ink-300 cursor-not-allowed'}`}
          >
            {createMut.isPending ? 'Criando...' : 'Criar OS (rascunho)'}
          </button>
        </div>

        <div className="text-[11px] text-ink-500 text-center">
          OS é criada como <b>rascunho</b> · você pode anexar foto/NF e mudar status na tela de detalhe.
        </div>
      </div>
    </section>
  )
}
