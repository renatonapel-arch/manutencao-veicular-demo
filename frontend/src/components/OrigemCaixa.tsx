import { fmtBRL } from './Badges'

/**
 * OS que nasceu de uma compra do Caixa Interno (#0233): chip na lista e card no
 * detalhe. A compra de manutenção feita no Caixa chega aqui como OS ABERTA para o
 * gestor conferir, dar continuidade (triagem, oficina…) ou cancelar.
 */

export const ehCaixa = (os: any) => os?.origem === 'caixa_interno'

export const OrigemChip = ({ os }: { os: any }) =>
  ehCaixa(os) ? <span className="pill pill-warn" title="Compra do Caixa Interno — conferir">Caixa</span> : null

// "2026-10-05" → "05/10/2026" (sem passar por Date: data pura vira a véspera no fuso do Brasil)
const diaBR = (iso?: string | null) => (iso ? iso.slice(0, 10).split('-').reverse().join('/') : null)

type Props = {
  os: any
  podeConferir: boolean
  conferindo: boolean
  onConferir: () => void
  className?: string
}

export function OrigemCaixaCard({ os, podeConferir, conferindo, onConferir, className = '' }: Props) {
  if (!ehCaixa(os)) return null
  const d = os.origem_dados || {}
  const ativa = !['encerrada', 'cancelada'].includes(os.status)
  const nota = d.kind === 'sem_nota'
    ? `Sem nota fiscal${d.motivo ? ` — ${d.motivo}` : ''}`
    : (d.doc_ref ? `Chave ${d.doc_ref}` : 'Com nota fiscal (fica no Caixa)')
  const linhas: [string, string | null][] = [
    ['Comprado por', d.funcionario_nome || null],
    ['Data da compra', diaBR(d.data)],
    ['Emitente', [d.emitente, d.emitente_cnpj].filter(Boolean).join(' · ') || null],
    ['Valor', d.valor_total != null ? fmtBRL(d.valor_total) : null],
    ['Nota fiscal', nota],
  ]

  return (
    <div className={`bg-white border border-line border-l-4 border-l-[#E0A100] rounded-lg p-3 ${className}`}>
      <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
        <div className="text-[10px] uppercase tracking-wider text-ink-500">Origem · Compra no Caixa Interno</div>
        {d.link_compra && (
          <a href={d.link_compra} target="_blank" rel="noopener noreferrer" className="text-xs text-naval hover:underline"
             title="Só abre para quem tem acesso ao Caixa Interno">
            Ver a compra ↗
          </a>
        )}
      </div>
      {d.descricao && <div className="text-[13px] font-medium mb-2">{d.descricao}</div>}
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[12px]">
        {linhas.filter(([, v]) => v).map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-ink-500">{k}</dt>
            <dd className="break-words">{v}</dd>
          </div>
        ))}
      </dl>
      {ativa && (
        <div className="mt-3 pt-3 border-t border-line">
          <div className="text-[12px] text-ink-500 mb-2">
            Confira se é manutenção do veículo. <b>Conferido</b> encerra esta OS (sem pedir foto/NF); ou siga o
            atendimento normalmente; ou cancele se não for manutenção.
          </div>
          {podeConferir && (
            <button
              type="button"
              onClick={onConferir}
              disabled={conferindo}
              className="bg-success text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-40"
            >
              {conferindo ? 'Enviando…' : '✓ Conferido'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
