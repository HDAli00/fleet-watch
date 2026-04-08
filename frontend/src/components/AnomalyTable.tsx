/**
 * AnomalyTable — shows recent anomalous readings in a sortable table.
 */
import type { TelemetryReading } from "../types";

interface AnomalyTableProps {
  anomalies: TelemetryReading[];
  loading: boolean;
}

const STATUS_COLOURS: Record<string, string> = {
  ok: "#16a34a",
  warning: "#d97706",
  error: "#dc2626",
  offline: "#6b7280",
};

function formatTs(iso: string): string {
  return new Date(iso).toLocaleString("nl-NL", { timeZone: "Europe/Amsterdam" });
}

export function AnomalyTable({ anomalies, loading }: AnomalyTableProps) {
  if (loading) return <p>Loading anomalies…</p>;
  if (anomalies.length === 0) return <p>No recent anomalies.</p>;

  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
      <thead>
        <tr style={{ background: "#f1f5f9" }}>
          <th style={th}>Panel</th>
          <th style={th}>Time</th>
          <th style={th}>AC Power (W)</th>
          <th style={th}>Expected (W)</th>
          <th style={th}>Status</th>
        </tr>
      </thead>
      <tbody>
        {anomalies.map((r) => (
          <tr key={r.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
            <td style={td}>{r.panel_id}</td>
            <td style={td}>{formatTs(r.ts)}</td>
            <td style={{ ...td, color: "#dc2626", fontWeight: 600 }}>
              {r.ac_power_w.toFixed(1)}
            </td>
            <td style={td}>
              {r.expected_ac_power_w != null ? r.expected_ac_power_w.toFixed(1) : "—"}
            </td>
            <td style={{ ...td, color: STATUS_COLOURS[r.status] ?? "#000" }}>
              {r.status}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const th: React.CSSProperties = {
  padding: "8px 12px",
  textAlign: "left",
  fontWeight: 600,
};

const td: React.CSSProperties = {
  padding: "6px 12px",
};
