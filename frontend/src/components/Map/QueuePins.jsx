import L from 'leaflet'
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png'
import iconUrl from 'leaflet/dist/images/marker-icon.png'
import shadowUrl from 'leaflet/dist/images/marker-shadow.png'
import { Marker, Tooltip } from 'react-leaflet'

const pinIcon = L.icon({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  tooltipAnchor: [1, -34],
  shadowSize: [41, 41],
})

// Atskirų eilių pinai; paspaudus atidaromas eilės langas
export default function QueuePins({ points, onSelect }) {
  return points.map((queue) => (
    <Marker
      key={queue.id}
      position={[queue.lat, queue.lng]}
      icon={pinIcon}
      eventHandlers={{ click: () => onSelect?.(queue.id) }}
    >
      <Tooltip direction="top">{queue.title}</Tooltip>
    </Marker>
  ))
}
