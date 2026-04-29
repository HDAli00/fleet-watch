import L from "leaflet";
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import type { VehiclePosition } from "../api/client";

const STATUS_COLORS: Record<string, string> = {
  ok: "#3fb950",
  warn: "#d29922",
  critical: "#f85149",
  offline: "#6e7681",
};

function statusFor(p: VehiclePosition): string {
  if (p.status) return p.status;
  if (p.coolant_c !== undefined && p.coolant_c >= 110) return "critical";
  if (p.battery_v !== undefined && p.battery_v < 11.5) return "critical";
  if (p.coolant_c !== undefined && p.coolant_c >= 100) return "warn";
  if (p.battery_v !== undefined && p.battery_v < 12.0) return "warn";
  return "ok";
}

function makeIcon(color: string): L.DivIcon {
  return L.divIcon({
    className: "vehicle-marker",
    html: `<div style="background:${color};width:10px;height:10px;border-radius:50%;border:2px solid #000;"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

export default function FleetMap({ positions }: { positions: Map<string, VehiclePosition> }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<string, L.Marker>>(new Map());
  const lastStatusRef = useRef<Map<string, string>>(new Map());
  const navigate = useNavigate();
  const navRef = useRef(navigate);
  navRef.current = navigate;

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      center: [50.0, 5.0],
      zoom: 4,
      preferCanvas: true,
      worldCopyJump: true,
    });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "© OpenStreetMap",
    }).addTo(map);
    mapRef.current = map;
    const markers = markersRef.current;
    const lastStatus = lastStatusRef.current;
    return () => {
      map.remove();
      mapRef.current = null;
      markers.clear();
      lastStatus.clear();
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const markers = markersRef.current;
    const lastStatus = lastStatusRef.current;

    positions.forEach((p, vid) => {
      const status = statusFor(p);
      const existing = markers.get(vid);
      if (existing) {
        existing.setLatLng([p.lat, p.lon]);
        if (lastStatus.get(vid) !== status) {
          existing.setIcon(makeIcon(STATUS_COLORS[status]));
          lastStatus.set(vid, status);
        }
      } else {
        const marker = L.marker([p.lat, p.lon], { icon: makeIcon(STATUS_COLORS[status]) });
        marker.on("click", () => navRef.current(`/vehicles/${vid}`));
        marker.bindTooltip(vid, { direction: "top", offset: [0, -8] });
        marker.addTo(map);
        markers.set(vid, marker);
        lastStatus.set(vid, status);
      }
    });
  }, [positions]);

  return (
    <div className="map-wrap">
      <div ref={containerRef} className="map" />
    </div>
  );
}
