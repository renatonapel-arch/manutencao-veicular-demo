import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import LoginPage from './auth/LoginPage'
import Layout from './components/Layout'
import DashboardPage from './pages/DashboardPage'
import ListaOSPage from './pages/ListaOSPage'
import NovaOSPage from './pages/NovaOSPage'
import DetalheOSPage from './pages/DetalheOSPage'
import PlanosPage from './pages/PlanosPage'
import OficinasPage from './pages/OficinasPage'
import AlertasPage from './pages/AlertasPage'
import TimelineVeiculoPage from './pages/TimelineVeiculoPage'
import MobilePage from './pages/MobilePage'

function RequireAuth({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-6 text-ink-500">Carregando…</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="os" element={<ListaOSPage />} />
        <Route path="os/nova" element={<NovaOSPage />} />
        <Route path="os/:id" element={<DetalheOSPage />} />
        <Route path="planos" element={<PlanosPage />} />
        <Route path="oficinas" element={<OficinasPage />} />
        <Route path="alertas" element={<AlertasPage />} />
        <Route path="veiculo/:placa" element={<TimelineVeiculoPage />} />
        <Route path="mobile" element={<MobilePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
