import type { FleetEvent } from "../api/client";

export default function EventList({ events }: { events: FleetEvent[] }) {
  return (
    <div className="events-card">
      <h4>Recent events</h4>
      {events.length === 0 && <div className="muted">No events for this vehicle.</div>}
      {events.map((e, i) => (
        <div key={e.id ?? `${e.ts}-${i}`} className={`alert-row ${e.severity}`}>
          <div className="meta">{new Date(e.ts).toLocaleTimeString()} · {e.kind}</div>
          <div>{e.message}</div>
        </div>
      ))}
    </div>
  );
}
