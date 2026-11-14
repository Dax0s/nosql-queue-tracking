import { useCallback, useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png'
import iconUrl from 'leaflet/dist/images/marker-icon.png'
import shadowUrl from 'leaflet/dist/images/marker-shadow.png'
import { Marker, Popup, useMap, useMapEvents } from 'react-leaflet'
import { queues } from '../../api/index.js'

const REFRESH_MS = 30000
const DEBOUNCE_MS = 300

const pinIcon = L.icon({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))

export default function QueuePins({ extraQueues = [] }) {
  const map = useMap()
  const [points, setPoints] = useState([])
  const requestId = useRef(0)

  const load = useCallback(async () => {
    const id = ++requestId.current
    const bounds = map.getBounds()
    try {
      const data = await queues.map(
        {
          min_lat: clamp(bounds.getSouth(), -90, 90),
          min_lng: clamp(bounds.getWest(), -180, 180),
          max_lat: clamp(bounds.getNorth(), -90, 90),
          max_lng: clamp(bounds.getEast(), -180, 180),
        },
        Math.round(map.getZoom()),
      )
      if (id === requestId.current) setPoints(data)
    } catch {
      // keep the pins already shown
    }
  }, [map])

  useEffect(() => {
    load()
    const interval = setInterval(load, REFRESH_MS)
    return () => clearInterval(interval)
  }, [load])

  const debounce = useRef(null)
  useMapEvents({
    moveend: () => {
      clearTimeout(debounce.current)
      debounce.current = setTimeout(load, DEBOUNCE_MS)
    },
  })
  useEffect(() => () => clearTimeout(debounce.current), [])

  const known = new Set(points.map((point) => point.id))
  const visible = [...points, ...extraQueues.filter((queue) => !known.has(queue.id))]

  return visible.map((queue) => (
    <Marker key={queue.id} position={[queue.lat, queue.lng]} icon={pinIcon}>
      <Popup>
        <div className="queue-popup">
          <h3>{queue.title}</h3>
        </div>
      </Popup>
    </Marker>
  ))
}
