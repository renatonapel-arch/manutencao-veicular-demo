import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import EmptyState from '../components/EmptyState'

const MODELOS_SUGERIDOS = [
  'CG 160 FAN', 'CG 125 FAN KS', 'CG 125I FAN',
  'STRADA ENDURANCE CS', 'SAVEIRO CS RB MF', 'SAVEIRO 1.6 CS',
  'MONTANA', 'EMPILHADEIRA HYSTER',
]

interface PlanoForm {
  modelo_veiculo: string
  item: string
  descricao: string
  km_intervalo: number | null
  dias_intervalo: number | null
  antecedencia_dias: number
}

const planoVazio: PlanoForm = {
  modelo_veiculo: '',
  item: '',
  descricao: '',
  km_intervalo: null,
  dias_intervalo: null,
  antecedencia_dias: 7,
}

export default function PlanosPage() {
  const qc = useQueryClient()
  const [modalAberto, setModalAberto] = useState(false)
  const [form, setForm] = useState<PlanoForm>(planoVazio)
  const [erroForm, setErroForm] = useState('')

  const { data: planos } = useQuery({
    queryKey: ['planos'],
    queryFn: () => api.get('/planos').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (payload: PlanoForm) => api.post('/planos', {
      ...payload,
      km_intervalo: payload.km_intervalo || null,
      dias_intervalo: payload.dias_intervalo || null,
    }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['planos'] })
      setModalAberto(false)
      setForm(planoVazio)
      setErroForm('')
    },
    onError: (e: any) => setErroForm(e.response?.data?.detail || 'Erro ao salvar'),
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/planos/${id}`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['planos'] }),
  })

  const onSalvar = () => {
    setErroForm('')
    if (!form.modelo_veiculo.trim()) { setErroForm('Modelo obrigatório'); return }
    if (!form.item.trim()) { setErroForm('Item obrigatório'); return }
    if (!form.km_intervalo && !form.dias_intervalo) {
      setErroForm('Pelo menos 1 intervalo (km ou dias) é obrigatório'); return
    }
    createMut.mutate(form)
  }

  const onDelete = (id: number, modelo: string, item: string) => {
    if (confirm(`Apagar plano "${item}" do ${modelo}?`)) {
      deleteMut.mutate(id)
    }
  }

  return (
    <section>
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="text-lg font-semibold text-naval">Planos preventivos</div>
          <div className="text-xs text-ink-500">{planos?.length || 0} planos ativos</div>
        </div>
        <button
          onClick={() => { setForm(planoVazio); setErroForm(''); setModalAberto(true) }}
          className="bg-naval text-white px-3 py-1.5 rounded text-sm font-medium hover:bg-noite"
        >
          + Novo plano
        </button>
      </div>

      {planos && planos.length === 0 ? (
        <EmptyState
          titulo="Nenhum plano cadastrado"
          descricao="Cadastre planos preventivos por modelo de veículo. O sistema gera OS automática quando o km ou data atinge o intervalo."
          cta={
            <button
              onClick={() => { setForm(planoVazio); setErroForm(''); setModalAberto(true) }}
              className="bg-naval text-white px-4 py-2 rounded text-sm font-medium"
            >
              + Criar primeiro plano
            </button>
          }
        />
      ) : (
        <div className="bg-white border border-border rounded overflow-hidden">
          <table className="w-full text-[12px] dense">
            <thead className="bg-ink-50 text-ink-500 border-b border-border">
              <tr>
                <th className="text-left">Modelo</th>
                <th className="text-left">Item</th>
                <th className="text-right">Intervalo km</th>
                <th className="text-right">Intervalo dias</th>
                <th className="text-right">Antecedência</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(planos || []).map((p: any) => (
                <tr key={p.id} className="border-t border-border hover:bg-ink-50">
                  <td>{p.modelo_veiculo}</td>
                  <td>{p.item}</td>
                  <td className="text-right font-mono">{p.km_intervalo?.toLocaleString('pt-BR') || '—'}</td>
                  <td className="text-right font-mono">{p.dias_intervalo || '—'}</td>
                  <td className="text-right font-mono">{p.antecedencia_dias}d</td>
                  <td><span className={`badge ${p.ativo ? 'bg-success-bg text-success-fg' : 'bg-ink-200 text-ink-500'}`}>{p.ativo ? 'Ativo' : 'Inativo'}</span></td>
                  <td>
                    <button
                      onClick={() => onDelete(p.id, p.modelo_veiculo, p.item)}
                      className="text-ink-400 hover:text-danger-fg px-2"
                      title="Apagar plano"
                    >
                      🗑
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="text-[11px] text-ink-500 mt-2">
        💡 Planos rodam diariamente às 08:00 UTC via APScheduler. Quando km do veículo entra na janela, cria OS preventiva em status <b>aberta</b> e dispara alerta WhatsApp.
      </div>

      {/* Modal criar */}
      {modalAberto && (
        <div className="fixed inset-0 bg-noite/50 flex items-center justify-center z-50 p-4" onClick={(e) => { if (e.target === e.currentTarget) setModalAberto(false) }}>
          <div className="bg-white rounded-lg max-w-lg w-full p-5">
            <div className="text-lg font-semibold text-naval mb-3">+ Novo plano preventivo</div>

            <div className="space-y-3">
              <div>
                <label className="text-[11px] text-ink-500">Modelo do veículo <span className="text-danger">*</span></label>
                <input
                  type="text"
                  value={form.modelo_veiculo}
                  onChange={(e) => setForm({ ...form, modelo_veiculo: e.target.value })}
                  list="modelos-list"
                  placeholder="Ex: CG 160 FAN"
                  className="w-full px-3 py-2 border border-border-strong rounded text-sm"
                />
                <datalist id="modelos-list">
                  {MODELOS_SUGERIDOS.map(m => <option key={m} value={m} />)}
                </datalist>
              </div>

              <div>
                <label className="text-[11px] text-ink-500">Item / peça <span className="text-danger">*</span></label>
                <input
                  type="text"
                  value={form.item}
                  onChange={(e) => setForm({ ...form, item: e.target.value })}
                  placeholder="Ex: Filtro de ar"
                  className="w-full px-3 py-2 border border-border-strong rounded text-sm"
                />
              </div>

              <div>
                <label className="text-[11px] text-ink-500">Descrição (opcional)</label>
                <textarea
                  value={form.descricao}
                  onChange={(e) => setForm({ ...form, descricao: e.target.value })}
                  placeholder="Detalhes do plano..."
                  className="w-full px-3 py-2 border border-border-strong rounded text-sm h-16"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] text-ink-500">Intervalo km</label>
                  <input
                    type="number"
                    value={form.km_intervalo ?? ''}
                    onChange={(e) => setForm({ ...form, km_intervalo: e.target.value ? Number(e.target.value) : null })}
                    placeholder="Ex: 10000"
                    className="w-full px-3 py-2 border border-border-strong rounded text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-ink-500">Intervalo dias</label>
                  <input
                    type="number"
                    value={form.dias_intervalo ?? ''}
                    onChange={(e) => setForm({ ...form, dias_intervalo: e.target.value ? Number(e.target.value) : null })}
                    placeholder="Ex: 365"
                    className="w-full px-3 py-2 border border-border-strong rounded text-sm font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] text-ink-500">Antecedência do alerta (dias antes do trigger)</label>
                <input
                  type="number"
                  value={form.antecedencia_dias}
                  onChange={(e) => setForm({ ...form, antecedencia_dias: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-border-strong rounded text-sm font-mono"
                />
              </div>

              <div className="text-[11px] text-ink-500 bg-gelo border border-ceu-claro rounded p-2">
                💡 Pelo menos um intervalo (km <b>ou</b> dias) é obrigatório. Pode preencher os dois — o que acontecer primeiro dispara a preventiva.
              </div>

              {erroForm && (
                <div className="bg-danger-bg border border-danger text-danger-fg rounded p-2 text-sm">{erroForm}</div>
              )}
            </div>

            <div className="flex gap-2 justify-end mt-4">
              <button onClick={() => setModalAberto(false)} className="border border-border-strong bg-white px-3 py-1.5 rounded text-sm">Cancelar</button>
              <button
                onClick={onSalvar}
                disabled={createMut.isPending}
                className={`px-3 py-1.5 rounded text-sm font-medium text-white ${createMut.isPending ? 'bg-ink-300' : 'bg-naval hover:bg-noite'}`}
              >
                {createMut.isPending ? 'Salvando...' : 'Criar plano'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
