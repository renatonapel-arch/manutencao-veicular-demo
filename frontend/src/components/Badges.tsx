const ST_LABELS: Record<string, string> = {
  rascunho: 'Rascunho',
  aberta: 'Aberta',
  em_triagem: 'Em triagem',
  aguardando_orcamento: 'Aguard. orçamento',
  aguardando_aprovacao: 'Aguard. aprovação',
  em_execucao: 'Em execução',
  aguardando_peca: 'Aguard. peça',
  encerrada: 'Encerrada',
  cancelada: 'Cancelada',
}

const TP_LABELS: Record<string, string> = {
  corretiva_manual: 'Corretiva',
  corretiva_checklist: 'Corretiva (chk)',
  preventiva_automatica: 'Preventiva',
  devolucao: 'Devolução',
  sinistro: 'Sinistro',
  recall: 'Recall',
}

const SRC_LABELS: Record<string, string> = {
  os_manutencao: '🔧 OS Manutenção',
  troca_oleo: '🛢️ Troca de Óleo',
  checklist_v2: '✅ Checklist (V2)',
  patrimonial: '📋 Patrimonial',
}

export const StatusBadge = ({ status }: { status: string }) => (
  <span className={`badge st-${status}`}>{ST_LABELS[status] || status}</span>
)

export const TipoBadge = ({ tipo }: { tipo: string }) => (
  <span className={`badge tp-${tipo}`}>{TP_LABELS[tipo] || tipo}</span>
)

const FILIAL_CODIGO: Record<number, string> = {
  1: '100', 2: '700', 3: '900',
  5: 'DIR',  // Diretoria/executiva — carros de gestor não vinculados às lojas
}

export const FilialChip = ({ filialId }: { filialId: number }) => {
  const codigo = FILIAL_CODIGO[filialId] ?? String(filialId)
  return <span className={`badge fil-${filialId}`}>{codigo}</span>
}

export const SourceBadge = ({ source }: { source: string }) => (
  <span className={`badge src-${source}`}>{SRC_LABELS[source] || source}</span>
)

export const fmtBRL = (v: number | string | null | undefined) => {
  const n = typeof v === 'string' ? parseFloat(v) : (v ?? 0)
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

export const fmtKm = (v: number | null | undefined) => (v ?? 0).toLocaleString('pt-BR')

export const fmtData = (iso: string | null | undefined) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

export const fmtDataHora = (iso: string | null | undefined) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}
