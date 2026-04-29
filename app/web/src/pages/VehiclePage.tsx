import { useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import Gauge from "../components/Gauge";
import HistoryChart from "../components/HistoryChart";
import EventList from "../components/EventList";
import { useVehicleStream } from "../hooks/useVehicleStream";

export default function VehiclePage() {
  const { id = "" } = useParams<{ id: string }>();
  const { summary, position, history, events } = useVehicleStream(id);

  const seriesByMetric = useMemo(() => {
    const xs: number[] = [];
    const speed: number[] = [];
    const rpm: number[] = [];
    const coolant: number[] = [];
    const battery: number[] = [];
    if (history) {
      for (const p of history.points) {
        xs.push(Math.floor(new Date(p.ts).getTime() / 1000));
        speed.push(p.speed_kph);
        rpm.push(p.rpm);
        coolant.push(p.coolant_c);
        battery.push(p.battery_v);
      }
    }
    return { xs, speed, rpm, coolant, battery };
  }, [history]);

  const status = summary?.status ?? "ok";
  const speedNow = position?.speed_kph ?? summary?.last_speed_kph ?? null;
  const coolantNow = position?.coolant_c ?? summary?.last_coolant_c ?? null;
  const batteryNow = position?.battery_v ?? summary?.last_battery_v ?? null;

  return (
    <div className="vehicle">
      <div className="vhead">
        <div>
          <h1>{id}</h1>
          <div className="muted">
            {summary ? `${summary.year} ${summary.make} ${summary.model} · ${summary.region}` : "loading…"}
          </div>
        </div>
        <Link to="/" className="muted">← back to fleet</Link>
      </div>

      <div className="gauge-row">
        <Gauge label="Speed" value={speedNow} unit="kph" precision={0} status={status} />
        <Gauge label="Coolant" value={coolantNow} unit="°C" status={status} />
        <Gauge label="Battery" value={batteryNow} unit="V" precision={2} status={status} />
        <Gauge label="Status" value={null} status={status} />
      </div>

      <div className="charts">
        <HistoryChart title="Speed (kph)" xs={seriesByMetric.xs} ys={seriesByMetric.speed} color="#58a6ff" />
        <HistoryChart title="RPM" xs={seriesByMetric.xs} ys={seriesByMetric.rpm} color="#d29922" />
        <HistoryChart title="Coolant (°C)" xs={seriesByMetric.xs} ys={seriesByMetric.coolant} color="#f85149" />
        <HistoryChart title="Battery (V)" xs={seriesByMetric.xs} ys={seriesByMetric.battery} color="#3fb950" />
      </div>

      <EventList events={events} />
    </div>
  );
}
