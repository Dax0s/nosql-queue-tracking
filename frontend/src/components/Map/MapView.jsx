import { useCallback, useState } from 'react'
import { MapContainer, Popup, TileLayer, useMapEvents } from 'react-leaflet'
import { useAuth } from '../../auth/AuthContext.jsx'
import CreateQueuePopup from './CreateQueuePopup.jsx'

const VILNIUS = [54.6872, 25.2797]
export const PIN_ZOOM = 15 // nuo šio zoom vietoj heatmapo rodomi pinai

// TODO(A):
// - /queues/map užklausa pajudinus žemėlapį (debounce) ir kas 30 s
// - heatmapas (leaflet.heat), kai zoom < PIN_ZOOM; pinai, kai zoom >= PIN_ZOOM
// - pino paspaudimas -> onSelectQueue(id)
function MapClick({ onClick }) {
  useMapEvents({ click: (e) => onClick(e.latlng) })
  return null
}

export default function MapView({ onSelectQueue, onQueueCreated }) {
  const { user } = useAuth()
  const [newQueueAt, setNewQueueAt] = useState(null)
  const closePopup = useCallback(() => setNewQueueAt(null), [])
  const canCreate = user?.role !== 'admin'

  return (
    <MapContainer center={VILNIUS} zoom={12} className="map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {canCreate && <MapClick onClick={setNewQueueAt} />}
      {canCreate && newQueueAt && (
        <Popup
          key={`${newQueueAt.lat},${newQueueAt.lng}`}
          position={newQueueAt}
          eventHandlers={{ remove: closePopup }}
        >
          <CreateQueuePopup
            position={newQueueAt}
            onClose={closePopup}
            onCreated={onQueueCreated}
          />
        </Popup>
      )}
    </MapContainer>
  )
}
