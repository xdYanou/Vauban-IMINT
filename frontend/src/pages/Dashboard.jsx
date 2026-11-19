import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AirbaseMap from "../components/AirbaseMap";
import { fetchAirbases, fetchOverview } from "../utils/api";
import api from "../utils/api";

export default function Dashboard() {
  const [airbases, setAirbases] = useState([]);
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);
  const navigate = useNavigate();

  function loadAll() {
    return Promise.all([fetchAirbases(), fetchOverview().catch(() => null)])
      .then(([bases, ov]) => {
        setAirbases(bases);
        setOverview(ov);
      });
  }

  useEffect(() => {
    loadAll().finally(() => setLoading(false));
  }, []);

  async function handleBulkCapture() {
    setBulkRunning(true);
    setBulkResult(null);
    try {
      const { data } = await api.post("/api/bulk/capture?zoom=17&grid_size=6", null, {
        timeout: 600000,
      });
      setBulkResult(data);
      loadAll();
    } catch (err) {
      setBulkResult({ error: err.message });
    } finally {
      setBulkRunning(false);
    }
  }

  const filtered = airbases.filter(
    (b) =>
      b.name.toLowerCase().includes(search.toLowerCase()) ||
      (b.icao_code && b.icao_code.toLowerCase().includes(search.toLowerCase())) ||
      (b.region && b.region.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <header className="app-header">
        <div className="header-brand">
          <h1>VAUBAN</h1>
          <span className="header-sub">IMINT Platform</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          {overview && (
            <div className="header-stats">
              <div className="stat">
                <span className="stat-value">{overview.total_airbases}</span>
                <span className="stat-label">Airbases</span>
              </div>
              <div className="stat">
                <span className="stat-value">{overview.total_observations}</span>
                <span className="stat-label">Observations</span>
              </div>
              <div className="stat">
                <span className="stat-value">{overview.total_detections}</span>
                <span className="stat-label">Detections</span>
              </div>
            </div>
          )}
          <button
            onClick={handleBulkCapture}
            disabled={bulkRunning}
            className="bulk-btn"
          >
            {bulkRunning ? "Capturing all bases..." : "Bulk Capture All"}
          </button>
        </div>
      </header>

      {/* Bulk result banner */}
      {bulkResult && !bulkResult.error && (
        <div className="bulk-banner">
          Bulk capture complete: {bulkResult.succeeded}/{bulkResult.total} bases captured
          {bulkResult.failed > 0 && ` (${bulkResult.failed} failed)`}
          <button onClick={() => setBulkResult(null)} style={{ marginLeft: 12, background: "none", border: "none", color: "#4fa3e3", cursor: "pointer" }}>
            Dismiss
          </button>
        </div>
      )}
      {bulkResult?.error && (
        <div className="bulk-banner" style={{ background: "#2d1215", borderColor: "#5c2024" }}>
          Bulk capture failed: {bulkResult.error}
          <button onClick={() => setBulkResult(null)} style={{ marginLeft: 12, background: "none", border: "none", color: "#e74c3c", cursor: "pointer" }}>
            Dismiss
          </button>
        </div>
      )}

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <aside className="sidebar">
          <div className="sidebar-search">
            <input
              type="text"
              placeholder="Search airbases..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="sidebar-count">{filtered.length} airbases</div>
          {loading ? (
            <p style={{ padding: 16, color: "#8b949e" }}>Loading...</p>
          ) : (
            <ul className="airbase-list">
              {filtered.map((base) => (
                <li key={base.id}>
                  <a onClick={() => navigate(`/airbase/${base.id}`)}>
                    <div className="airbase-item-header">
                      <strong>{base.name}</strong>
                      {base.icao_code && <span className="icao">{base.icao_code}</span>}
                    </div>
                    <div className="airbase-item-meta">
                      {base.region} — {base.military_district}
                    </div>
                    <div className="airbase-item-units">{base.known_units}</div>
                  </a>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <main style={{ flex: 1 }}>
          {!loading && <AirbaseMap airbases={airbases} />}
        </main>
      </div>
    </div>
  );
}
