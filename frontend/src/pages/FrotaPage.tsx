import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { fmtKm, FilialChip } from '../components/Badges'
import { Icon } from '../components/Icons'
import { useFilial } from '../context/FilialContext'

/** Frota — somente leitura, fonte: Cadastro Veicular (frota-demo). */
export default function FrotaPage() {
  const { filialId } = useFilial()
  const [q, setQ] = useState('')

  const { data: veiculos, isLoading } = useQuery({
    queryKey: ['frota', filialId, q],
    queryFn: () => {
      const p = new URLSearchParams()
      if (filialId) p.set('filial_id', String(filialId))
      if (q) p.set('q', q)
      return api.get('/veiculos?' + p).then(r => r.data)
    },
  })

  return (
    <section>
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <span className="pill pill-sky">
          <Icon name="refresh" size={11} /> Fonte: Cadastro Veicular
        </span>
        <span className="text-xs text-ink-500">
          Somente leitura · {veiculos?.length ?? 0} veículos ativos · manutenção não altera a frota
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-5">
        <div className="relative flex-1 max-w-md">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-400">
            <Icon name="search" size={16} />
          </span>
          <input
            className="input pl-10"
            placeholder="Buscar por placa ou modelo…"
            value={q}
            onChange={e => setQ(e.target.value)}
          />
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[680px]">
            <thead>
              <tr className="text-[11px] uppercase tracking-wider text-ink-500 bg-[#F8FBFD]">
                <th className="text-left px-5 py-3 font-semibold">Placa</th>
                <th className="text-left py-3 font-semibold">Modelo</th>
                <th className="text-left py-3 font-semibold">Tipo</th>
                <th className="text-left py-3 font-semibold">Filial</th>
                <th className="text-right py-3 font-semibold">Km atual</th>
                <th className="text-left px-5 py-3 font-semibold">CRLV vence</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={6} className="empty">Carregando…</td></tr>
              )}
              {!isLoading && !(veiculos || []).length && (
                <tr>
                  <td colSpan={6} className="empty py-14">
                    <Icon name="car" size={44} />
                    <div className="text-sm">Frota vazia. Rode o sync no Admin.</div>
                  </td>
                </tr>
              )}
              {(veiculos || []).map((v: any) => (
                <tr key={v.id} className="row border-t border-line cursor-pointer"
                    onClick={() => location.assign(`/veiculo/${v.placa}`)}>
                  <td className="px-5 py-3 font-mono font-semibold text-navy-800">{v.placa}</td>
                  <td className="py-3">
                    <div className="font-semibold">{v.modelo}</div>
                    {v.marca && <div className="text-xs text-ink-500">{v.marca}</div>}
                  </td>
                  <td className="py-3"><span className="pill pill-gray">{v.tipo || '—'}</span></td>
                  <td className="py-3"><FilialChip filialId={v.filial_id} /></td>
                  <td className="py-3 text-right font-mono num">{fmtKm(v.km_atual)}</td>
                  <td className="px-5 py-3 font-mono text-xs text-ink-500">{v.vencimento_crlv || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
