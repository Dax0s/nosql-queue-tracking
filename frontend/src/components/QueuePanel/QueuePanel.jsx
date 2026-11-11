// Eilės langas. Karkasas – A; <Rating /> ir <Comments /> įstato B.
// TODO(A): queues.get(queueId), suvestinė, check-in / check-out mygtukas
export default function QueuePanel({ queueId, onClose }) {
  return (
    <aside className="queue-panel">
      <button onClick={onClose}>Uždaryti</button>
      <h2>Eilė {queueId}</h2>
      {/* <Rating queueId={queueId} /> */}
      {/* <Comments queueId={queueId} /> */}
    </aside>
  )
}
