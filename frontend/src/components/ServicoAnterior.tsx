import { Link } from 'react-router-dom'

/**
 * "Última vez" do mesmo serviço (mesma categoria) neste veículo — #0272.
 * A lista vem pronta do backend (servico_anterior: até 3, sem canceladas nem a própria).
 */
// OS migradas do Pipefy guardam só o dia (meia-noite UTC); no fuso de Brasília isso
// cairia no dia anterior — então meia-noite UTC exata é lida como data pura.
const data = (s: string) => {
  const d = new Date(s)
  const soDia = d.getUTCHours() === 0 && d.getUTCMinutes() === 0 && d.getUTCSeconds() === 0
  return d.toLocaleDateString('pt-BR', soDia ? { timeZone: 'UTC' } : undefined)
}
const km = (n: number) => n.toLocaleString('pt-BR')

function distancia(s: any) {
  const dias = s.dias_antes === 0 ? 'no mesmo dia' : `há ${s.dias_antes} dia${s.dias_antes === 1 ? '' : 's'}`
  return s.km_antes != null ? `${dias} · ${km(s.km_antes)} km` : dias
}

export default function ServicoAnterior({ os, mobile }: { os: any; mobile?: boolean }) {
  const lista: any[] = os.servico_anterior || []
  const [ult, ...outras] = lista
  let corpo
  if (!os.categoria) corpo = <div className="text-nv-soft">OS sem categoria — não dá para comparar.</div>
  else if (os.categoria === 'Outros') corpo = <div className="text-nv-soft">Categoria "Outros" junta serviços diferentes — não dá para comparar.</div>
  else if (!ult) corpo = <div className="text-nv-soft">Sem registro anterior de {os.categoria} neste veículo.</div>
  else corpo = (
    <>
      <div>
        Última vez: <Link to={`/os/${ult.id}`} className="text-nv-primary font-medium hover:underline">OS #{ult.id}</Link>
        {' '}em {data(ult.data)}, KM <span className="font-mono">{km(ult.km_veiculo)}</span>
        <span className="text-nv-soft"> ({distancia(ult)} antes desta)</span>
      </div>
      {ult.descricao && <div className="text-[12px] text-nv-soft mt-0.5 line-clamp-2">{ult.descricao}</div>}
      {outras.length > 0 && (
        <div className="mt-2 pt-2 border-t border-nv-border space-y-1 text-[12px]">
          {outras.map(s => (
            <div key={s.id}>
              <Link to={`/os/${s.id}`} className="text-nv-primary hover:underline">OS #{s.id}</Link>
              {' '}· {data(s.data)} · KM <span className="font-mono">{km(s.km_veiculo)}</span>
              <span className="text-nv-soft"> · {distancia(s)} antes</span>
            </div>
          ))}
        </div>
      )}
    </>
  )

  return (
    <div className={mobile ? 'bg-nv-surface border border-nv-border rounded-lg p-3' : 'card p-5'}>
      <div className={mobile ? 'text-[10px] uppercase tracking-wider text-nv-soft mb-1' : 'kpi-label mb-3'}>
        Última vez deste serviço{os.categoria ? <> · <span className="pill pill-sky normal-case">{os.categoria}</span></> : null}
      </div>
      <div className="text-[13px]">{corpo}</div>
    </div>
  )
}
