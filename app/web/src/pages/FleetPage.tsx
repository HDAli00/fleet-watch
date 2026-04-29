import KpiBar from "../components/KpiBar";
import FleetMap from "../components/FleetMap";
import AlertFeed from "../components/AlertFeed";
import { useFleetStream } from "../hooks/useFleetStream";

export default function FleetPage() {
  const { kpis, positions, events } = useFleetStream();
  return (
    <div className="fleet">
      <KpiBar kpis={kpis} />
      <div className="fleet-body">
        <FleetMap positions={positions} />
        <AlertFeed events={events} />
      </div>
    </div>
  );
}
