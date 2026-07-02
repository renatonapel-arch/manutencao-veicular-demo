import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import { fmtKm } from '../../components/Badges'
import { Icon } from '../../components/Icons'

/**
 * Checklist mensal do motorista — pipe "Custos - Checklist Veiculos".
 * Cada item PROBLEMA gera 1 OS corretiva_checklist automaticamente.
 */

function uuid4(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

type Status = 'OK' | 'PROBLEMA' | 'NA'

export default function MobileNovoChecklistPage() {
  const nav = useNavigate()
  const [veiculoId, setVeiculoId] = useState<number | ''>('')
  const [km, setKm] = useState<number>(0)
  const [obs, setObs] = useState('')
  const [status, setStatus] = useState<Record<string, Status>>({})

  const { data: veiculos } = useQuery({
    queryKey: ['m-veic-checklist'],
    queryFn: () => api.get('/veiculos').then(r => r.data),
  })
  const { data: itensRef } = useQuery({
    queryKey: ['checklist-itens-ref'],
    queryFn: () => api.get('/checklist/itens-referencia').then(r => r.data),
  })

  const veic = (veiculos || []).find((v: any) => v.id === veiculoId)
  const tipo = (veic?.tipo || '').toLowerCase().startsWith('mot') ? 'moto' : 'carro'
  const itens: string[] = itensRef?.[tipo] || []

  const onSelectVeic = (id: number) => {
    setVeiculoId(id)
    const v = (veiculos || []).find((x: any) => x.id === id)
    if (v) setKm(v.km_atual || 0)
    // Reset status ao trocar veículo
    setStatus({})
  }

  const marcar = (item: string, s: Status) =>
    setStatus(p => ({ ...p, [item]: p[item] === s ? 'NA' : s }))

  const n_ok = itens.filter(i => status[i] === 'OK').length
  const n_prob = itens.filter(i => status[i] === 'PROBLEMA').length
  const n_pendente = itens.length - n_ok - n_prob - itens.filter(i => status[i] === 'NA').length
  const podeEnviar = !!veiculoId && km > 0 && n_pendente === 0

  const submit = useMutation({
    mutationFn: () => api.post('/checklist', {
      request_id: uuid4(),
      veiculo_id: Number(veiculoId),
      km_veiculo: Number(km),
      itens_status: status,
      observacao: obs || null,
    }).then(r => r.data),
    onSuccess: (data) => {
      alert(
        `Checklist enviado! ${data.total_ok} OK · ${data.total_problemas} problemas` +
        (data.os_geradas?.length ? `\n\nOS abertas automaticamente: ${data.os_geradas.map((n: number) => '#' + n).join(', ')}` : ''),
      )
      nav('/os')
    },
    onError: (e: any) => alert(e.response?.data?.detail || 'Erro ao enviar'),
  })

  return (
    <section className="px-3 py-4 space-y-4">
      <div className="card-m">
        <div className="kpi-label mb-2">Veículo</div>
        <select
          value={veiculoId}
          onChange={(e) => onSelectVeic(Number(e.target.value))}
          className="input w-full"
        >
          <option value="">— escolha o veículo —</option>
          {(veiculos || []).map((v: any) => (
            <option key={v.id} value={v.id}>{v.placa} · {v.modelo} ({v.tipo || '—'})</option>
          ))}
        </select>

        {veic && (
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div>
              <div className="kpi-label mb-1">KM atual</div>
              <div className="font-mono num text-sm text-navy-800">{fmtKm(veic.km_atual)}</div>
            </div>
            <div>
              <div className="kpi-label mb-1">KM lido agora *</div>
              <input
                type="number"
                value={km}
                onChange={(e) => setKm(Number(e.target.value))}
                className="input font-mono text-navy-800"
                min={veic.km_atual || 0}
              />
            </div>
          </div>
        )}
      </div>

      {veic && (
        <div className="card-m">
          <div className="flex items-center justify-between mb-3">
            <div className="kpi-label">Checklist {tipo}</div>
            <div className="text-xs">
              <span className="text-ok-fg font-semibold">{n_ok} OK</span>
              <span className="mx-1 text-ink-400">·</span>
              <span className="text-err-fg font-semibold">{n_prob} problema{n_prob !== 1 ? 's' : ''}</span>
              {n_pendente > 0 && (
                <>
                  <span className="mx-1 text-ink-400">·</span>
                  <span className="text-warn-fg font-semibold">{n_pendente} pendente{n_pendente !== 1 ? 's' : ''}</span>
                </>
              )}
            </div>
          </div>

          <div className="space-y-2.5">
            {itens.map(item => {
              const s = status[item]
              return (
                <div key={item} className="border border-line rounded-xl p-3 space-y-2">
                  <div className="text-sm font-medium leading-snug">{item}</div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => marcar(item, 'OK')}
                      className={`flex-1 py-2 rounded-lg text-xs font-bold transition-colors ${
                        s === 'OK' ? 'bg-ok text-white' : 'bg-ok-bg/40 text-ok-fg border border-ok'
                      }`}
                    >
                      OK
                    </button>
                    <button
                      type="button"
                      onClick={() => marcar(item, 'PROBLEMA')}
                      className={`flex-1 py-2 rounded-lg text-xs font-bold transition-colors ${
                        s === 'PROBLEMA' ? 'bg-err text-white' : 'bg-err-bg/40 text-err-fg border border-err'
                      }`}
                    >
                      PROBLEMA
                    </button>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="mt-4">
            <div className="kpi-label mb-1">Observação (opcional)</div>
            <textarea
              value={obs}
              onChange={(e) => setObs(e.target.value)}
              placeholder="Ex: fez revisão no fim de semana"
              className="input h-20 text-sm w-full"
            />
          </div>
        </div>
      )}

      {veic && (
        <>
          {n_prob > 0 && (
            <div className="bg-warn-bg border border-warn rounded-xl p-3 text-xs text-warn-fg flex gap-2">
              <Icon name="alert" size={16} />
              <div>
                <b>{n_prob} OS ser{n_prob === 1 ? 'á aberta' : 'ão abertas'}</b> automaticamente
                para os itens marcados como problema. O responsável da filial será
                notificado por WhatsApp.
              </div>
            </div>
          )}

          <button
            onClick={() => submit.mutate()}
            disabled={!podeEnviar || submit.isPending}
            className="btn btn-primary btn-lg w-full justify-center disabled:opacity-40"
          >
            <Icon name="check" size={16} />
            {submit.isPending ? 'Enviando…' : 'Enviar checklist'}
          </button>

          {!podeEnviar && n_pendente > 0 && (
            <div className="text-xs text-ink-500 text-center">
              Marque todos os itens como OK ou PROBLEMA antes de enviar.
            </div>
          )}
        </>
      )}
    </section>
  )
}
