import { Link, Route, Routes } from "react-router-dom";
import FleetPage from "./pages/FleetPage";
import VehiclePage from "./pages/VehiclePage";

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="dot" /> Fleet Telemetry
        </Link>
        <span className="muted">live · 1Hz · ~500 vehicles</span>
      </header>
      <Routes>
        <Route path="/" element={<FleetPage />} />
        <Route path="/vehicles/:id" element={<VehiclePage />} />
      </Routes>
    </div>
  );
}
