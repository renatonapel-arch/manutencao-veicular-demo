import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { DataTable } from '../components/DataTable'
import EmptyState from '../components/EmptyState'

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

  // Modelos disponíveis = modelos únicos dos veículos cadastrados na frota
  const { data: veiculos } = useQuery({
    queryKey: ['veiculos-modelos'],
    queryFn: () => api.get('/veiculos').then(r => r.data),
  })

  const modelosDisponiveis = useMemo(() => {
    const set = new Set<string>()
    for (const v of veiculos || []) {
      if (v.modelo) set.add(v.modelo)
    }
    return Array.from(set).sort()
  }, [veiculos])

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
          <div className="text-lg font-semibold text-nv-primary">Planos preventivos</div>
          <div className="text-xs text-nv-soft">{planos?.length || 0} planos ativos</div>
        </div>
        <button
          onClick={() => { setForm(planoVazio); setErroForm(''); setModalAberto(true) }}
          className="bg-nv-primary text-nv-bg px-3 py-1.5 rounded text-sm font-medium hover:bg-nv-primary-hover"
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
              className="bg-nv-primary text-nv-bg px-4 py-2 rounded text-sm font-medium hover:bg-nv-primary-hover"
            >
              + Criar primeiro plano
            </button>
          }
        />
      ) : (
        <div className="card overflow-hidden">
          <DataTable
            data={planos || []}
            rowKey={(p: any) => p.id}
            emptyMessage="Nenhum plano cadastrado."
            columns={[
              {
                key: 'modelo_veiculo', label: 'Modelo',
                accessor: (p: any) => p.modelo_veiculo || '', filter: true,
                render: (p: any) => p.modelo_veiculo,
              },
              {
                key: 'item', label: 'Item',
                accessor: (p: any) => p.item || '', filter: true,
                render: (p: any) => p.item,
              },
              {
                key: 'km_intervalo', label: 'Intervalo km', align: 'right',
                accessor: (p: any) => Number(p.km_intervalo || 0),
                cellClassName: 'font-mono num',
                render: (p: any) => p.km_intervalo?.toLocaleString('pt-BR') || '—',
              },
              {
                key: 'dias_intervalo', label: 'Intervalo dias', align: 'right',
                accessor: (p: any) => Number(p.dias_intervalo || 0),
                cellClassName: 'font-mono num',
                render: (p: any) => p.dias_intervalo || '—',
              },
              {
                key: 'antecedencia_dias', label: 'Antecedência', align: 'right',
                accessor: (p: any) => Number(p.antecedencia_dias || 0),
                cellClassName: 'font-mono num',
                render: (p: any) => `${p.antecedencia_dias}d`,
              },
              {
                key: 'ativo', label: 'Status',
                accessor: (p: any) => p.ativo ? 'Ativo' : 'Inativo', filter: true,
                render: (p: any) => <span className={`pill ${p.ativo ? 'pill-ok' : 'pill-gray'}`}>{p.ativo ? 'Ativo' : 'Inativo'}</span>,
              },
              {
                key: 'acoes', label: '',
                render: (p: any) => (
                  <button
                    onClick={(e) => { e.stopPropagation(); onDelete(p.id, p.modelo_veiculo, p.item) }}
                    className="text-nv-soft hover:text-nv-danger-text px-2 text-xs font-semibold"
                    title="Apagar plano"
                  >
                    Remover
                  </button>
                ),
              },
            ]}
          />
        </div>
      )}

      <div className="text-[11px] text-nv-soft mt-2">
        💡 Planos rodam diariamente às 08:00 UTC via APScheduler. Quando km do veículo entra na janela, cria OS preventiva em status <b>aberta</b> e dispara alerta WhatsApp.
      </div>

      {/* Modal criar */}
      {modalAberto && (
        <div className="fixed inset-0 bg-[rgba(2,15,26,.7)] flex items-center justify-center z-50 p-4" onClick={(e) => { if (e.target === e.currentTarget) setModalAberto(false) }}>
          <div className="bg-nv-surface rounded-lg max-w-lg w-full p-5">
            <div className="text-lg font-semibold text-nv-primary mb-3">+ Novo plano preventivo</div>

            <div className="space-y-3">
              <div>
                <label className="text-[11px] text-nv-soft">Modelo do veículo <span className="text-nv-danger-text">*</span></label>
                <select
                  value={form.modelo_veiculo}
                  onChange={(e) => setForm({ ...form, modelo_veiculo: e.target.value })}
                  className="w-full px-3 py-2 border border-nv-border-strong rounded text-sm bg-nv-surface"
                >
                  <option value="">— escolha o modelo da frota —</option>
                  {modelosDisponiveis.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
                <div className="text-[10px] text-nv-soft mt-1">
                  {modelosDisponiveis.length} modelos distintos cadastrados no Controle Patrimonial · texto livre <b className="text-nv-danger-text">bloqueado</b>
                </div>
              </div>

              <div>
                <label className="text-[11px] text-nv-soft">Item / peça <span className="text-nv-danger-text">*</span></label>
                <input
                  type="text"
                  value={form.item}
                  onChange={(e) => setForm({ ...form, item: e.target.value })}
                  placeholder="Ex: Filtro de ar"
                  className="w-full px-3 py-2 border border-nv-border-strong rounded text-sm"
                />
              </div>

              <div>
                <label className="text-[11px] text-nv-soft">Descrição (opcional)</label>
                <textarea
                  value={form.descricao}
                  onChange={(e) => setForm({ ...form, descricao: e.target.value })}
                  placeholder="Detalhes do plano..."
                  className="w-full px-3 py-2 border border-nv-border-strong rounded text-sm h-16"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] text-nv-soft">Intervalo km</label>
                  <input
                    type="number"
                    value={form.km_intervalo ?? ''}
                    onChange={(e) => setForm({ ...form, km_intervalo: e.target.value ? Number(e.target.value) : null })}
                    placeholder="Ex: 10000"
                    className="w-full px-3 py-2 border border-nv-border-strong rounded text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-nv-soft">Intervalo dias</label>
                  <input
                    type="number"
                    value={form.dias_intervalo ?? ''}
                    onChange={(e) => setForm({ ...form, dias_intervalo: e.target.value ? Number(e.target.value) : null })}
                    placeholder="Ex: 365"
                    className="w-full px-3 py-2 border border-nv-border-strong rounded text-sm font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] text-nv-soft">Antecedência do alerta (dias antes do trigger)</label>
                <input
                  type="number"
                  value={form.antecedencia_dias}
                  onChange={(e) => setForm({ ...form, antecedencia_dias: Number(e.target.value) })}
                  className="w-full px-3 py-2 border border-nv-border-strong rounded text-sm font-mono"
                />
              </div>

              <div className="text-[11px] text-nv-soft bg-nv-surface-2 border border-nv-border-strong rounded p-2">
                💡 Pelo menos um intervalo (km <b>ou</b> dias) é obrigatório. Pode preencher os dois — o que acontecer primeiro dispara a preventiva.
              </div>

              {erroForm && (
                <div className="bg-nv-danger-bg border border-nv-danger text-nv-danger-text rounded p-2 text-sm">{erroForm}</div>
              )}
            </div>

            <div className="flex gap-2 justify-end mt-4">
              <button onClick={() => setModalAberto(false)} className="border border-nv-border-strong bg-nv-surface px-3 py-1.5 rounded text-sm">Cancelar</button>
              <button
                onClick={onSalvar}
                disabled={createMut.isPending}
                className={`px-3 py-1.5 rounded text-sm font-medium ${createMut.isPending ? 'bg-nv-surface-2 text-nv-soft' : 'bg-nv-primary text-nv-bg hover:bg-nv-primary-hover'}`}
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
