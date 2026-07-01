import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { fmtBRL, fmtDataHora, FilialChip, StatusBadge, TipoBadge } from '../components/Badges'

// v3: cada transição vira POST /ordem-servico/{id}/{acao} — máquina de 9 estados
const TRANSICOES_ACAO: { de: string; acao: string; label: string; cor: string; precisaMotivo?: boolean }[] = [
  { de: 'rascunho',              acao: 'abrir',                label: 'Abrir OS',            cor: 'btn-outline' },
  { de: 'aberta',                acao: 'triagem',              label: 'Iniciar triagem',     cor: 'btn-outline' },
  { de: 'em_triagem',            acao: 'enviar-orcamento',     label: 'Enviar p/ orçamento', cor: 'btn-outline' },
  { de: 'aguardando_orcamento',  acao: 'submeter-orcamento',   label: 'Submeter orçamento',  cor: 'btn-primary' },
  { de: 'aguardando_aprovacao',  acao: 'aprovar',              label: '✓ Aprovar',           cor: 'btn-ok' },
  { de: 'aguardando_aprovacao',  acao: 'pedir-2o-orcamento',   label: 'Pedir 2º orçamento',  cor: 'btn-outline', precisaMotivo: true },
  { de: 'aguardando_aprovacao',  acao: 'reprovar',             label: '✗ Reprovar',          cor: 'btn-err', precisaMotivo: true },
  { de: 'em_execucao',           acao: 'aguardando-peca',      label: 'Aguardando peça',     cor: 'btn-outline' },
  { de: 'aguardando_peca',       acao: 'retomar-execucao',     label: 'Retomar execução',    cor: 'btn-outline' },
  { de: 'em_execucao',           acao: 'encerrar',             label: '🔒 Encerrar',         cor: 'btn-ok' },
]

