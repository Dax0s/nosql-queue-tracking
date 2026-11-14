import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext.jsx'
import LoginPage from './pages/LoginPage.jsx'
import MapPage from './pages/MapPage.jsx'
import MyQueuesPage from './pages/MyQueuesPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import ReportsPage from './pages/ReportsPage.jsx'

function RequireRole({ role, children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/login" replace />
  if (role && user.role !== role) return <Navigate to="/" replace />
  return children
}

export default function App() {
  const { user, signOut } = useAuth()

  return (
    <div className="layout">
      <nav className="navbar">
        <Link to="/" className="brand">Low IQueue</Link>
        {user?.role === 'user' && <Link to="/my-queues">Mano eilės</Link>}
        {user?.role === 'admin' && <Link to="/reports">Ataskaitos</Link>}
        {user ? (
          <>
            <span>{user.first_name}</span>
            <button onClick={signOut}>Atsijungti</button>
          </>
        ) : (
          <>
            <Link to="/login">Prisijungti</Link>
            <Link to="/register">Registruotis</Link>
          </>
        )}
      </nav>
      <main className="content">
        <Routes>
          <Route path="/" element={<MapPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/my-queues" element={<RequireRole role="user"><MyQueuesPage /></RequireRole>} />
          <Route path="/reports" element={<RequireRole role="admin"><ReportsPage /></RequireRole>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
