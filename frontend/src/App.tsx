/**
 * Solar IoT Platform Dashboard
 * One-page app: site selector → panel list → power chart + anomaly table.
 */
import { useEffect, useState } from "react";
import { api } from "./api/client";
import { AnomalyTable } from "./components/AnomalyTable";
import { PowerChart } from "./components/PowerChart";
import { SiteSelector } from "./components/SiteSelector";
import { WindowSelector } from "./components/WindowSelector";
import { useAnomalies } from "./hooks/useAnomalies";
import { useTelemetry } from "./hooks/useTelemetry";
import type { Panel, Site, TelemetryWindow } from "./types";

export default function App() {
  const [sites, setSites] = useState<Site[]>([]);
  const [panels, setPanels] = useState<Panel[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [selectedPanelId, setSelectedPanelId] = useState<string | null>(null);
  const [window, setWindow] = useState<TelemetryWindow>("1h");

  const { readings, loading: telLoading, error: telError } = useTelemetry(
    selectedPanelId,
    window
  );
  const { anomalies, loading: anomLoading } = useAnomalies(window);

  useEffect(() => {
    api.sites.list().then(setSites).catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedSiteId) return;
    api.panels
      .list(selectedSiteId)
      .then((ps) => {
        setPanels(ps);
        setSelectedPanelId(ps[0]?.panel_id ?? null);
      })
      .catch(console.error);
  }, [selectedSiteId]);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 1100, margin: "0 auto", padding: 24 }}>
      <header style={{ borderBottom: "2px solid #2563eb", paddingBottom: 12, marginBottom: 24 }}>
        <h1 style={{ margin: 0, color: "#1e3a5f" }}>Solar IoT Platform</h1>
        <p style={{ margin: "4px 0 0", color: "#64748b" }}>
          Real-time panel telemetry &amp; KNMI weather correlation
        </p>
      </header>

      {/* Controls */}
      <section style={{ display: "flex", gap: 24, alignItems: "center", marginBottom: 24, flexWrap: "wrap" }}>
        <SiteSelector
          sites={sites}
          selectedSiteId={selectedSiteId}
          onSelect={setSelectedSiteId}
        />
        {panels.length > 0 && (
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontWeight: 600 }}>Panel:</span>
            <select
              value={selectedPanelId ?? ""}
              onChange={(e) => setSelectedPanelId(e.target.value)}
              style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid #cbd5e1" }}
            >
              {panels.map((p) => (
                <option key={p.panel_id} value={p.panel_id}>
                  {p.panel_id} ({p.rated_power_w}W)
                </option>
              ))}
            </select>
          </label>
        )}
        <WindowSelector selected={window} onChange={setWindow} />
      </section>

      {/* Power Chart */}
      <section style={{ marginBottom: 32 }}>
        <h2 style={{ color: "#1e3a5f", marginBottom: 8 }}>AC Output</h2>
        {telError && (
          <p style={{ color: "#dc2626" }}>Error loading telemetry: {telError}</p>
        )}
        {!selectedPanelId && <p style={{ color: "#94a3b8" }}>Select a site and panel to view output.</p>}
        {selectedPanelId && !telLoading && readings.length === 0 && (
          <p style={{ color: "#94a3b8" }}>No data in selected window.</p>
        )}
        {readings.length > 0 && <PowerChart readings={readings} />}
      </section>

      {/* Anomaly Table */}
      <section>
        <h2 style={{ color: "#1e3a5f", marginBottom: 8 }}>
          Recent Anomalies{" "}
          {anomalies.length > 0 && (
            <span
              style={{
                background: "#dc2626",
                color: "#fff",
                borderRadius: 12,
                padding: "2px 8px",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {anomalies.length}
            </span>
          )}
        </h2>
        <AnomalyTable anomalies={anomalies} loading={anomLoading} />
      </section>
    </div>
  );
}
