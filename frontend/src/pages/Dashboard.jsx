import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AirbaseMap from "../components/AirbaseMap";
import { fetchAirbases, fetchOverview } from "../utils/api";
import api from "../utils/api";

const COUNTRIES = {
  all: { label: "All", flag: null },
  Russia: { label: "Russia", flag: "\u{1F1F7}\u{1F1FA}" },
  Iran: { label: "Iran", flag: "\u{1F1EE}\u{1F1F7}" },
  NATO: { label: "NATO", flag: "\u{1F310}" },
};

export default function Dashboard() {
  const [airbases, setAirbases] = useState([]);
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [country, setCountry] = useState("all");
  const [expandedCountries, setExpandedCountries] = useState({});
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);
  const navigate = useNavigate();

  function loadAll() {
    return Promise.all([fetchAirbases(), fetchOverview().catch(() => null)])
      .then(([bases, ov]) => {
        setAirbases(bases);
        setOverview(ov);
        // Auto-expand all countries
        const countries = [...new Set(bases.map((b) => b.country))];
        const expanded = {};
        countries.forEach((c) => (expanded[c] = true));
        setExpandedCountries(expanded);
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

  // Filter by search and country
  const filtered = airbases.filter((b) => {
    if (country !== "all" && b.country !== country) return false;
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      b.name.toLowerCase().includes(s) ||
      (b.icao_code && b.icao_code.toLowerCase().includes(s)) ||
      (b.region && b.region.toLowerCase().includes(s))
    );
  });

  // Group by country for sidebar
  const grouped = {};
  filtered.forEach((b) => {
    if (!grouped[b.country]) grouped[b.country] = [];
    grouped[b.country].push(b);
  });

  // Bases to show on map
  const mapBases = country === "all" ? airbases : airbases.filter((b) => b.country === country);

  function toggleCountry(c) {
    setExpandedCountries((prev) => ({ ...prev, [c]: !prev[c] }));
  }

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

      {bulkResult && !bulkResult.error && (
        <div className="bulk-banner">
          Bulk capture complete: {bulkResult.succeeded}/{bulkResult.total} bases captured
          {bulkResult.failed > 0 && ` (${bulkResult.failed} failed)`}
          <button onClick={() => setBulkResult(null)} style={{ marginLeft: 12, background: "none", border: "none", color: "#4fa3e3", cursor: "pointer" }}>Dismiss</button>
        </div>
      )}
      {bulkResult?.error && (
        <div className="bulk-banner" style={{ background: "#2d1215", borderColor: "#5c2024" }}>
          Bulk capture failed: {bulkResult.error}
          <button onClick={() => setBulkResult(null)} style={{ marginLeft: 12, background: "none", border: "none", color: "#e74c3c", cursor: "pointer" }}>Dismiss</button>
        </div>
      )}

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <aside className="sidebar">
          {/* Country filter */}
          <div className="country-filter">
            {Object.entries(COUNTRIES).map(([key, { label, flag }]) => (
              <button
                key={key}
                className={`country-btn ${country === key ? "active" : ""}`}
                onClick={() => setCountry(key)}
              >
                {flag && <span className="country-flag">{flag}</span>}
                {label}
                {key !== "all" && (
                  <span className="country-count">
                    {airbases.filter((b) => b.country === key).length}
                  </span>
                )}
              </button>
            ))}
          </div>

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
            <p style={{ padding: 16, color: "#7a8ba0" }}>Loading...</p>
          ) : (
            <div className="airbase-list-container">
              {Object.entries(grouped).map(([countryName, bases]) => (
                <div key={countryName}>
                  <div
                    className="country-group-header"
                    onClick={() => toggleCountry(countryName)}
                  >
                    <span className="country-flag">
                      {COUNTRIES[countryName]?.flag || ""}
                    </span>
                    <span>{countryName}</span>
                    <span className="country-group-count">{bases.length}</span>
                    <span className="country-chevron">
                      {expandedCountries[countryName] ? "\u25BE" : "\u25B8"}
                    </span>
                  </div>
                  {expandedCountries[countryName] && (
                    <ul className="airbase-list">
                      {bases.map((base) => (
                        <li key={base.id}>
                          <a onClick={() => navigate(`/airbase/${base.id}`)}>
                            <div className="airbase-item-header">
                              <strong>{base.name}</strong>
                              {base.icao_code && <span className="icao">{base.icao_code}</span>}
                              {base.capture_zones?.length > 0 && (
                                <span className="zone-count">{base.capture_zones.length}z</span>
                              )}
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
                </div>
              ))}
            </div>
          )}
        </aside>

        <main style={{ flex: 1 }}>
          {!loading && <AirbaseMap airbases={mapBases} />}
        </main>
      </div>
    </div>
  );
}
