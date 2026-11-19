import HeatLayer from './HeatLayer.jsx'
import QueuePins from './QueuePins.jsx'
import useMapPoints from './useMapPoints.js'

export const PIN_ZOOM = 15 // nuo šio zoom vietoj heatmapo rodomi pinai

// Toli atitolinus – heatmapas, priartinus – pinai.
// `extraQueues`: ką tik sukurtos eilės, kurių dar nėra žemėlapio cache (30 s).
export default function QueueLayer({ extraQueues = [], onSelectQueue }) {
  const { points, zoom } = useMapPoints()

  const known = new Set(points.map((p) => p.id))
  const visible = [...points, ...extraQueues.filter((q) => !known.has(q.id))]

  return zoom >= PIN_ZOOM ? (
    <QueuePins points={visible} onSelect={onSelectQueue} />
  ) : (
    <HeatLayer points={visible} />
  )
}
