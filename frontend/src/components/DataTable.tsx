import { useMemo, useRef, useState, type ReactNode } from 'react'
import { Icon } from './Icons'

/**
 * DataTable — tabela reutilizável com ordenação e filtro por coluna.
 *
 * Uso:
 *   <DataTable
 *     data={rows}
 *     columns={[
 *       { key: 'id', label: 'OS', accessor: r => r.id, render: r => `#${r.id}` },
 *       { key: 'placa', label: 'Placa', accessor: r => r.placa, filter: true, render: r => r.placa },
 *     ]}
 *     onRowClick={r => nav(`/os/${r.id}`)}
 *   />
 *
 * Regras:
 * - `accessor` define o valor pro sort. Se ausente → coluna não é ordenável.
 * - `filter: true` habilita o ícone de funil (popover com input). O componente
 *    compara o valor de `accessor` (ou o texto do `render` como string) via
 *    `String.toLowerCase().includes(query)`. Se quiser filtro customizado,
 *    passe `filter: (row, q) => boolean`.
 * - Múltiplos filtros são AND. Filtros atualizam a cada tecla.
 */

export type DataCol<T> = {
  key: string
  label: string
  accessor?: (row: T) => string | number | Date | null | undefined
  filter?: boolean | ((row: T, query: string) => boolean)
  align?: 'left' | 'right' | 'center'
  headClassName?: string
  cellClassName?: string
  render: (row: T) => ReactNode
}

type Props<T> = {
  data: T[]
  columns: DataCol<T>[]
  onRowClick?: (row: T) => void
  rowKey: (row: T) => string | number
  emptyMessage?: string
  loading?: boolean
  defaultSort?: { key: string; dir: 'asc' | 'desc' }
  className?: string
}

function normalize(v: any): string {
  if (v == null) return ''
  if (v instanceof Date) return v.toISOString()
  return String(v).toLowerCase()
}

export function DataTable<T>({
  data, columns, onRowClick, rowKey, emptyMessage = 'Sem resultados.',
  loading = false, defaultSort, className,
}: Props<T>) {
  const [sort, setSort] = useState<{ key: string; dir: 'asc' | 'desc' } | null>(defaultSort ?? null)
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [openFilter, setOpenFilter] = useState<string | null>(null)

  const filtered = useMemo(() => {
    const activeFilters = Object.entries(filters).filter(([, v]) => v.trim() !== '')
    if (!activeFilters.length) return data
    return data.filter(row =>
      activeFilters.every(([k, q]) => {
        const col = columns.find(c => c.key === k)
        if (!col) return true
        const qLower = q.toLowerCase().trim()
        if (typeof col.filter === 'function') return col.filter(row, qLower)
        const val = col.accessor ? col.accessor(row) : ''
        return normalize(val).includes(qLower)
      }),
    )
  }, [data, filters, columns])

  const sorted = useMemo(() => {
    if (!sort) return filtered
    const col = columns.find(c => c.key === sort.key)
    if (!col?.accessor) return filtered
    const factor = sort.dir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      const va = col.accessor!(a); const vb = col.accessor!(b)
      if (va == null && vb == null) return 0
      if (va == null) return 1
      if (vb == null) return -1
      if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * factor
      return normalize(va).localeCompare(normalize(vb)) * factor
    })
  }, [filtered, sort, columns])

  const clickSort = (col: DataCol<T>) => {
    if (!col.accessor) return
    setSort(prev => {
      if (!prev || prev.key !== col.key) return { key: col.key, dir: 'asc' }
      if (prev.dir === 'asc') return { key: col.key, dir: 'desc' }
      return null
    })
  }

  return (
    <div className={`overflow-x-auto ${className || ''}`}>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[11px] uppercase tracking-wider text-ink-500 bg-[#F8FBFD]">
            {columns.map(col => (
              <Th
                key={col.key}
                col={col}
                isSorted={sort?.key === col.key ? sort.dir : null}
                filterValue={filters[col.key] || ''}
                onSort={() => clickSort(col)}
                onToggleFilter={() => setOpenFilter(openFilter === col.key ? null : col.key)}
                isFilterOpen={openFilter === col.key}
                onFilter={(v) => setFilters(p => ({ ...p, [col.key]: v }))}
              />
            ))}
          </tr>
        </thead>
        <tbody>
          {loading && (
            <tr><td colSpan={columns.length} className="empty">Carregando…</td></tr>
          )}
          {!loading && sorted.length === 0 && (
            <tr><td colSpan={columns.length} className="empty py-10">{emptyMessage}</td></tr>
          )}
          {sorted.map(row => (
            <tr
              key={rowKey(row)}
              className={`row border-t border-line ${onRowClick ? 'cursor-pointer' : ''}`}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {columns.map(col => (
                <td
                  key={col.key}
                  className={`py-3.5 ${col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'} ${col.cellClassName || ''}`}
                >
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** <th> com botões de sort e filtro. */
function Th<T>({
  col, isSorted, filterValue, onSort, isFilterOpen, onToggleFilter, onFilter,
}: {
  col: DataCol<T>
  isSorted: 'asc' | 'desc' | null
  filterValue: string
  onSort: () => void
  onToggleFilter: () => void
  isFilterOpen: boolean
  onFilter: (v: string) => void
}) {
  const canSort = !!col.accessor
  const canFilter = !!col.filter
  const wrapRef = useRef<HTMLDivElement | null>(null)

  return (
    <th
      className={`px-5 py-3 font-semibold ${col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'} ${col.headClassName || ''}`}
    >
      <div className={`inline-flex items-center gap-1 relative ${col.align === 'right' ? 'flex-row-reverse' : ''}`}>
        <button
          type="button"
          onClick={onSort}
          disabled={!canSort}
          className={`inline-flex items-center gap-1 ${canSort ? 'hover:text-navy-800 cursor-pointer' : 'cursor-default'}`}
        >
          {col.label}
          {canSort && (
            <span className={`ml-0.5 ${isSorted ? 'text-navy-800' : 'text-ink-300'}`}>
              <Icon name={isSorted === 'desc' ? 'arrow-down' : isSorted === 'asc' ? 'arrow-up' : 'sort'} size={10} />
            </span>
          )}
        </button>
        {canFilter && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onToggleFilter() }}
            className={`p-0.5 rounded hover:bg-sky-bg ${filterValue ? 'text-sky-700' : 'text-ink-300'}`}
            title="Filtrar"
          >
            <Icon name="filter" size={11} />
          </button>
        )}
        {isFilterOpen && (
          <div
            ref={wrapRef}
            className="absolute top-full left-0 mt-1 z-10 bg-white border border-line rounded-lg shadow-lg p-2 w-56 text-normal"
            onClick={(e) => e.stopPropagation()}
          >
            <input
              autoFocus
              value={filterValue}
              onChange={(e) => onFilter(e.target.value)}
              placeholder={`Filtrar ${col.label.toLowerCase()}…`}
              className="input text-xs w-full"
              onKeyDown={(e) => { if (e.key === 'Escape') onToggleFilter() }}
            />
            {filterValue && (
              <button
                type="button"
                onClick={() => { onFilter(''); onToggleFilter() }}
                className="text-xs text-sky-700 mt-1 font-semibold"
              >
                Limpar
              </button>
            )}
          </div>
        )}
      </div>
    </th>
  )
}
