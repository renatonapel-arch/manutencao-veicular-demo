/**
 * Ícones SVG inline (estilo Lucide) — sprite do mockup aprovado.
 * Zero emoji como ícone (regra do playbook UI/UX Napel).
 *
 * Uso: <Icon name="wrench" size={16} className="text-sky-500" />
 */

const PATHS: Record<string, JSX.Element> = {
  grid: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </>
  ),
  wrench: (
    <>
      <path d="M14.7 6.3a4 4 0 1 1 5 5l-8.5 8.5a2.5 2.5 0 0 1-3.5-3.5l7-7" />
      <path d="M15 9l3 3" />
    </>
  ),
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 9h18M8 3v4M16 3v4" />
    </>
  ),
  store: (
    <>
      <path d="M3 9l1.5-5h15L21 9" />
      <path d="M4 9v11h16V9" />
      <path d="M9 20v-6h6v6" />
    </>
  ),
  bell: (
    <>
      <path d="M6 8a6 6 0 0 1 12 0v5l1.5 3h-15L6 13z" />
      <path d="M10 19a2 2 0 0 0 4 0" />
    </>
  ),
  phone: (
    <>
      <rect x="6" y="2" width="12" height="20" rx="3" />
      <path d="M11 18h2" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-3.5-3.5" />
    </>
  ),
  filter: <path d="M3 5h18l-7 9v5l-4 2v-7z" />,
  download: (
    <>
      <path d="M12 3v13" />
      <path d="M7 12l5 5 5-5" />
      <path d="M4 20h16" />
    </>
  ),
  'arrow-up': (
    <>
      <path d="M12 19V5" />
      <path d="M5 12l7-7 7 7" />
    </>
  ),
  'arrow-down': (
    <>
      <path d="M12 5v14" />
      <path d="M5 12l7 7 7-7" />
    </>
  ),
  'chevron-right': <path d="M9 6l6 6-6 6" />,
  'chevron-left': <path d="M15 6l-6 6 6 6" />,
  car: (
    <>
      <path d="M5 17h14M3 17v-4l2-5h14l2 5v4" />
      <circle cx="7.5" cy="17.5" r="1.5" />
      <circle cx="16.5" cy="17.5" r="1.5" />
    </>
  ),
  check: <path d="M5 12l5 5L20 7" />,
  x: <path d="M6 6l12 12M6 18L18 6" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c1-4.5 4.5-7 8-7s7 2.5 8 7" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2 20c1-3.5 3.5-6 7-6s6 2.5 7 6" />
      <circle cx="17" cy="9" r="3" />
      <path d="M22 19c-.5-2.5-2-4-4-4.5" />
    </>
  ),
  doc: (
    <>
      <path d="M6 3h9l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" />
      <path d="M14 3v5h5" />
    </>
  ),
  logout: (
    <>
      <path d="M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4" />
      <path d="M10 8l-4 4 4 4" />
      <path d="M6 12h13" />
    </>
  ),
  alert: (
    <>
      <path d="M12 3l10 18H2z" />
      <path d="M12 10v4M12 17v.5" />
    </>
  ),
  shield: <path d="M12 3l8 3v6c0 5-3 8-8 10-5-2-8-5-8-10V6z" />,
  flag: (
    <>
      <path d="M4 3v18" />
      <path d="M4 4h14l-3 4 3 4H4" />
    </>
  ),
  refresh: (
    <>
      <path d="M4 12a8 8 0 0 1 14-5.3L21 4v6h-6" />
      <path d="M20 12a8 8 0 0 1-14 5.3L3 20v-6h6" />
    </>
  ),
  cog: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" />
    </>
  ),
  'check-square': (
    <>
      <rect x="3" y="3" width="18" height="18" rx="3" />
      <path d="M8 12l3 3 5-6" />
    </>
  ),
  thermometer: <path d="M14 4a2 2 0 1 0-4 0v10a4 4 0 1 0 4 0z" />,
  tool: <path d="M14 6a4 4 0 1 1-5 5L4 16v4h4l5-5a4 4 0 0 1 5-5l3-3-3-3z" />,
  camera: (
    <>
      <rect x="3" y="7" width="18" height="13" rx="2" />
      <circle cx="12" cy="13" r="4" />
      <path d="M8 7l2-3h4l2 3" />
    </>
  ),
  eye: (
    <>
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  edit: (
    <>
      <path d="M4 20h4l11-11-4-4L4 16z" />
      <path d="M14 5l5 5" />
    </>
  ),
  trash: (
    <>
      <path d="M4 7h16" />
      <path d="M10 4h4v3h-4z" />
      <path d="M6 7l1 13h10l1-13" />
    </>
  ),
  print: (
    <>
      <path d="M6 9V3h12v6" />
      <rect x="3" y="9" width="18" height="9" rx="2" />
      <path d="M6 14h12v7H6z" />
    </>
  ),
  qr: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <path d="M14 14h3v3M20 14v3M14 20h3M20 20v.5" />
    </>
  ),
  cash: (
    <>
      <rect x="3" y="6" width="18" height="12" rx="2" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  chart: (
    <>
      <path d="M3 20h18" />
      <path d="M6 20V10M12 20V4M18 20v-8" />
    </>
  ),
  package: (
    <>
      <path d="M4 8l8-4 8 4v9l-8 4-8-4z" />
      <path d="M4 8l8 4 8-4M12 12v9" />
    </>
  ),
  map: (
    <>
      <path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12z" />
      <circle cx="12" cy="9" r="2.5" />
    </>
  ),
  upload: (
    <>
      <path d="M12 3v13" />
      <path d="M7 8l5-5 5 5" />
      <path d="M4 20h16" />
    </>
  ),
  more: (
    <>
      <circle cx="5" cy="12" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
      <circle cx="19" cy="12" r="1.4" fill="currentColor" stroke="none" />
    </>
  ),
}

export type IconName = keyof typeof PATHS

export function Icon({
  name, size = 16, className = '',
}: { name: string; size?: number; className?: string }) {
  const paths = PATHS[name]
  if (!paths) return null
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth={1.9}
      strokeLinecap="round" strokeLinejoin="round"
      className={`shrink-0 ${className}`}
    >
      {paths}
    </svg>
  )
}
