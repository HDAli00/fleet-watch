interface Props {
  label: string;
  value: number | null | undefined;
  unit?: string;
  precision?: number;
  status?: "ok" | "warn" | "critical" | "offline";
}

export default function Gauge({ label, value, unit, precision = 1, status = "ok" }: Props) {
  const formatted = value == null ? "—" : value.toFixed(precision);
  return (
    <div className="gauge">
      <div className="label">{label}</div>
      <div className={`value status-${status}`}>
        {formatted}
        {unit && <span className="unit"> {unit}</span>}
      </div>
    </div>
  );
}
