// Eilės įvertinimas 1–5 (tik kartą, pakeisti negalima). Atsakingas: B.
// Pradines reikšmes (rating_avg, rating_count, my_score) paduoda QueuePanel iš queues.get().
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { queues } from '../../api/index.js'
import { useAuth } from '../../auth/AuthContext.jsx'

const SCORES = [1, 2, 3, 4, 5]

// 1 įvertinimas, 2–9 įvertinimai, 10–20 įvertinimų, 21 įvertinimas, ...
function pluralLt(n) {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'įvertinimas'
  if (mod10 >= 2 && (mod100 < 10 || mod100 >= 20)) return 'įvertinimai'
  return 'įvertinimų'
}

function Stars({ value, size = 'md' }) {
  return (
    <span className={`stars stars-${size}`} aria-hidden="true">
      {SCORES.map((s) => (
        <span key={s} className={s <= Math.round(value) ? 'star on' : 'star'}>★</span>
      ))}
    </span>
  )
}

export default function Rating({ queueId, ratingAvg = null, ratingCount = 0, myScore = null, onRated }) {
  const { user } = useAuth()
  const canRate = user?.role === 'user'
  const [summary, setSummary] = useState({ avg: ratingAvg, count: ratingCount })
  const [mine, setMine] = useState(myScore)
  const [selected, setSelected] = useState(0)
  const [hover, setHover] = useState(0)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(null)

  // Atnaujinam, kai pasikeičia eilė arba atkeliauja duomenys iš serverio
  useEffect(() => {
    setSummary({ avg: ratingAvg, count: ratingCount })
    setMine(myScore)
    setSelected(0)
    setError(null)
  }, [queueId, ratingAvg, ratingCount, myScore])

  const submit = async () => {
    if (!selected) return
    setSending(true)
    setError(null)
    try {
      const res = await queues.review(queueId, selected)
      setSummary({ avg: res.rating_avg, count: res.rating_count })
      setMine(res.score)
      onRated?.(res)
    } catch (err) {
      if (err.status === 409) setMine((m) => m ?? -1) // jau vertinta, bet balas nežinomas
      else if (err.status === 401) setError('Prisijunkite iš naujo')
      else setError(typeof err.detail === 'string' ? err.detail : 'Nepavyko įvertinti')
    } finally {
      setSending(false)
    }
  }

  const shown = hover || selected

  return (
    <section className="rating">
      <div className="rating-summary">
        {summary.count > 0 ? (
          <>
            <Stars value={summary.avg} />
            <strong>{summary.avg.toFixed(1)}</strong>
            <span className="muted">({summary.count} {pluralLt(summary.count)})</span>
          </>
        ) : (
          <span className="muted">Dar neįvertinta</span>
        )}
      </div>

      {mine != null ? (
        <p className="muted rating-mine">
          {mine > 0 ? (
            <>Jūsų įvertinimas: <Stars value={mine} size="sm" /></>
          ) : (
            'Šią eilę jau įvertinote'
          )}
        </p>
      ) : canRate ? (
        <div className="rating-form">
          <div
            className="stars stars-lg"
            role="radiogroup"
            aria-label="Jūsų įvertinimas"
            onMouseLeave={() => setHover(0)}
          >
            {SCORES.map((s) => (
              <button
                key={s}
                type="button"
                role="radio"
                aria-checked={selected === s}
                aria-label={`${s} iš 5`}
                className={s <= shown ? 'star on' : 'star'}
                onMouseEnter={() => setHover(s)}
                onClick={() => setSelected(s)}
                disabled={sending}
              >
                ★
              </button>
            ))}
          </div>
          <button type="button" onClick={submit} disabled={!selected || sending}>
            {sending ? 'Siunčiama…' : 'Įvertinti'}
          </button>
          {selected > 0 && <span className="muted">Įvertinimo pakeisti nebus galima</span>}
        </div>
      ) : !user ? (
        <p className="muted">
          <Link to="/login">Prisijunkite</Link>, kad galėtumėte įvertinti
        </p>
      ) : null}

      {error && <p className="form-error" role="alert">{error}</p>}
    </section>
  )
}
