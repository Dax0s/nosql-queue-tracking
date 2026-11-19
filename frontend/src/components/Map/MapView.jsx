import { useCallback, useState } from 'react'
import { MapContainer, Popup, TileLayer, useMapEvents } from 'react-leaflet'
import { useAuth } from '../../auth/AuthContext.jsx'
import CreateQueuePopup from './CreateQueuePopup.jsx'
import QueueLayer from './QueueLayer.jsx'

const VILNIUS = [54.6872, 25.2797]
const WEIGHT_MAX = 360 // spec. 6 skyrius

function MapClick({ onClick }) {
  useMapEvents({ click: (e) => onClick(e.latlng) })
  return null
}

export default function MapView({ onSelectQueue }) {
  const { user } = useAuth()
  const [newQueueAt, setNewQueueAt] = useState(null)
  const [createdQueues, setCreatedQueues] = useState([])
  const closePopup = useCallback(() => setNewQueueAt(null), [])
  const addCreatedQueue = useCallback(
    (queue) =>
      setCreatedQueues((prev) => [...prev, { ...queue, intensity: queue.weight / WEIGHT_MAX }]),
    [],
  )
  const canCreate = user?.role !== 'admin'

  return (
    <MapContainer center={VILNIUS} zoom={12} className="map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <QueueLayer extraQueues={createdQueues} onSelectQueue={onSelectQueue} />
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
            onCreated={addCreatedQueue}
          />
        </Popup>
      )}
    </MapContainer>
  )
}
