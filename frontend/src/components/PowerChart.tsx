/**
 * PowerChart — AC power (W) over time for a single panel.
 * Anomalous points rendered in red.
 */
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TelemetryReading } from "../types";

interface PowerChartProps {
  readings: TelemetryReading[];
  height?: number;
}

interface ChartPoint {
  ts: string; // formatted timestamp label
  ac_power_w: number;
  anomaly: boolean;
}

function formatTs(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function PowerChart({ readings, height = 300 }: PowerChartProps) {
  const points: ChartPoint[] = readings.map((r) => ({
    ts: formatTs(r.ts),
    ac_power_w: r.ac_power_w,
    anomaly: r.anomaly_flag,
  }));

  const normalPoints = points.filter((p) => !p.anomaly);
  const anomalyPoints = points.filter((p) => p.anomaly);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={normalPoints}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="ts" label={{ value: "Time", position: "insideBottom", offset: -5 }} />
        <YAxis label={{ value: "AC Power (W)", angle: -90, position: "insideLeft" }} />
        <Tooltip formatter={(v: number) => [`${v.toFixed(1)} W`, "AC Power"]} />
        <Line
          type="monotone"
          dataKey="ac_power_w"
          stroke="#2563eb"
          dot={false}
          strokeWidth={2}
        />
        {anomalyPoints.length > 0 && (
          <Scatter
            data={anomalyPoints}
            dataKey="ac_power_w"
            fill="#dc2626"
            name="Anomaly"
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
