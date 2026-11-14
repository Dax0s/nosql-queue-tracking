import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { queues } from '../../api/index.js'
import { useAuth } from '../../auth/AuthContext.jsx'

const CLOSE_DELAY_MS = 1500

const errorText = (err) => {
  if (err.status === 401) return 'Prisijunkite, kad sukurtumėte eilę'
  if (err.status === 403) return 'Neturite teisės kurti eilių'
  if (err.status === 422) return 'Patikrinkite įvestus duomenis'
  return 'Įvyko klaida. Bandykite dar kartą'
}

export default function CreateQueuePopup({ position, onClose, onCreated }) {
  const { user } = useAuth()
  const [title, setTitle] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [created, setCreated] = useState(false)

  useEffect(() => {
    if (!created) return
    const timer = setTimeout(onClose, CLOSE_DELAY_MS)
    return () => clearTimeout(timer)
  }, [created, onClose])

  if (!user) {
    return (
      <div className="queue-form">
        <p>
          <Link to="/login">Prisijunkite</Link>, kad sukurtumėte eilę
        </p>
      </div>
    )
  }

  if (created) {
    return (
      <div className="queue-form">
        <p>Eilė sukurta</p>
      </div>
    )
  }

  const onSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const queue = await queues.create({
        title: title.trim(),
        lat: position.lat,
        lng: position.lng,
      })
      setCreated(true)
      onCreated?.(queue)
    } catch (err) {
      setError(errorText(err))
      setSubmitting(false)
    }
  }

  const onCancel = (e) => {
    e.stopPropagation()
    onClose()
  }

  return (
    <form className="queue-form" onSubmit={onSubmit}>
      <h3>Nauja eilė</h3>
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Pavadinimas"
        aria-label="Pavadinimas"
        maxLength={100}
        required
        autoFocus
      />
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="queue-form-actions">
        <button type="submit" disabled={submitting || !title.trim()}>
          {submitting ? 'Kuriama…' : 'Sukurti'}
        </button>
        <button type="button" onClick={onCancel} disabled={submitting}>
          Atšaukti
        </button>
      </div>
    </form>
  )
}
