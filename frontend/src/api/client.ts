import axios from 'axios'

const TOKEN_KEY = 'clavis_manut_token'

export const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function isEmbedded(): boolean {
  try { return window.self !== window.top } catch { return true }
}

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && window.location.pathname !== '/login') {
      localStorage.removeItem(TOKEN_KEY)
      // Dentro do Clavis não existe tela de login: recarrega e cai no card
      // "Sessão expirada". Fora dele, vai para /login.
      if (isEmbedded()) window.location.reload()
      else window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}
