/**
 * SSO bootstrap — captura JWT do Clavis quando o módulo é embarcado como iframe.
 *
 * Fluxos suportados:
 * 1. Primeira carga: Clavis navega pra `.../dashboard#access_token=<jwt>`.
 *    Lemos o hash, gravamos em localStorage, limpamos a URL.
 * 2. Renovação: Clavis renova o token a cada ~15min e envia via postMessage.
 *    Escutamos e atualizamos o token em memória — a próxima chamada `api.*`
 *    já usa o novo.
 *
 * O backend do módulo tem `CLAVIS_JWT_SECRET` — valida esse token e
 * auto-provisiona o user local. Zero fricção pro usuário.
 */
import { tokenStore } from '../api/client'

const CLAVIS_ORIGIN_ALLOWLIST = [
  'https://clavis.napel.com.br',
  'https://staging.clavis.napel.com.br',
  'http://localhost:5173',       // Clavis dev
  'http://localhost:5174',       // fallback pra convivência
]

function isTrustedOrigin(origin: string): boolean {
  return CLAVIS_ORIGIN_ALLOWLIST.includes(origin)
}

export function bootstrapSSO(): void {
  // 1) Hash na URL de entrada
  const hash = window.location.hash || ''
  if (hash.includes('access_token=')) {
    const params = new URLSearchParams(hash.replace(/^#/, ''))
    const tok = params.get('access_token')
    if (tok) {
      tokenStore.set(tok)
      // Limpa URL preservando o path (não deixa token no history/back button)
      history.replaceState(null, '', window.location.pathname + window.location.search)
    }
  }

  // 2) Renovação via postMessage
  window.addEventListener('message', (ev) => {
    if (!isTrustedOrigin(ev.origin)) return
    const data = ev.data
    if (data && data.type === 'clavis-token' && typeof data.token === 'string') {
      tokenStore.set(data.token)
    }
  })
}
