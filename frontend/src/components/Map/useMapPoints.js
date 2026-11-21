import { useCallback, useEffect, useRef, useState } from 'react'
import { useMap, useMapEvents } from 'react-leaflet'
import { queues } from '../../api/index.js'

const REFRESH_MS = 30000
const DEBOUNCE_MS = 300

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))

// Eilių taškai matomai žemėlapio sričiai: pajudinus (su debounce) ir kas 30 s.
// Naudojama tik MapContainer viduje.
export default function useMapPoints() {
  const map = useMap()
  const [points, setPoints] = useState([])
  const [zoom, setZoom] = useState(() => map.getZoom())
  const requestId = useRef(0)
  const debounce = useRef(null)

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
      // Ignoruojam pavėlavusius senesnių užklausų atsakymus
      if (id === requestId.current) setPoints(data)
    } catch {
      // paliekam jau rodomus taškus
    }
  }, [map])

  useEffect(() => {
    load()
    const interval = setInterval(load, REFRESH_MS)
    return () => {
      clearInterval(interval)
      clearTimeout(debounce.current)
    }
  }, [load])

  useMapEvents({
    zoomend: () => setZoom(map.getZoom()),
    moveend: () => {
      clearTimeout(debounce.current)
      debounce.current = setTimeout(load, DEBOUNCE_MS)
    },
  })

  return { points, zoom }
}
