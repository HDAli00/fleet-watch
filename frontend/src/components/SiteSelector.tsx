/**
 * SiteSelector — dropdown to pick an active site.
 */
import type { Site } from "../types";

interface SiteSelectorProps {
  sites: Site[];
  selectedSiteId: string | null;
  onSelect: (siteId: string) => void;
}

export function SiteSelector({ sites, selectedSiteId, onSelect }: SiteSelectorProps) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontWeight: 600, whiteSpace: "nowrap" }}>Site:</span>
      <select
        value={selectedSiteId ?? ""}
        onChange={(e) => onSelect(e.target.value)}
        style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid #cbd5e1" }}
      >
        <option value="" disabled>
          Select a site…
        </option>
        {sites.map((s) => (
          <option key={s.site_id} value={s.site_id}>
            {s.name} ({s.capacity_kwp} kWp)
          </option>
        ))}
      </select>
    </label>
  );
}
