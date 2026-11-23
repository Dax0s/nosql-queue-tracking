// Eilės langas. Karkasas – A; <Rating /> ir <Comments /> įstato B.
// TODO(A): check-in / check-out mygtukas
import { useEffect, useState } from 'react'
import { queues } from '../../api/index.js'
import { useAuth } from '../../auth/AuthContext.jsx'
import Comments from './Comments.jsx'
import Rating from './Rating.jsx'

export default function QueuePanel({ queueId, onClose }) {
  const { user } = useAuth()
  const [queue, setQueue] = useState(null)
  const [error, setError] = useState(null)

  // Vartotojo būsena (my_score, is_checked_in) priklauso nuo prisijungimo, todėl krauname iš naujo
  useEffect(() => {
    let cancelled = false
    setQueue(null)
    setError(null)
    queues
      .get(queueId)
      .then((q) => !cancelled && setQueue(q))
      .catch((err) => {
        if (cancelled) return
        setError(err.status === 404 ? 'Eilė nerasta' : 'Nepavyko įkelti eilės')
      })
    return () => {
      cancelled = true
    }
  }, [queueId, user?.id])

  return (
    <aside className="queue-panel">
      <button onClick={onClose}>Uždaryti</button>
      <h2>{queue?.title ?? 'Eilė'}</h2>
      {error && <p className="form-error" role="alert">{error}</p>}
      {queue && (
        <Rating
          queueId={queueId}
          ratingAvg={queue.rating_avg}
          ratingCount={queue.rating_count}
          myScore={queue.my_score}
        />
      )}
      <Comments queueId={queueId} />
    </aside>
  )
}
