import { useEffect, useState } from "react";
import { useSSE } from "../api/sse";
import type { FleetEvent, VehiclePosition } from "../api/client";

interface Kpis {
  active_vehicles: number;
  msgs_per_sec: number;
  alerts_per_min: number;
  leader_instance: string | null;
}

interface SnapshotPayload {
  ts: string;
  kpis: Kpis;
  positions: VehiclePosition[];
}

interface PositionsPayload {
  positions: VehiclePosition[];
}

export function useFleetStream() {
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [positions, setPositions] = useState<Map<string, VehiclePosition>>(new Map());
  const [events, setEvents] = useState<FleetEvent[]>([]);

  useSSE("/api/stream/fleet", (event, data) => {
    if (event === "snapshot") {
      const payload = data as SnapshotPayload;
      setKpis(payload.kpis);
      const next = new Map<string, VehiclePosition>();
      for (const p of payload.positions) next.set(p.vehicle_id, p);
      setPositions(next);
    } else if (event === "kpis") {
      const payload = data as SnapshotPayload;
      setKpis(payload.kpis);
    } else if (event === "positions") {
      const payload = data as PositionsPayload;
      setPositions((prev) => {
        const next = new Map(prev);
        for (const p of payload.positions) next.set(p.vehicle_id, p);
        return next;
      });
    } else if (event === "event") {
      const ev = data as FleetEvent;
      setEvents((prev) => [{ ...ev, id: ev.id ?? Date.now() }, ...prev].slice(0, 100));
    }
  });

  // Backfill events on mount.
  useEffect(() => {
    fetch("/api/events?limit=50")
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: FleetEvent[]) => setEvents(rows))
      .catch(() => undefined);
  }, []);

  return { kpis, positions, events };
}
