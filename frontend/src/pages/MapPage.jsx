import { useState } from 'react'
import MapView from '../components/Map/MapView.jsx'
import QueuePanel from '../components/QueuePanel/QueuePanel.jsx'

export default function MapPage() {
  const [selectedQueueId, setSelectedQueueId] = useState(null)

  return (
    <>
      <MapView onSelectQueue={setSelectedQueueId} />
      {selectedQueueId && (
        <QueuePanel queueId={selectedQueueId} onClose={() => setSelectedQueueId(null)} />
      )}
    </>
  )
}
