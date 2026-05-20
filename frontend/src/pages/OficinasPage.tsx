import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { FilialChip } from '../components/Badges'
import EmptyState from '../components/EmptyState'

const ESPECIALIDADES = ['moto', 'carro', 'caminhao', 'pneu', 'eletrica', 'empilhadeira', 'geral']
const UFS = ['PR', 'BA', 'SP', 'SC', 'RS', 'MG', 'RJ', 'GO', 'MT', 'MS', 'TO', 'DF']

interface OficinaForm {
  nome: string
  cnpj: string
  telefone: string
  cidade: string
  uf: string
  especialidade: string
  filial_id_preferencial: number | null
}

const vazia: OficinaForm = {
  nome: '', cnpj: '', telefone: '', cidade: '', uf: 'PR',
  especialidade: 'moto', filial_id_preferencial: null,
}

export default function OficinasPage() {
  const qc = useQueryClient()
  const [q, setQ] = useState('')
  const [modalAberto, setModalAberto] = useState(false)
  const [form, setForm] = useState<OficinaForm>(vazia)
  const [erro, setErro] = useState('')

  const { data: oficinas } = useQuery({
    queryKey: ['oficinas', q],
    queryFn: () => api.get('/oficinas' + (q ? `?q=${encodeURIComponent(q)}` : '')).then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (payload: OficinaForm) => api.post('/oficinas', {
      ...payload,
      filial_id_preferencial: payload.filial_id_preferencial || null,
    }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['oficinas'] })
      setModalAberto(false)
      setForm(vazia)
      setErro('')
    },
    onError: (e: any) => setErro(e.response?.data?.detail || 'Erro ao salvar'),
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/oficinas/${id}`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['oficinas'] }),
    onError: (e: any) => alert(e.response?.data?.detail || 'Erro ao desativar'),
  })

  const onSalvar = () => {
    setErro('')
    if (!form.nome.trim()) { setErro('Nome obrigatório'); return }
    if (form.nome.trim().length < 3) { setErro('Nome muito curto'); return }
    createMut.mutate(form)
  }

  const onDelete = (id: number, nome: string) => {
    if (confirm(`Desativar oficina "${nome}"? (não apaga histórico de OS)`)) {
      deleteMut.mutate(id)
    }
  }

  return (
    <section>
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="text-lg font-semibold text-naval">Catálogo de oficinas</div>
          <div className="text-xs text-ink-500">{oficinas?.length || 0} oficinas ativas · texto livre <b className="text-danger-fg">bloqueado</b></div>
        </div>
        <button
          onClick={() => { setForm(vazia); setErro(''); setModalAberto(true) }}
          className="bg-naval text-white px-3 py-1.5 rounded text-sm font-medium hover:bg-noite"
        >
          + Nova oficina
        </button>
      </div>

      <div className="bg-white border border-border rounded p-3 mb-3">
        <input
          className="border border-border-strong rounded px-2 py-1 w-64 text-xs"
          placeholder="🔍 Buscar nome / CNPJ / cidade"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      {oficinas && oficinas.length === 0 ? (
        <EmptyState
          titulo="Nenhuma oficina cadastrada"
          descricao="Cadastre oficinas que sua frota usa. Texto livre é bloqueado em todo o módulo — toda OS vai escolher daqui."
          cta={
            <button
              onClick={() => { setForm(vazia); setErro(''); setModalAberto(true) }}
              className="bg-naval text-white px-4 py-2 rounded text-sm font-medium"
            >
              + Cadastrar primeira oficina
            </button>
          }
        />
      ) : (
        <div className="bg-white border border-border rounded overflow-hidden">
          <table className="w-full text-[12px] dense">
            <thead className="bg-ink-50 text-ink-500 border-b border-border">
              <tr>
                <th className="text-left">Nome</th>
                <th className="text-left">CNPJ</th>
                <th className="text-left">Cidade/UF</th>
                <th className="text-left">Especialidade</th>
                <th className="text-left">Filial</th>
                <th className="text-right">Ticket médio</th>
                <th className="text-center">Avaliação</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(oficinas || []).map((o: any) => (
                <tr key={o.id} className="border-t border-border hover:bg-ink-50">
                  <td className="font-medium">{o.nome}</td>
                  <td className="font-mono text-[10px]">{o.cnpj || '—'}</td>
                  <td>{o.cidade ? `${o.cidade} / ${o.uf}` : '—'}</td>
                  <td><span className="badge bg-info-bg text-info-fg">{o.especialidade || '—'}</span></td>
                  <td>{o.filial_id_preferencial ? <FilialChip filialId={o.filial_id_preferencial}/> : '—'}</td>
                  <td className="text-right font-mono">{o.valor_servico_padrao ? `R$ ${Number(o.valor_servico_padrao).toFixed(0)}` : '—'}</td>
                  <td className="text-center text-warn">★ {o.avaliacao || '—'}</td>
                  <td><span className="badge bg-success-bg text-success-fg">Ativo</span></td>
                  <td>
                    <button
                      onClick={() => onDelete(o.id, o.nome)}
                      className="text-ink-400 hover:text-danger-fg px-2"
                      title="Desativar oficina"
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

      {/* Modal criar */}
      {modalAberto && (
        <div className="fixed inset-0 bg-noite/50 flex items-center justify-center z-50 p-4" onClick={(e) => { if (e.target === e.currentTarget) setModalAberto(false) }}>
          <div className="bg-white rounded-lg max-w-lg w-full p-5">
            <div className="text-lg font-semibold text-naval mb-3">+ Nova oficina</div>

            <div className="space-y-3">
              <div>
                <label className="text-[11px] text-ink-500">Nome <span className="text-danger">*</span></label>
                <input
                  type="text"
                  value={form.nome}
                  onChange={(e) => setForm({ ...form, nome: e.target.value })}
                  placeholder="Ex: DIDA MOTOS"
                  className="w-full px-3 py-2 border border-border-strong rounded text-sm"
                  autoFocus
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] text-ink-500">CNPJ</label>
                  <input
                    type="text"
                    value={form.cnpj}
                    onChange={(e) => setForm({ ...form, cnpj: e.target.value })}
                    placeholder="00.000.000/0001-00"
                    className="w-full px-3 py-2 border border-border-strong rounded text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-ink-500">Telefone</label>
                  <input
                    type="text"
                    value={form.telefone}
                    onChange={(e) => setForm({ ...form, telefone: e.target.value })}
                    placeholder="+55 44 99999-0000"
                    className="w-full px-3 py-2 border border-border-strong rounded text-sm font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className="text-[11px] text-ink-500">Cidade</label>
                  <input
                    type="text"
                    value={form.cidade}
                    onChange={(e) => setForm({ ...form, cidade: e.target.value })}
                    placeholder="Ex: Maringá"
                    className="w-full px-3 py-2 border border-border-strong rounded text-sm"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-ink-500">UF</label>
                  <select
                    value={form.uf}
                    onChange={(e) => setForm({ ...form, uf: e.target.value })}
                    className="w-full px-3 py-2 border border-border-strong rounded text-sm bg-white"
                  >
                    {UFS.map(u => <option key={u} value={u}>{u}</option>)}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] text-ink-500">Especialidade</label>
                  <select
                    value={form.especialidade}
                    onChange={(e) => setForm({ ...form, especialidade: e.target.value })}
                    className="w-full px-3 py-2 border border-border-strong rounded text-sm bg-white"
                  >
                    {ESPECIALIDADES.map(esp => <option key={esp} value={esp}>{esp}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] text-ink-500">Filial preferencial</label>
                  <select
                    value={form.filial_id_preferencial ?? ''}
                    onChange={(e) => setForm({ ...form, filial_id_preferencial: e.target.value ? Number(e.target.value) : null })}
                    className="w-full px-3 py-2 border border-border-strong rounded text-sm bg-white"
                  >
                    <option value="">(nenhuma)</option>
                    <option value="1">Maringá (100)</option>
                    <option value="2">Ponta Grossa (700)</option>
                    <option value="3">LEM (900)</option>
                  </select>
                </div>
              </div>

              <div className="text-[11px] text-ink-500 bg-gelo border border-ceu-claro rounded p-2">
                💡 Toda OS no módulo vai escolher daqui — texto livre <b>bloqueado</b>. Pra desativar uma oficina sem apagar histórico, use o ícone 🗑 na lista.
              </div>

              {erro && (
                <div className="bg-danger-bg border border-danger text-danger-fg rounded p-2 text-sm">{erro}</div>
              )}
            </div>

            <div className="flex gap-2 justify-end mt-4">
              <button onClick={() => setModalAberto(false)} className="border border-border-strong bg-white px-3 py-1.5 rounded text-sm">Cancelar</button>
              <button
                onClick={onSalvar}
                disabled={createMut.isPending}
                className={`px-3 py-1.5 rounded text-sm font-medium text-white ${createMut.isPending ? 'bg-ink-300' : 'bg-naval hover:bg-noite'}`}
              >
                {createMut.isPending ? 'Salvando...' : 'Criar oficina'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
