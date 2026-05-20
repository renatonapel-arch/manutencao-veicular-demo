const ST_LABELS: Record<string, string> = {
  rascunho: 'Rascunho',
  aberta: 'Aberta',
  aguardando_anexos: 'Aguard. anexos',
  pronta_execucao: 'Pronta',
  em_execucao: 'Em execução',
  encerrada: 'Encerrada',
  cancelada: 'Cancelada',
}

const TP_LABELS: Record<string, string> = {
  corretiva_manual: 'Corretiva',
  corretiva_checklist: 'Corretiva (chk)',
  preventiva_automatica: 'Preventiva',
  devolucao: 'Devolução',
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

export const FilialChip = ({ filialId }: { filialId: number }) => {
  const codigo = filialId === 1 ? '100' : filialId === 2 ? '700' : filialId === 3 ? '900' : String(filialId)
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
