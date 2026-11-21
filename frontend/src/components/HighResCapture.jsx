import { useState } from "react";
import api from "../utils/api";
import DetectionOverlay from "./DetectionOverlay";

export default function HighResCapture({ airbaseId, airbase, onObservationCreated }) {
  const [fetching, setFetching] = useState(false);
  const [multiResult, setMultiResult] = useState(null);
  const [singleResult, setSingleResult] = useState(null);
  const [error, setError] = useState(null);

  const zoneCount = airbase?.capture_zones?.length || 0;

  async function handleSingleCapture(source = "esri") {
    setFetching(true);
    setError(null);
    setSingleResult(null);
    try {
      const { data } = await api.post(`/api/tiles/fetch/${airbaseId}?source=${source}`, null, { timeout: 180000 });
      setSingleResult(data);
      onObservationCreated(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to fetch imagery");
    } finally {
      setFetching(false);
    }
  }

  async function handleMultiCapture() {
    setFetching(true);
    setError(null);
    setMultiResult(null);
    setSingleResult(null);
    try {
      const { data } = await api.post(`/api/tiles/fetch-multi/${airbaseId}`, null, { timeout: 600000 });
      setMultiResult(data);
      onObservationCreated(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to fetch imagery");
    } finally {
      setFetching(false);
    }
  }

  return (
    <div>
      <h3>Satellite Capture</h3>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
        color: "#4a5a70", marginBottom: 14,
      }}>
        {zoneCount > 0
          ? `${zoneCount} capture zone${zoneCount > 1 ? "s" : ""} defined`
          : "No zones — will use single default capture. Configure in Settings."
        }
      </div>

      {/* Capture buttons */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
        <button onClick={() => handleSingleCapture("esri")} disabled={fetching} className="capture-btn esri">
          {fetching ? "Capturing..." : "Esri"}
        </button>
        <button onClick={() => handleSingleCapture("google")} disabled={fetching} className="capture-btn google">
          {fetching ? "..." : "Google"}
        </button>
        <button onClick={() => handleSingleCapture("bing")} disabled={fetching} className="capture-btn bing">
          {fetching ? "..." : "Bing"}
        </button>
        <div style={{ width: 1, background: "#1b2535", margin: "0 4px" }} />
        <button onClick={handleMultiCapture} disabled={fetching} className="capture-btn multi">
          {fetching ? "Capturing 3 sources..." : "Multi-Source (3 dates)"}
        </button>
      </div>

      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: "#4a5a70", marginBottom: 14 }}>
        * Each source has different capture dates. Multi-source gives 3 temporal snapshots for change detection.
      </div>

      {error && <p style={{ color: "#c0392b", marginTop: 10, fontSize: 12 }}>{error}</p>}

      {/* Multi-source results */}
      {multiResult && (
        <div style={{ marginTop: 14 }}>
          <div style={{
            padding: 10, background: "#0d1118", borderRadius: "4px 4px 0 0",
            border: "1px solid #1b2535", borderBottom: "none",
            fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
          }}>
            <span style={{ color: "#27ae60" }}>3 temporal captures complete</span>
          </div>
          {multiResult.captures.map((cap, i) => (
            <div key={i} style={{
              padding: 10, background: "#0d1118",
              border: "1px solid #1b2535", borderTop: i > 0 ? "none" : undefined,
              borderRadius: i === multiResult.captures.length - 1 ? "0 0 4px 4px" : 0,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#d0d8e4" }}>
                  {cap.mock_date} — {cap.label}
                </span>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#2d7dd2" }}>
                  {cap.total_aircraft} aircraft
                </span>
              </div>
              {Object.keys(cap.aircraft_types).length > 0 && (
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {Object.entries(cap.aircraft_types).sort((a, b) => b[1] - a[1]).map(([type, count]) => (
                    <span key={type} className={`type-badge type-${type}`}>{type}: {count}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
          <div style={{
            padding: 6, fontFamily: "'JetBrains Mono', monospace",
            fontSize: 9, color: "#4a5a70", textAlign: "center",
          }}>
            * Dates are simulated from different tile sources
          </div>
        </div>
      )}

      {/* Single source results */}
      {singleResult && (
        <div style={{ marginTop: 14 }}>
          <div style={{
            padding: 10, background: "#0d1118", borderRadius: "4px 4px 0 0",
            border: "1px solid #1b2535", borderBottom: "none",
            fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
            display: "flex", gap: 16,
          }}>
            <span style={{ color: "#27ae60" }}>
              {singleResult.zones_captured} zone{singleResult.zones_captured > 1 ? "s" : ""} — {singleResult.source}
            </span>
            <span style={{ color: "#2d7dd2" }}>{singleResult.total_aircraft} aircraft</span>
            <span style={{ color: "#4a5a70" }}>{singleResult.mock_date}*</span>
          </div>
          {(singleResult.zones || []).map((zone, i) => (
            <div key={i}>
              {zone.zone_label && (
                <div style={{
                  padding: "5px 10px", background: "#131a24",
                  fontFamily: "'JetBrains Mono', monospace", fontSize: 9,
                  color: "#7a8ba0", textTransform: "uppercase", letterSpacing: "1px",
                  borderLeft: "1px solid #1b2535", borderRight: "1px solid #1b2535",
                  display: "flex", justifyContent: "space-between",
                }}>
                  <span>{zone.zone_label}</span>
                  <span>z{zone.zoom} {zone.aircraft_count} det</span>
                </div>
              )}
              {zone.image_url && (
                <div style={{
                  borderRadius: i === (singleResult.zones || []).length - 1 ? "0 0 4px 4px" : 0,
                  overflow: "hidden",
                }}>
                  <DetectionOverlay
                    imageUrl={`http://localhost:8000${zone.image_url}`}
                    detections={(zone.detections || []).map((d) => ({
                      aircraft_type: d.type,
                      confidence: d.confidence,
                      bbox: d.bbox,
                    }))}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
