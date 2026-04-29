import type { FleetEvent } from "../api/client";

export default function AlertFeed({ events }: { events: FleetEvent[] }) {
  return (
    <div className="alert-feed">
      <h3>Alert feed</h3>
      {events.length === 0 && <div className="muted" style={{ padding: "0 10px" }}>No alerts yet…</div>}
      {events.map((e) => (
        <div key={`${e.id ?? e.vehicle_id + e.ts}`} className={`alert-row ${e.severity}`}>
          <div className="meta">
            {fmtTime(e.ts)} · <a href={`/vehicles/${e.vehicle_id}`}>{e.vehicle_id}</a> · {e.kind}
          </div>
          <div>{e.message}</div>
        </div>
      ))}
    </div>
  );
}

function fmtTime(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString();
  } catch {
    return ts;
  }
}
