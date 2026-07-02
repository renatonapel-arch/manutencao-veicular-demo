import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { AuthProvider } from './auth/AuthContext'
import { bootstrapSSO } from './auth/ssoBootstrap'
import { FilialProvider } from './context/FilialContext'
import './index.css'

// SSO com Clavis: captura JWT do hash e escuta postMessage. Precisa rodar
// ANTES do AuthProvider pra o carregamento do usuário ver o token novo.
bootstrapSSO()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      // Listas/dashboards refazem ao montar (entrar na rota) pra evitar stale.
      // Cache de 30s evita doublefetch dentro da mesma tela.
      refetchOnMount: 'always',
      staleTime: 30_000,
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <FilialProvider>
            <App />
          </FilialProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
