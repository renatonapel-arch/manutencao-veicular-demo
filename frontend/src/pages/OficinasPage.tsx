import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { FilialChip } from '../components/Badges'

export default function OficinasPage() {
  const [q, setQ] = useState('')
  const { data: oficinas } = useQuery({
    queryKey: ['oficinas', q],
    queryFn: () => api.get('/oficinas' + (q ? `?q=${encodeURIComponent(q)}` : '')).then(r => r.data),
  })

  return (
    <section>
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="text-lg font-semibold text-naval">Catálogo de oficinas</div>
          <div className="text-xs text-ink-500">{oficinas?.length || 0} oficinas ativas · texto livre <b className="text-danger-fg">bloqueado</b></div>
        </div>
        <button className="bg-naval text-white px-3 py-1.5 rounded text-sm font-medium hover:bg-noite">+ Nova oficina</button>
      </div>

      <div className="bg-white border border-border rounded p-3 mb-3">
        <input
          className="border border-border-strong rounded px-2 py-1 w-64 text-xs"
          placeholder="🔍 Buscar nome / CNPJ / cidade"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

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
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
