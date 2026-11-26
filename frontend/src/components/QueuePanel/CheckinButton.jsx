// Check-in / check-out mygtukas. Atsakingas: A.
// Pradines reikšmes (active_count, is_checked_in, has_waited, avg_wait_sec, wait_samples) paduoda QueuePanel iš queues.get().
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

// 1 matavimas, 2–9 matavimai, 10–20 matavimų, 21 matavimas, ...
function pluralSamples(n) {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'matavimas'
  if (mod10 >= 2 && (mod100 < 10 || mod100 >= 20)) return 'matavimai'
  return 'matavimų'
}

function formatDuration(sec) {
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = Math.round(sec % 60)
  if (h > 0) return `${h} val. ${m} min.`
  if (m > 0) return `${m} min. ${s} s`
  return `${s} s`
}

export default function CheckinButton({
  queueId,
  activeCount = 0,
  isCheckedIn = false,
  hasWaited = false,
  avgWaitSec = null,
  waitSamples = 0,
}) {
  const { user } = useAuth()
  const canCheckin = user?.role === 'user'
  const [count, setCount] = useState(activeCount)
  const [checkedIn, setCheckedIn] = useState(Boolean(isCheckedIn))
  // Vienoje eilėje galima stovėti tik kartą: po check-out mygtukas neberodomas
  const [waited, setWaited] = useState(Boolean(hasWaited))
  const [lastDuration, setLastDuration] = useState(null)
  const [wait, setWait] = useState({ avg: avgWaitSec, samples: waitSamples })
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(null)

  // Atnaujinam, kai pasikeičia eilė arba atkeliauja duomenys iš serverio
  useEffect(() => {
    setCount(activeCount)
    setCheckedIn(Boolean(isCheckedIn))
    setWaited(Boolean(hasWaited))
    setLastDuration(null)
    setError(null)
  }, [queueId, activeCount, isCheckedIn, hasWaited])

  useEffect(() => {
    setWait({ avg: avgWaitSec, samples: waitSamples })
  }, [queueId, avgWaitSec, waitSamples])

  // Po 409 būsena kliente pasenusi (pvz., kitame skirtuke jau pasižymėta), todėl ją perkraunam
  const resync = async () => {
    try {
      const q = await queues.get(queueId)
      setCount(q.active_count)
      setCheckedIn(Boolean(q.is_checked_in))
      setWaited(Boolean(q.has_waited))
      setWait({ avg: q.avg_wait_sec, samples: q.wait_samples })
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
        // Naujas matavimas įskaičiuojamas iškart, nelaukiant serverio cache (30 s)
        setWait(({ avg, samples }) => ({
          avg: ((avg ?? 0) * samples + res.duration_sec) / (samples + 1),
          samples: samples + 1,
        }))
      } else {
        const res = await queues.checkin(queueId)
        setCheckedIn(true)
        setWaited(true)
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
      <p className="checkin-wait">
        Vidutinis laukimas:{' '}
        {wait.samples > 0 && wait.avg != null ? (
          <>
            <strong>{formatDuration(wait.avg)}</strong>{' '}
            <span className="muted">({wait.samples} {pluralSamples(wait.samples)})</span>
          </>
        ) : (
          <span className="muted">dar nėra duomenų</span>
        )}
      </p>

      {canCheckin && waited && !checkedIn ? (
        <p className="muted">Šioje eilėje jau stovėjote</p>
      ) : canCheckin ? (
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
