import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { reports } from '../api/index.js'

const PERIODS = { day: 'Diena', week: 'Savaitė', month: 'Mėnuo' }
const WEEKDAYS = ['Pr', 'An', 'Tr', 'Ke', 'Pn', 'Še', 'Se']
const HOURS = Array.from({ length: 24 }, (_, h) => h)
const COLORS = { users: '#2f6fdf', queues: '#e8833a', checkins: '#2a9d6f' }

const isoDate = (d) => {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const daysAgo = (n) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return isoDate(d)
}

function periodLabel(value, period) {
  if (period === 'month') return value.slice(0, 7)
  return value.slice(5) // MM-DD
}

const errorText = (err) => {
  if (err.status === 401) return 'Prisijunkite iš naujo'
  if (err.status === 403) return 'Ataskaitos prieinamos tik administratoriui'
  return err.message || 'Nepavyko įkelti ataskaitos'
}

// Įkelia ataskaitą, kai pasikeičia `deps`. Seni atsakymai ignoruojami.
function useReport(load, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true })

  useEffect(() => {
    let cancelled = false
    setState((s) => ({ ...s, error: null, loading: true }))
    load()
      .then((data) => !cancelled && setState({ data, error: null, loading: false }))
      .catch((error) => !cancelled && setState({ data: null, error, loading: false }))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return state
}

function Section({ title, controls, state, isEmpty, wide, children }) {
  let body
  if (state.error) body = <p className="form-error">{errorText(state.error)}</p>
  else if (!state.data) body = <p className="muted">Įkeliama…</p>
  else if (isEmpty?.(state.data)) body = <p className="muted">Duomenų nėra</p>
  else body = children(state.data)

  return (
    <section className={`report${wide ? ' report-wide' : ''}${state.loading && state.data ? ' report-loading' : ''}`}>
      <header className="report-head">
        <h2>{title}</h2>
        {controls && <div className="report-controls">{controls}</div>}
      </header>
      {body}
    </section>
  )
}

const allZero = (rows, keys) => rows.every((r) => keys.every((k) => !r[k]))

function ActivityReport({ filters }) {
  const state = useReport(
    () => reports.activity(filters),
    [filters.period, filters.from, filters.to],
  )
  return (
    <Section
      title="Nauji vartotojai ir eilės"
      state={state}
      isEmpty={(rows) => allZero(rows, ['new_users', 'new_queues'])}
    >
      {(rows) => (
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 0, left: -16 }}>
            <CartesianGrid stroke="#eef1f4" vertical={false} />
            <XAxis dataKey="period_start" tickFormatter={(v) => periodLabel(v, filters.period)} fontSize={12} />
            <YAxis allowDecimals={false} fontSize={12} />
            <Tooltip />
            <Legend />
            <Line dataKey="new_users" name="Vartotojai" stroke={COLORS.users} strokeWidth={2} dot={false} />
            <Line dataKey="new_queues" name="Eilės" stroke={COLORS.queues} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </Section>
  )
}

function CheckinsReport({ filters }) {
  const state = useReport(
    () => reports.checkins(filters),
    [filters.period, filters.from, filters.to],
  )
  return (
    <Section title="Check-in skaičius" state={state} isEmpty={(rows) => allZero(rows, ['checkins'])}>
      {(rows) => (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={rows} margin={{ top: 8, right: 16, bottom: 0, left: -16 }}>
            <CartesianGrid stroke="#eef1f4" vertical={false} />
            <XAxis dataKey="period_start" tickFormatter={(v) => periodLabel(v, filters.period)} fontSize={12} />
            <YAxis allowDecimals={false} fontSize={12} />
            <Tooltip />
            <Bar dataKey="checkins" name="Check-in" fill={COLORS.checkins} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </Section>
  )
}

function CheckoutRateReport({ filters }) {
  const state = useReport(
    () => reports.checkoutRate({ from: filters.from, to: filters.to }),
    [filters.from, filters.to],
  )
  return (
    <Section title="Check-out dalis" state={state}>
      {(d) => (
        <div className="kpi">
          <span className="kpi-value">{d.rate === null ? '–' : `${(d.rate * 100).toFixed(1)} %`}</span>
          <span className="muted">
            {d.checkouts} check-out iš {d.checkins} check-in
          </span>
        </div>
      )}
    </Section>
  )
}

function PopularQueuesReport({ selectedQueue, onSelectQueue }) {
  const [days, setDays] = useState(7)
  const [sortBy, setSortBy] = useState('views')
  const state = useReport(() => reports.popularQueues({ days, sort_by: sortBy }), [days, sortBy])

  const controls = (
    <>
      <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
        {[7, 30, 90, 365].map((d) => (
          <option key={d} value={d}>{d} d.</option>
        ))}
      </select>
      <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
        <option value="views">Pagal peržiūras</option>
        <option value="checkins">Pagal check-in</option>
      </select>
    </>
  )

  return (
    <Section wide title="Populiariausios eilės" controls={controls} state={state} isEmpty={(rows) => !rows.length}>
      {(rows) => (
        <table className="report-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Eilė</th>
              <th className="num">Peržiūros</th>
              <th className="num">Check-in</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.queue_id} className={r.queue_id === selectedQueue?.id ? 'selected' : undefined}>
                <td>{i + 1}</td>
                <td>{r.title}</td>
                <td className="num">{r.views}</td>
                <td className="num">{r.checkins}</td>
                <td className="num">
                  <button
                    type="button"
                    className="link-btn"
                    onClick={() => onSelectQueue({ id: r.queue_id, title: r.title })}
                  >
                    Laukimo laikas
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Section>
  )
}

function WaitTimesReport({ queue, onClear }) {
  const state = useReport(() => reports.waitTimes(queue?.id), [queue?.id])

  const controls = queue && (
    <span className="chip">
      {queue.title}
      <button type="button" onClick={onClear} aria-label="Rodyti visas eiles">×</button>
    </span>
  )

  return (
    <Section
      wide
      title={queue ? 'Vid. laukimo laikas (min)' : 'Vid. laukimo laikas (min), visos eilės'}
      controls={controls}
      state={state}
      isEmpty={(rows) => !rows.length}
    >
      {(rows) => {
        const cells = new Map(rows.map((r) => [`${r.weekday}-${r.hour}`, r]))
        const max = Math.max(...rows.map((r) => r.avg_wait_min), 1)
        return (
          <div className="heatgrid-wrap">
            <table className="heatgrid">
              <thead>
                <tr>
                  <th />
                  {HOURS.map((h) => <th key={h}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {WEEKDAYS.map((name, i) => (
                  <tr key={name}>
                    <th>{name}</th>
                    {HOURS.map((h) => {
                      const c = cells.get(`${i + 1}-${h}`)
                      if (!c) return <td key={h} className="empty" />
                      const alpha = 0.12 + 0.88 * (c.avg_wait_min / max)
                      return (
                        <td
                          key={h}
                          style={{ background: `rgba(232, 131, 58, ${alpha})` }}
                          title={`${name} ${h}:00 – ${c.avg_wait_min} min (${c.samples} matav.)`}
                        >
                          {Math.round(c.avg_wait_min)}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      }}
    </Section>
  )
}

function AgeReport() {
  const state = useReport(() => reports.activityByAge(), [])
  return (
    <Section title="Aktyvumas pagal amžiaus grupes" state={state} isEmpty={(rows) => !rows.length}>
      {(rows) => (
        <div className="age-report">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={rows} margin={{ top: 8, right: 16, bottom: 0, left: -8 }}>
              <CartesianGrid stroke="#eef1f4" vertical={false} />
              <XAxis dataKey="age_group" tickFormatter={(v) => (v === 'unknown' ? 'nežinoma' : v)} fontSize={12} />
              <YAxis allowDecimals={false} fontSize={12} />
              <Tooltip labelFormatter={(v) => (v === 'unknown' ? 'nežinoma' : v)} />
              <Bar dataKey="events" name="Įvykiai" fill={COLORS.users} />
            </BarChart>
          </ResponsiveContainer>
          <table className="report-table">
            <thead>
              <tr>
                <th>Grupė</th>
                <th className="num">Įvykiai</th>
                <th className="num">Vartotojai</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.age_group}>
                  <td>{r.age_group === 'unknown' ? 'nežinoma' : r.age_group}</td>
                  <td className="num">{r.events}</td>
                  <td className="num">{r.users}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  )
}

export default function ReportsPage() {
  const [filters, setFilters] = useState({ period: 'day', from: daysAgo(30), to: isoDate(new Date()) })
  const [waitQueue, setWaitQueue] = useState(null)
  const set = (key) => (e) => setFilters((f) => ({ ...f, [key]: e.target.value || undefined }))
  const invalidRange = filters.from && filters.to && filters.from > filters.to
  // Kol intervalas neteisingas, ataskaitos rodo paskutinį teisingą
  const [applied, setApplied] = useState(filters)
  useEffect(() => {
    if (!invalidRange) setApplied(filters)
  }, [filters, invalidRange])

  return (
    <div className="page reports-page">
      <h1>Ataskaitos</h1>

      <div className="report-filters">
        <label>
          Nuo
          <input type="date" value={filters.from ?? ''} onChange={set('from')} />
        </label>
        <label>
          Iki
          <input type="date" value={filters.to ?? ''} onChange={set('to')} />
        </label>
        <div className="segmented" role="group" aria-label="Periodas">
          {Object.entries(PERIODS).map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={filters.period === value ? 'active' : undefined}
              onClick={() => setFilters((f) => ({ ...f, period: value }))}
            >
              {label}
            </button>
          ))}
        </div>
        {invalidRange && <p className="form-error">„Nuo“ negali būti vėliau nei „Iki“</p>}
      </div>

      <div className="report-grid">
        <ActivityReport filters={applied} />
        <CheckinsReport filters={applied} />
        <CheckoutRateReport filters={applied} />
        <AgeReport />
        <PopularQueuesReport selectedQueue={waitQueue} onSelectQueue={setWaitQueue} />
        <WaitTimesReport queue={waitQueue} onClear={() => setWaitQueue(null)} />
      </div>
      <p className="muted">Ataskaitos atnaujinamos kas 10 min.</p>
    </div>
  )
}
