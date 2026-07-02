import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import { useIsMobile } from './hooks/useIsMobile'

import LoginPage from './auth/LoginPage'

import Layout from './components/Layout'
import MobileLayout from './components/MobileLayout'

// Desktop
import DashboardPage from './pages/DashboardPage'
import ListaOSPage from './pages/ListaOSPage'
import NovaOSPage from './pages/NovaOSPage'
import DetalheOSPage from './pages/DetalheOSPage'
import PlanosPage from './pages/PlanosPage'
import OficinasPage from './pages/OficinasPage'
import AlertasPage from './pages/AlertasPage'
import TimelineVeiculoPage from './pages/TimelineVeiculoPage'
import MobilePage from './pages/MobilePage'
import AprovacoesPage from './pages/AprovacoesPage'
import FrotaPage from './pages/FrotaPage'
import ChecklistsPage from './pages/ChecklistsPage'

// Mobile dedicado
import MobileHomePage from './pages/mobile/MobileHomePage'
import MobileListaOSPage from './pages/mobile/MobileListaOSPage'
import MobileDetalheOSPage from './pages/mobile/MobileDetalheOSPage'
import MobileNovaOSPage from './pages/mobile/MobileNovaOSPage'
import MobilePerfilPage from './pages/mobile/MobilePerfilPage'
import MobileNovoChecklistPage from './pages/mobile/MobileNovoChecklistPage'

function RequireAuth({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-6 text-ink-500">Carregando…</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const isMobile = useIsMobile()

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            {isMobile ? <MobileLayout /> : <Layout />}
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />

        <Route path="dashboard"      element={isMobile ? <MobileHomePage />     : <DashboardPage />} />
        <Route path="os"             element={isMobile ? <MobileListaOSPage /> : <ListaOSPage />} />
        <Route path="os/nova"        element={isMobile ? <MobileNovaOSPage />  : <NovaOSPage />} />
        <Route path="os/:id"         element={isMobile ? <MobileDetalheOSPage /> : <DetalheOSPage />} />

        {/* Telas secundárias compartilhadas (desktop reaproveitado, scroll horizontal no mobile) */}
        <Route path="planos"           element={<PlanosPage />} />
        <Route path="aprovacoes"       element={<AprovacoesPage />} />
        <Route path="frota"            element={<FrotaPage />} />
        <Route path="oficinas"         element={<OficinasPage />} />
        <Route path="alertas"          element={<AlertasPage />} />
        <Route path="checklists"       element={<ChecklistsPage />} />
        <Route path="checklist/novo"   element={<MobileNovoChecklistPage />} />
        <Route path="veiculo/:placa"   element={<TimelineVeiculoPage />} />
        <Route path="mobile"           element={<MobilePage />} />

        {/* Só mobile */}
        <Route path="perfil"           element={isMobile ? <MobilePerfilPage /> : <Navigate to="/dashboard" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
