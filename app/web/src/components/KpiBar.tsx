interface Kpis {
  active_vehicles: number;
  msgs_per_sec: number;
  alerts_per_min: number;
  leader_instance: string | null;
}

export default function KpiBar({ kpis }: { kpis: Kpis | null }) {
  return (
    <div className="kpi-bar">
      <Tile label="Active vehicles" value={kpis?.active_vehicles ?? "—"} />
      <Tile label="Messages / sec" value={kpis?.msgs_per_sec ?? "—"} />
      <Tile label="Alerts (last min)" value={kpis?.alerts_per_min ?? "—"} />
      <Tile label="Leader" value={kpis?.leader_instance ?? "—"} />
    </div>
  );
}

function Tile({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
    </div>
  );
}
