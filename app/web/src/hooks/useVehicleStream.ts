import { useEffect, useState } from "react";
import { useSSE } from "../api/sse";
import { api, type FleetEvent, type VehicleHistory, type VehiclePosition, type VehicleSummary } from "../api/client";

export function useVehicleStream(id: string) {
  const [summary, setSummary] = useState<VehicleSummary | null>(null);
  const [position, setPosition] = useState<VehiclePosition | null>(null);
  const [history, setHistory] = useState<VehicleHistory | null>(null);
  const [events, setEvents] = useState<FleetEvent[]>([]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.vehicle(id), api.history(id, 60), api.events(50)])
      .then(([v, h, evs]) => {
        if (cancelled) return;
        setSummary(v);
        setHistory(h);
        setEvents(evs.filter((e) => e.vehicle_id === id));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [id]);

  useSSE(
    `/api/stream/vehicles/${id}`,
    (event, data) => {
      if (event === "position") {
        setPosition(data as VehiclePosition);
      } else if (event === "event") {
        const ev = data as FleetEvent;
        setEvents((prev) => [{ ...ev, id: ev.id ?? Date.now() }, ...prev].slice(0, 100));
      }
    },
    [id]
  );

  return { summary, position, history, events };
}
