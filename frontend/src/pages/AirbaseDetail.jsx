import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchAirbase, fetchAirbaseTimeline, fetchAirbaseSummary } from "../utils/api";
import ObservationTimeline from "../components/ObservationTimeline";
import HighResCapture from "../components/HighResCapture";
import ObservationGallery from "../components/ObservationGallery";
import CoordsEditor from "../components/CoordsEditor";
import AnalyticsTab from "../components/AnalyticsTab";
import ReportsTab from "../components/ReportsTab";
import AircraftIntel from "../components/AircraftIntel";

export default function AirbaseDetail() {
  const { id } = useParams();
  const [airbase, setAirbase] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("capture");

  function loadData() {
    return Promise.all([
      fetchAirbase(id),
      fetchAirbaseTimeline(id).catch(() => []),
      fetchAirbaseSummary(id).catch(() => null),
    ]).then(([base, tl, sum]) => {
      setAirbase(base);
      setTimeline(tl);
      setSummary(sum);
    });
  }

  useEffect(() => {
    setLoading(true);
    loadData().finally(() => setLoading(false));
  }, [id]);

  function handleNewObservation() {
    loadData();
  }

  if (loading) return <div className="page-loading">Loading...</div>;
  if (!airbase) return <div className="page-loading">Airbase not found</div>;

  // Aggregate detections across all observations for the intel tab
  const allDetections = {};
  timeline.forEach((obs) => {
    Object.entries(obs.aircraft_types || {}).forEach(([type, count]) => {
      allDetections[type] = Math.max(allDetections[type] || 0, count);
    });
  });

  const tabs = [
    { id: "capture", label: "Capture" },
    { id: "intel", label: "Aircraft Intel" },
    { id: "history", label: `History (${timeline.length})` },
    { id: "analytics", label: "Analytics" },
    { id: "reports", label: "Reports" },
    { id: "settings", label: "Settings" },
  ];

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "#0d1117" }}>
      <header className="app-header">
        <div className="header-brand">
          <Link to="/" style={{ color: "#e0e0e0", textDecoration: "none", display: "flex", alignItems: "center", gap: 10 }}>
            <img src="/logo.png" alt="" className="header-logo" />
            <h1>VAUBAN</h1>
          </Link>
          <span className="header-sub">Airbase Intelligence</span>
        </div>
      </header>

      {/* Airbase header */}
      <div className="airbase-hero">
        <div className="airbase-hero-content">
          <div>
            <h2>{airbase.name}</h2>
            <div className="airbase-hero-meta">
              {airbase.icao_code && <span className="tag tag-blue">{airbase.icao_code}</span>}
              <span className="tag">{airbase.military_district} MD</span>
              <span className="tag">{airbase.region}</span>
              <span className="coords">
                {airbase.latitude.toFixed(4)}, {airbase.longitude.toFixed(4)}
              </span>
            </div>
            <p className="airbase-hero-units">{airbase.known_units}</p>
          </div>
          <div className="airbase-hero-stats">
            <div className="hero-stat">
              <span className="hero-stat-value">{summary?.capture_count || 0}</span>
              <span className="hero-stat-label">Captures</span>
            </div>
            <div className="hero-stat">
              <span className="hero-stat-value">{summary?.total_detections || 0}</span>
              <span className="hero-stat-label">Total Detections</span>
            </div>
            <div className="hero-stat">
              <span className="hero-stat-value">
                {summary?.latest?.total_aircraft ?? "—"}
              </span>
              <span className="hero-stat-label">Last Count</span>
            </div>
          </div>
        </div>

        {/* Latest image preview */}
        {summary?.latest?.images?.[0]?.image_url && (
          <div className="airbase-hero-preview">
            <img
              src={`http://localhost:8000${summary.latest.images[0].image_url}`}
              alt="Latest observation"
            />
            <div className="preview-overlay">
              {new Date(summary.latest.date).toLocaleDateString()} — {summary.latest.total_aircraft} aircraft
            </div>
          </div>
        )}
      </div>

      {/* Tab nav */}
      <div className="tab-nav">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={activeTab === tab.id ? "tab active" : "tab"}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="tab-content">
        {activeTab === "capture" && (
          <div className="card">
            <HighResCapture airbaseId={airbase.id} airbase={airbase} onObservationCreated={handleNewObservation} />
          </div>
        )}

        {activeTab === "history" && (
          <ObservationGallery timeline={timeline} airbaseId={airbase.id} onDataChanged={loadData} />
        )}

        {activeTab === "intel" && (
          <div className="card">
            <h3>Detected Aircraft — Threat Assessment</h3>
            <AircraftIntel detectionSummary={allDetections} />
          </div>
        )}

        {activeTab === "reports" && (
          <div className="card">
            <ReportsTab airbaseId={airbase.id} airbaseName={airbase.name} />
          </div>
        )}

        {activeTab === "settings" && (
          <div className="card" style={{ maxWidth: "100%" }}>
            <CoordsEditor
              airbase={airbase}
              onUpdated={(updated) => setAirbase(updated)}
            />
          </div>
        )}

        {activeTab === "analytics" && (
          <AnalyticsTab timeline={timeline} />
        )}
      </div>
    </div>
  );
}