export default function DetalheOSPage() {
  const { id } = useParams()
  const nav = useNavigate()
  const qc = useQueryClient()
  const [modalAlerta, setModalAlerta] = useState(false)
  const [tipoAlerta, setTipoAlerta] = useState('manual')

  const { data: os, isLoading } = useQuery({
    queryKey: ['os', id],
    queryFn: () => api.get(`/ordem-servico/${id}`).then(r => r.data),
  })

  const patchMut = useMutation({
    mutationFn: (payload: any) => api.patch(`/ordem-servico/${id}`, payload).then(r => r.data),
    onSuccess: () => qc.invalidateQueries(),  // refresca OS + Dashboard + listas + timeline
    onError: (e: any) => alert(e.response?.data?.detail || 'Erro ao atualizar'),
  })

  // v3: transições viram POST /ordem-servico/{id}/{acao}
  const transicaoMut = useMutation({
    mutationFn: ({ acao, motivo }: { acao: string; motivo?: string }) => {
      const qs = motivo ? `?motivo=${encodeURIComponent(motivo)}` : ''
      return api.post(`/ordem-servico/${id}/${acao}${qs}`).then(r => r.data)
    },
    onSuccess: () => qc.invalidateQueries(),
    onError: (e: any) => alert(e.response?.data?.detail || 'Erro na transição'),
  })

  const executarTransicao = (acao: string, precisaMotivo?: boolean) => {
    let motivo: string | undefined
    if (precisaMotivo) {
      motivo = window.prompt('Motivo (obrigatório):') || undefined
      if (!motivo) return
    }
    transicaoMut.mutate({ acao, motivo })
  }

  const uploadMut = useMutation({
    mutationFn: ({ tipo, file }: { tipo: string, file: File }) => {
      const form = new FormData()
      form.append('tipo', tipo)
      form.append('arquivo', file)
      return api.post(`/upload/os/${id}/anexos`, form, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }).then(r => r.data)
    },
    onSuccess: () => qc.invalidateQueries(),
    onError: (e: any) => alert(e.response?.data?.detail || 'Erro no upload'),
  })

  const dispatchMut = useMutation({
    mutationFn: () => api.post('/alertas/dispatch', {
      os_id: Number(id),
      tipo_alerta: tipoAlerta,
      telefone: '+5544999990000',
    }).then(r => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries()
      alert(`Alerta enviado (mock):\n\n${data.mensagem}`)
      setModalAlerta(false)
    },
  })

  if (isLoading || !os) return <div className="text-ink-500">Carregando OS #{id}…</div>

  const temNF = (os.anexos || []).some((a: any) => a.tipo === 'nf')
  const temFoto = (os.anexos || []).some((a: any) => a.tipo === 'foto_hodometro' || a.tipo === 'foto_problema')
  const podeEncerrar = temNF && temFoto && (os.itens || []).length > 0

  const acoesDisponiveis = TRANSICOES_ACAO.filter(t => t.de === os.status)

  return (
    <section>
      <div className="flex justify-between items-start mb-3 gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <Link to="/os" className="text-ink-400 hover:text-naval">← Voltar</Link>
          <div className="text-lg font-semibold font-mono text-naval">OS #{os.id}</div>
          <StatusBadge status={os.status}/>
          <TipoBadge tipo={os.tipo_os}/>
          <span className="text-xs text-ink-500">Aberta em {fmtDataHora(os.data_abertura)}</span>
        </div>
        <div className="flex gap-2 flex-wrap justify-end">
          <button onClick={() => setModalAlerta(true)} className="btn btn-outline">📲 Alerta WhatsApp</button>
          {acoesDisponiveis.map(a => {
            const disabled = a.acao === 'encerrar' && !podeEncerrar
            return (
              <button
                key={a.acao}
                disabled={disabled || transicaoMut.isPending}
                onClick={() => executarTransicao(a.acao, a.precisaMotivo)}
                className={`btn ${a.cor}`}
                title={disabled ? 'Falta NF/foto anexada' : ''}
              >
                {a.label}
              </button>
            )
          })}
          {!['encerrada', 'cancelada'].includes(os.status) && (
            <button
              onClick={() => executarTransicao('cancelar', true)}
              className="btn btn-err"
            >
              Cancelar OS
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2 space-y-3">
          {/* Veículo */}
          <div className="card p-5">
            <div className="kpi-label mb-3">1 · Veículo</div>
            <div className="grid grid-cols-4 gap-3 text-[12px]">
              <div className="col-span-2">
                <label className="text-[11px] text-ink-500">Veículo</label>
                <div className="px-2 py-1.5 border border-border-strong rounded bg-ink-50 font-mono font-medium">{os.veiculo?.placa} · {os.veiculo?.modelo}</div>
              </div>
              <div>
                <label className="text-[11px] text-ink-500">Filial</label>
                <div className="px-2 py-1.5 border border-border-strong rounded bg-ink-50"><FilialChip filialId={os.filial_id}/></div>
              </div>
              <div>
                <label className="text-[11px] text-ink-500">CRLV</label>
                <div className="px-2 py-1.5 border border-border-strong rounded bg-ink-50 text-success-fg font-mono">
                  {os.veiculo?.vencimento_crlv || '—'} ✓
                </div>
              </div>
              <div>
                <label className="text-[11px] text-ink-500">KM API</label>
                <div className="px-2 py-1.5 border border-border-strong rounded bg-ink-50 text-ink-500 font-mono">{os.km_api_snapshot?.toLocaleString('pt-BR') || '—'}</div>
              </div>
              <div>
                <label className="text-[11px] text-ink-500">KM lido</label>
                <div className="px-2 py-1.5 border border-border-strong rounded bg-warn-bg font-mono font-medium">{os.km_veiculo.toLocaleString('pt-BR')}</div>
              </div>
              <div className="col-span-2">
                <label className="text-[11px] text-ink-500">Oficina</label>
                <div className="px-2 py-1.5 border border-border-strong rounded bg-white font-medium">{os.oficina?.nome || '—'}</div>
              </div>
            </div>
          </div>

          {/* Descrição */}
          <div className="card p-5">
            <div className="kpi-label mb-3">2 · Problema reportado</div>
            <div className="text-[13px]">{os.descricao_problema || '—'}</div>
          </div>

          {/* Itens */}
          <div className="card p-5">
            <div className="kpi-label mb-3">3 · Itens</div>
            <table className="w-full text-[12px] dense">
              <thead className="bg-ink-50 text-ink-500 border-y border-border">
                <tr>
                  <th className="text-left">Tipo</th>
                  <th className="text-left">Descrição</th>
                  <th className="text-right">Qtd</th>
                  <th className="text-right">Valor</th>
                  <th className="text-right">Subtotal</th>
                </tr>
              </thead>
              <tbody>
                {(os.itens || []).map((it: any) => (
                  <tr key={it.id} className="border-t border-border">
                    <td><span className="badge bg-info-bg text-info-fg">{it.tipo_item}</span></td>
                    <td>{it.descricao}{it.sige_sku && <span className="text-success-fg text-[10px] block">💡 SKU {it.sige_sku}</span>}</td>
                    <td className="text-right font-mono">{Number(it.quantidade).toLocaleString('pt-BR')}</td>
                    <td className="text-right font-mono">{fmtBRL(it.valor_unitario)}</td>
                    <td className="text-right font-medium font-mono">{fmtBRL(it.subtotal)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="border-t-2 border-border-strong">
                <tr className="font-semibold bg-ink-50">
                  <td colSpan={4} className="text-right pr-2">Total</td>
                  <td className="text-right text-base font-mono text-naval">{fmtBRL(os.valor_total)}</td>
                </tr>
              </tfoot>
            </table>
          </div>

          {/* Anexos */}
          <div className="card p-5">
            <div className="kpi-label mb-3">4 · Anexos</div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-[11px] font-medium mb-1.5">📷 Fotos <span className={temFoto ? 'text-success-fg' : 'text-ink-400'}>({(os.anexos || []).filter((a: any) => a.tipo.startsWith('foto')).length})</span></div>
                <div className="grid grid-cols-3 gap-1.5">
                  {(os.anexos || []).filter((a: any) => a.tipo.startsWith('foto')).map((a: any) => (
                    <div key={a.id} className="aspect-square bg-ink-200 rounded border flex items-center justify-center text-3xl">📷</div>
                  ))}
                  <label className="aspect-square border-2 border-dashed border-border-strong rounded flex flex-col items-center justify-center text-ink-500 text-[10px] cursor-pointer hover:bg-gelo">
                    <span className="text-2xl">+</span>Foto
                    <input type="file" accept="image/*" capture="environment" className="hidden"
                           onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadMut.mutate({ tipo: 'foto_hodometro', file: f }) }}/>
                  </label>
                </div>
              </div>
              <div>
                <div className="text-[11px] font-medium mb-1.5">📄 NF <span className={temNF ? 'text-success-fg' : 'text-danger-fg'}>{temNF ? '✓' : '(obrigatória)'}</span></div>
                <label className={`aspect-[3/1] w-full border-2 border-dashed rounded flex flex-col items-center justify-center cursor-pointer ${temNF ? 'border-success bg-success-bg/30' : 'border-danger bg-danger-bg/20'}`}>
                  <span className="text-3xl">📄</span>
                  <span className="font-medium text-sm mt-1">{temNF ? 'NF anexada' : 'Anexar NF'}</span>
                  <span className="text-[9px] text-ink-400">PDF · JPG · ≤20MB</span>
                  <input type="file" accept="image/*,application/pdf" className="hidden"
                         onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadMut.mutate({ tipo: 'nf', file: f }) }}/>
                </label>
              </div>
            </div>
            {uploadMut.isPending && <div className="text-xs text-warn-fg mt-2">⏳ Enviando...</div>}
          </div>
        </div>

        {/* Sidebar histórico */}
        <div className="card p-5 self-start">
          <div className="kpi-label mb-3">Validação para encerrar</div>
          <div className="space-y-1.5 text-[12px]">
            <div className={`flex items-center gap-2 ${temFoto ? 'text-success-fg' : 'text-ink-400'}`}>
              {temFoto ? '✓' : '✗'} Foto anexada
            </div>
            <div className={`flex items-center gap-2 ${temNF ? 'text-success-fg' : 'text-danger-fg'}`}>
              {temNF ? '✓' : '✗'} NF/comprovante
            </div>
            <div className={`flex items-center gap-2 ${(os.itens || []).length > 0 ? 'text-success-fg' : 'text-danger-fg'}`}>
              {(os.itens || []).length > 0 ? '✓' : '✗'} Pelo menos 1 item
            </div>
            <div className={`flex items-center gap-2 ${os.km_veiculo > 0 ? 'text-success-fg' : 'text-danger-fg'}`}>
              {os.km_veiculo > 0 ? '✓' : '✗'} KM lido informado
            </div>
          </div>
          {podeEncerrar && os.status === 'em_execucao' && (
            <button onClick={() => executarTransicao('encerrar')} className="btn btn-ok w-full mt-3 justify-center">
              🔒 Encerrar OS
            </button>
          )}
          {os.motivo_aprovacao && (
            <div className={`mt-3 text-[11px] rounded px-2 py-1.5 ${os.motivo_aprovacao === 'auto' ? 'bg-info-bg text-info-fg' : 'bg-success-bg text-success-fg'}`}>
              {os.motivo_aprovacao === 'auto' ? '⚡ Auto-aprovada (abaixo do teto)' : '✓ Aprovada manualmente'}
            </div>
          )}
        </div>
      </div>

      {/* Modal Alerta */}
      {modalAlerta && (
        <div className="fixed inset-0 bg-noite/50 flex items-center justify-center z-50 p-4" onClick={(e) => { if (e.target === e.currentTarget) setModalAlerta(false) }}>
          <div className="bg-white rounded-lg max-w-lg w-full p-5">
            <div className="text-lg font-semibold text-naval mb-3">📲 Enviar alerta WhatsApp</div>
            <div className="mb-3">
              <label className="text-[11px] text-ink-500">Template</label>
              <select value={tipoAlerta} onChange={(e) => setTipoAlerta(e.target.value)}
                      className="w-full px-2 py-1.5 border border-border-strong rounded bg-white text-sm">
                <option value="manual">Manual — atualização</option>
                <option value="os_aberta_dias">OS atrasada (+5d)</option>
                <option value="preventiva_proxima">Preventiva próxima</option>
                <option value="solicitar_nf">Solicitar NF à oficina</option>
                <option value="custo_fora_padrao">Custo anômalo</option>
              </select>
            </div>
            <div className="bg-success-bg border border-success rounded p-3 mb-3 text-xs">
              <div className="text-[10px] uppercase text-success-fg font-medium mb-1">Mock no MVP (EVOLUTION_ENABLED=false)</div>
              <div className="text-ink-500">A integração real entra na Fase 2 com fila Redis + DLQ.</div>
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setModalAlerta(false)} className="border border-border-strong bg-white px-3 py-1.5 rounded text-sm">Cancelar</button>
              <button onClick={() => dispatchMut.mutate()} className="bg-success text-white px-3 py-1.5 rounded text-sm font-medium">Enviar (mock)</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
