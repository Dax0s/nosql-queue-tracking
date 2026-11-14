import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { auth } from '../api/index.js'
import { useAuth } from '../auth/AuthContext.jsx'

const CURRENT_YEAR = new Date().getFullYear()

const errorText = (err) => {
  if (err.status === 409) return 'El. paštas jau užregistruotas'
  if (err.status === 422) return 'Patikrinkite įvestus duomenis'
  return 'Įvyko klaida. Bandykite dar kartą'
}

export default function RegisterPage() {
  const { user, loading, signIn } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    birth_year: '',
    email: '',
    password: '',
  })
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
      signIn(await auth.register({ ...form, birth_year: Number(form.birth_year) }))
      navigate('/', { replace: true })
    } catch (err) {
      setError(errorText(err))
      setSubmitting(false)
    }
  }

  return (
    <div className="page auth-page">
      <h1>Registracija</h1>
      <form className="auth-form" onSubmit={onSubmit}>
        <label>
          Vardas
          <input
            name="first_name"
            value={form.first_name}
            onChange={onChange}
            autoComplete="given-name"
            maxLength={50}
            required
            autoFocus
          />
        </label>
        <label>
          Pavardė
          <input
            name="last_name"
            value={form.last_name}
            onChange={onChange}
            autoComplete="family-name"
            maxLength={50}
            required
          />
        </label>
        <label>
          Gimimo metai
          <input
            type="number"
            name="birth_year"
            value={form.birth_year}
            onChange={onChange}
            min={1900}
            max={CURRENT_YEAR}
            required
          />
        </label>
        <label>
          El. paštas
          <input
            type="email"
            name="email"
            value={form.email}
            onChange={onChange}
            autoComplete="email"
            required
          />
        </label>
        <label>
          Slaptažodis
          <input
            type="password"
            name="password"
            value={form.password}
            onChange={onChange}
            autoComplete="new-password"
            minLength={6}
            maxLength={72}
            required
          />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Registruojama…' : 'Registruotis'}
        </button>
      </form>
      <p>
        Jau turite paskyrą? <Link to="/login">Prisijungti</Link>
      </p>
    </div>
  )
}
