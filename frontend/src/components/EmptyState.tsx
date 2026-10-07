interface Props {
  icon?: string
  titulo: string
  descricao?: string
  cta?: React.ReactNode
}

export default function EmptyState({ icon = '📭', titulo, descricao, cta }: Props) {
  return (
    <div className="bg-nv-surface border border-nv-border rounded p-10 text-center">
      <svg viewBox="0 0 200 160" className="w-40 h-32 mx-auto mb-3">
        <circle cx="100" cy="70" r="50" fill="#113C58" stroke="#27557A" strokeWidth="2"/>
        <path d="M 80 70 L 95 85 L 125 55" stroke="#34D399" strokeWidth="4" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        <ellipse cx="100" cy="135" rx="40" ry="4" fill="#113C58"/>
      </svg>
      <div className="text-base font-medium text-nv-ink mb-1">{titulo}</div>
      {descricao && <div className="text-xs text-nv-soft mb-3">{descricao}</div>}
      {cta && <div className="mt-3">{cta}</div>}
    </div>
  )
}
