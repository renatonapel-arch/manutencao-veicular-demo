interface Props {
  icon?: string
  titulo: string
  descricao?: string
  cta?: React.ReactNode
}

export default function EmptyState({ icon = '📭', titulo, descricao, cta }: Props) {
  return (
    <div className="bg-white border border-border rounded p-10 text-center">
      <svg viewBox="0 0 200 160" className="w-40 h-32 mx-auto mb-3">
        <circle cx="100" cy="70" r="50" fill="#EBF7FA" stroke="#B5D4E8" strokeWidth="2"/>
        <path d="M 80 70 L 95 85 L 125 55" stroke="#10B981" strokeWidth="4" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        <ellipse cx="100" cy="135" rx="40" ry="4" fill="#D6E7F1"/>
      </svg>
      <div className="text-base font-medium text-naval mb-1">{titulo}</div>
      {descricao && <div className="text-xs text-ink-500 mb-3">{descricao}</div>}
      {cta && <div className="mt-3">{cta}</div>}
    </div>
  )
}
