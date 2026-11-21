import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AirbaseMap from "../components/AirbaseMap";
import { fetchAirbases, fetchOverview } from "../utils/api";
import api from "../utils/api";

const COUNTRY_FLAGS = {
  Russia: "\u{1F1F7}\u{1F1FA}", USA: "\u{1F1FA}\u{1F1F8}", UK: "\u{1F1EC}\u{1F1E7}",
  France: "\u{1F1EB}\u{1F1F7}", Germany: "\u{1F1E9}\u{1F1EA}", Italy: "\u{1F1EE}\u{1F1F9}",
  Iran: "\u{1F1EE}\u{1F1F7}", NATO: "\u{1F310}", Japan: "\u{1F1EF}\u{1F1F5}",
  "South Korea": "\u{1F1F0}\u{1F1F7}", Norway: "\u{1F1F3}\u{1F1F4}",
  Netherlands: "\u{1F1F3}\u{1F1F1}", Belgium: "\u{1F1E7}\u{1F1EA}",
  Poland: "\u{1F1F5}\u{1F1F1}", Turkey: "\u{1F1F9}\u{1F1F7}",
  "Czech Republic": "\u{1F1E8}\u{1F1FF}", Lithuania: "\u{1F1F1}\u{1F1F9}",
  Estonia: "\u{1F1EA}\u{1F1EA}", Bulgaria: "\u{1F1E7}\u{1F1EC}",
  Romania: "\u{1F1F7}\u{1F1F4}",
  Spain: "\u{1F1EA}\u{1F1F8}",
  Portugal: "\u{1F1F5}\u{1F1F9}",
  Brazil: "\u{1F1E7}\u{1F1F7}",
  India: "\u{1F1EE}\u{1F1F3}",
  Pakistan: "\u{1F1F5}\u{1F1F0}",
  Australia: "\u{1F1E6}\u{1F1FA}",
  Argentina: "\u{1F1E6}\u{1F1F7}",
  Mexico: "\u{1F1F2}\u{1F1FD}",
  Canada: "\u{1F1E8}\u{1F1E6}",
  Djibouti: "\u{1F1E9}\u{1F1EF}",
  Israel: "\u{1F1EE}\u{1F1F1}",
  China: "\u{1F1E8}\u{1F1F3}",
  Taiwan: "\u{1F1F9}\u{1F1FC}",
  Egypt: "\u{1F1EA}\u{1F1EC}",
  Jordan: "\u{1F1EF}\u{1F1F4}",
  UAE: "\u{1F1E6}\u{1F1EA}",
  "Saudi Arabia": "\u{1F1F8}\u{1F1E6}",
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
        // Start collapsed
        if (Object.keys(expandedCountries).length === 0) {
          setExpandedCountries({});
        }
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
          <img src="/logo.png" alt="" className="header-logo" />
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
            <button
              className={`country-btn ${country === "all" ? "active" : ""}`}
              onClick={() => setCountry("all")}
            >
              All
            </button>
            {[...new Set(airbases.map((b) => b.country))].sort().map((c) => (
              <button
                key={c}
                className={`country-btn ${country === c ? "active" : ""}`}
                onClick={() => setCountry(c)}
              >
                {COUNTRY_FLAGS[c] && <span className="country-flag">{COUNTRY_FLAGS[c]}</span>}
                {c}
                <span className="country-count">
                  {airbases.filter((b) => b.country === c).length}
                </span>
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
                      {COUNTRY_FLAGS[countryName] || ""}
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
