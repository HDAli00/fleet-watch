/**
 * WindowSelector — toggle between telemetry time windows.
 */
import type { TelemetryWindow } from "../types";

interface WindowSelectorProps {
  selected: TelemetryWindow;
  onChange: (w: TelemetryWindow) => void;
}

const WINDOWS: TelemetryWindow[] = ["1h", "6h", "24h", "7d"];
const LABELS: Record<TelemetryWindow, string> = {
  "1h": "1 Hour",
  "6h": "6 Hours",
  "24h": "24 Hours",
  "7d": "7 Days",
};

export function WindowSelector({ selected, onChange }: WindowSelectorProps) {
  return (
    <div style={{ display: "flex", gap: 4 }}>
      {WINDOWS.map((w) => (
        <button
          key={w}
          onClick={() => onChange(w)}
          style={{
            padding: "4px 12px",
            borderRadius: 4,
            border: "1px solid #cbd5e1",
            background: selected === w ? "#2563eb" : "#fff",
            color: selected === w ? "#fff" : "#374151",
            cursor: "pointer",
            fontWeight: selected === w ? 600 : 400,
          }}
        >
          {LABELS[w]}
        </button>
      ))}
    </div>
  );
}
