import { useEffect, useRef } from 'react'
import { HeatLayer as LeafletHeatLayer } from 'leaflet.heat'
import { useMap } from 'react-leaflet'

// maxZoom: 0 – leaflet.heat kitaip dalija intensyvumą iš 2^(map.maxZoom − zoom),
// todėl atitolinus net 360 svorio eilė būtų vos matoma. Spalva = tik svoris.
const OPTIONS = { radius: 25, blur: 18, minOpacity: 0.3, max: 1, maxZoom: 0 }

const toLatLngs = (points) => points.map((p) => [p.lat, p.lng, p.intensity])

// Heatmapas: intensyvumas = svoris_dabar / 360 (skaičiuoja backend)
export default function HeatLayer({ points }) {
  const map = useMap()
  const layer = useRef(null)

  useEffect(() => {
    const heat = new LeafletHeatLayer([], OPTIONS).addTo(map)
    layer.current = heat
    return () => {
      heat.remove()
      layer.current = null
    }
  }, [map])

  useEffect(() => {
    layer.current?.setLatLngs(toLatLngs(points))
  }, [points])

  return null
}
