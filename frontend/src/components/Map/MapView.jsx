import { MapContainer, TileLayer } from 'react-leaflet'

const VILNIUS = [54.6872, 25.2797]
export const PIN_ZOOM = 15 // nuo šio zoom vietoj heatmapo rodomi pinai

// TODO(A):
// - /queues/map užklausa pajudinus žemėlapį (debounce) ir kas 30 s
// - heatmapas (leaflet.heat), kai zoom < PIN_ZOOM; pinai, kai zoom >= PIN_ZOOM
// - pino paspaudimas -> onSelectQueue(id)
// - mygtukas „Nauja eilė“
export default function MapView({ onSelectQueue }) {
  return (
    <MapContainer center={VILNIUS} zoom={12} className="map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
    </MapContainer>
  )
}
