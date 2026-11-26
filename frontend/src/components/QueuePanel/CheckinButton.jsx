// Check-in / check-out mygtukas. Atsakingas: A.
// Pradines reikšmes (active_count, is_checked_in) paduoda QueuePanel iš queues.get().
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { queues } from '../../api/index.js'
import { useAuth } from '../../auth/AuthContext.jsx'

// 1 žmogus, 2–9 žmonės, 10–20 žmonių, 21 žmogus, ...
function pluralPeople(n) {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'žmogus'
  if (mod10 >= 2 && (mod100 < 10 || mod100 >= 20)) return 'žmonės'
  return 'žmonių'
}

function formatDuration(sec) {
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  if (h > 0) return `${h} val. ${m} min.`
  if (m > 0) return `${m} min. ${s} s`
  return `${s} s`
}

export default function CheckinButton({ queueId, activeCount = 0, isCheckedIn = false }) {
  const { user } = useAuth()
  const canCheckin = user?.role === 'user'
  const [count, setCount] = useState(activeCount)
  const [checkedIn, setCheckedIn] = useState(Boolean(isCheckedIn))
  const [lastDuration, setLastDuration] = useState(null)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(null)

  // Atnaujinam, kai pasikeičia eilė arba atkeliauja duomenys iš serverio
  useEffect(() => {
    setCount(activeCount)
    setCheckedIn(Boolean(isCheckedIn))
    setLastDuration(null)
    setError(null)
  }, [queueId, activeCount, isCheckedIn])

  // Po 409 būsena kliente pasenusi (pvz., kitame skirtuke jau pasižymėta), todėl ją perkraunam
  const resync = async () => {
    try {
      const q = await queues.get(queueId)
      setCount(q.active_count)
      setCheckedIn(Boolean(q.is_checked_in))
    } catch {
      // paliekam, kaip yra – klaida jau parodyta
    }
  }

  const toggle = async () => {
    setSending(true)
    setError(null)
    try {
      if (checkedIn) {
        const res = await queues.checkout(queueId)
        setCheckedIn(false)
        setCount(res.active_count)
        setLastDuration(res.duration_sec)
      } else {
        const res = await queues.checkin(queueId)
        setCheckedIn(true)
        setCount(res.active_count)
        setLastDuration(null)
      }
    } catch (err) {
      if (err.status === 401) setError('Prisijunkite iš naujo')
      else setError(typeof err.detail === 'string' ? err.detail : 'Nepavyko')
      if (err.status === 409) await resync()
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="checkin">
      <p className="checkin-count">
        Eilėje dabar: <strong>{count}</strong> {pluralPeople(count)}
      </p>

      {canCheckin ? (
        <div className="checkin-form">
          <button
            type="button"
            className={checkedIn ? 'checkin-btn out' : 'checkin-btn'}
            onClick={toggle}
            disabled={sending}
          >
            {sending ? 'Siunčiama…' : checkedIn ? 'Išeinu iš eilės' : 'Stoviu eilėje'}
          </button>
          {checkedIn && <span className="muted">Pasižymėjote šioje eilėje</span>}
        </div>
      ) : !user ? (
        <p className="muted">
          <Link to="/login">Prisijunkite</Link>, kad galėtumėte pasižymėti eilėje
        </p>
      ) : null}

      {lastDuration != null && (
        <p className="muted">Eilėje stovėjote {formatDuration(lastDuration)}</p>
      )}
      {error && <p className="form-error" role="alert">{error}</p>}
    </section>
  )
}
