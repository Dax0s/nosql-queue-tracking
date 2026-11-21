// Eilės komentarai: sąrašas su ženkleliais, rašymas, trynimas, likai. Atsakingas: B.
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { comments as api } from '../../api/index.js'
import { useAuth } from '../../auth/AuthContext.jsx'

const MAX_LEN = 1000
const rtf = new Intl.RelativeTimeFormat('lt', { numeric: 'auto' })

function timeAgo(iso) {
  const sec = Math.round((new Date(iso) - Date.now()) / 1000)
  const steps = [[60, 'second'], [60, 'minute'], [24, 'hour'], [30, 'day'], [12, 'month']]
  let value = sec
  for (const [size, unit] of steps) {
    if (Math.abs(value) < size) return rtf.format(value, unit)
    value = Math.round(value / size)
  }
  return rtf.format(value, 'year')
}

const errorText = (err, fallback) => {
  if (err.status === 401) return 'Prisijunkite iš naujo'
  if (err.status === 429) return 'Per daug komentarų, palaukite minutę'
  if (typeof err.detail === 'string') return err.detail
  return fallback
}

function Badge({ badge }) {
  if (!badge) return null
  return (
    <span className={`badge badge-${badge.icon}`} title={`${badge.min_likes}+ likų`}>
      {badge.name}
    </span>
  )
}

function CommentItem({ comment, canAct, isMine, onLike, onDelete }) {
  const [busy, setBusy] = useState(false)
  const run = async (fn) => {
    setBusy(true)
    try {
      await fn()
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="comment">
      <div className="comment-head">
        <strong>{comment.author_name}</strong>
        <Badge badge={comment.badge} />
        <time dateTime={comment.created_at} title={new Date(comment.created_at).toLocaleString('lt')}>
          {timeAgo(comment.created_at)}
        </time>
      </div>
      <p className="comment-text">{comment.text}</p>
      <div className="comment-actions">
        <button
          type="button"
          className={`like-btn${comment.liked_by_me ? ' liked' : ''}`}
          onClick={() => run(() => onLike(comment))}
          disabled={!canAct || isMine || busy}
          title={isMine ? 'Savo komentaro likinti negalima' : undefined}
          aria-pressed={Boolean(comment.liked_by_me)}
        >
          ♥ {comment.likes_count}
        </button>
        {isMine && (
          <button
            type="button"
            className="link-btn"
            onClick={() => window.confirm('Ištrinti komentarą?') && run(() => onDelete(comment))}
            disabled={busy}
          >
            Ištrinti
          </button>
        )}
      </div>
    </li>
  )
}

function CommentForm({ onSubmit }) {
  const [text, setText] = useState('')
  const [error, setError] = useState(null)
  const [sending, setSending] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    const value = text.trim()
    if (!value) return
    setError(null)
    setSending(true)
    try {
      await onSubmit(value)
      setText('')
    } catch (err) {
      setError(errorText(err, 'Nepavyko išsiųsti komentaro'))
    } finally {
      setSending(false)
    }
  }

  return (
    <form className="comment-form" onSubmit={submit}>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Parašykite komentarą…"
        aria-label="Komentaras"
        maxLength={MAX_LEN}
        rows={3}
      />
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="comment-form-footer">
        <span className="muted">{text.length}/{MAX_LEN}</span>
        <button type="submit" disabled={sending || !text.trim()}>
          {sending ? 'Siunčiama…' : 'Komentuoti'}
        </button>
      </div>
    </form>
  )
}

export default function Comments({ queueId }) {
  const { user } = useAuth()
  const canAct = user?.role === 'user'
  const [items, setItems] = useState([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(
    async (p, signal) => {
      setLoading(true)
      setError(null)
      try {
        const data = await api.list(queueId, p)
        if (signal?.cancelled) return
        // Tarp puslapių galėjo atsirasti naujų komentarų: dubliai išmetami pagal id
        setItems((prev) => {
          if (p === 1) return data.items
          const seen = new Set(prev.map((c) => c.id))
          return [...prev, ...data.items.filter((c) => !seen.has(c.id))]
        })
        setPage(data.page)
        setHasMore(data.has_more)
      } catch (err) {
        if (!signal?.cancelled) setError(errorText(err, 'Nepavyko įkelti komentarų'))
      } finally {
        if (!signal?.cancelled) setLoading(false)
      }
    },
    [queueId],
  )

  // Iš naujo kraunama pasikeitus eilei arba prisijungus (liked_by_me priklauso nuo vartotojo)
  useEffect(() => {
    const signal = { cancelled: false }
    setItems([])
    load(1, signal)
    return () => {
      signal.cancelled = true
    }
  }, [load, user?.id])

  const patch = (id, changes) =>
    setItems((prev) => prev.map((c) => (c.id === id ? { ...c, ...changes } : c)))

  const create = async (text) => {
    const comment = await api.create(queueId, text)
    setItems((prev) => [{ ...comment, liked_by_me: false }, ...prev])
  }

  const remove = async (comment) => {
    try {
      await api.remove(comment.id)
      setItems((prev) => prev.filter((c) => c.id !== comment.id))
    } catch (err) {
      if (err.status === 404) setItems((prev) => prev.filter((c) => c.id !== comment.id))
      else setError(errorText(err, 'Nepavyko ištrinti komentaro'))
    }
  }

  const toggleLike = async (comment) => {
    setError(null)
    try {
      if (comment.liked_by_me) {
        await api.unlike(comment.id)
        patch(comment.id, { liked_by_me: false, likes_count: Math.max(0, comment.likes_count - 1) })
      } else {
        const { likes_count } = await api.like(comment.id)
        patch(comment.id, { liked_by_me: true, likes_count })
      }
    } catch (err) {
      // Būsena serveryje jau kita (409 jau palikinta, 404 liko nėra): sinchronizuojam
      if (err.status === 409) patch(comment.id, { liked_by_me: true })
      else if (err.status === 404 && comment.liked_by_me) patch(comment.id, { liked_by_me: false })
      else setError(errorText(err, 'Nepavyko'))
    }
  }

  return (
    <section className="comments">
      <h3>Komentarai</h3>

      {canAct ? (
        <CommentForm onSubmit={create} />
      ) : !user ? (
        <p className="muted">
          <Link to="/login">Prisijunkite</Link>, kad galėtumėte komentuoti
        </p>
      ) : null}

      {error && <p className="form-error" role="alert">{error}</p>}

      {items.length === 0 && !loading && !error && <p className="muted">Komentarų dar nėra</p>}

      <ul className="comment-list">
        {items.map((c) => (
          <CommentItem
            key={c.id}
            comment={c}
            canAct={canAct}
            isMine={c.user_id === user?.id}
            onLike={toggleLike}
            onDelete={remove}
          />
        ))}
      </ul>

      {loading && <p className="muted">Kraunama…</p>}
      {hasMore && !loading && (
        <button type="button" className="more-btn" onClick={() => load(page + 1)}>
          Rodyti daugiau
        </button>
      )}
    </section>
  )
}
