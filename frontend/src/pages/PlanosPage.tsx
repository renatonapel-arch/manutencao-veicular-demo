import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export default function PlanosPage() {
  const { data: planos } = useQuery({
    queryKey: ['planos'],
    queryFn: () => api.get('/planos').then(r => r.data),
  })

  return (
    <section>
      <div className="flex justify-between items-start mb-3">
        <div>
          <div className="text-lg font-semibold text-naval">Planos preventivos</div>
          <div className="text-xs text-ink-500">{planos?.length || 0} planos ativos</div>
        </div>
        <button className="bg-naval text-white px-3 py-1.5 rounded text-sm font-medium hover:bg-noite">+ Novo plano</button>
      </div>

      <div className="bg-white border border-border rounded overflow-hidden">
        <table className="w-full text-[12px] dense">
          <thead className="bg-ink-50 text-ink-500 border-b border-border">
            <tr>
              <th className="text-left">Modelo</th>
              <th className="text-left">Item</th>
              <th className="text-right">Intervalo km</th>
              <th className="text-right">Intervalo dias</th>
              <th className="text-right">Antecedência</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {(planos || []).map((p: any) => (
              <tr key={p.id} className="border-t border-border hover:bg-ink-50">
                <td>{p.modelo_veiculo}</td>
                <td>{p.item}</td>
                <td className="text-right font-mono">{p.km_intervalo?.toLocaleString('pt-BR') || '—'}</td>
                <td className="text-right font-mono">{p.dias_intervalo || '—'}</td>
                <td className="text-right font-mono">{p.antecedencia_dias}d</td>
                <td><span className={`badge ${p.ativo ? 'bg-success-bg text-success-fg' : 'bg-ink-200 text-ink-500'}`}>{p.ativo ? 'Ativo' : 'Inativo'}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="text-[11px] text-ink-500 mt-2">💡 Planos rodam diariamente às 08:00 UTC via APScheduler. Quando km do veículo entra na janela, cria OS preventiva em status <b>aberta</b> e dispara alerta WhatsApp.</div>
    </section>
  )
}
