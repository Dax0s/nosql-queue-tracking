import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { auth } from '../api/index.js'
import { useAuth } from '../auth/AuthContext.jsx'

const errorText = (err) => {
  if (err.status === 401) return 'Neteisingas el. paštas arba slaptažodis'
  if (err.status === 422) return 'Patikrinkite įvestus duomenis'
  return 'Įvyko klaida. Bandykite dar kartą'
}

export default function LoginPage() {
  const { user, loading, signIn } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  if (loading) return null
  if (user) return <Navigate to="/" replace />

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const onSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      signIn(await auth.login(form))
      navigate('/', { replace: true })
    } catch (err) {
      setError(errorText(err))
      setSubmitting(false)
    }
  }

  return (
    <div className="page auth-page">
      <h1>Prisijungimas</h1>
      <form className="auth-form" onSubmit={onSubmit}>
        <label>
          El. paštas
          <input
            type="email"
            name="email"
            value={form.email}
            onChange={onChange}
            autoComplete="email"
            required
            autoFocus
          />
        </label>
        <label>
          Slaptažodis
          <input
            type="password"
            name="password"
            value={form.password}
            onChange={onChange}
            autoComplete="current-password"
            required
          />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Jungiamasi…' : 'Prisijungti'}
        </button>
      </form>
      <p>
        Neturite paskyros? <Link to="/register">Registruotis</Link>
      </p>
    </div>
  )
}
