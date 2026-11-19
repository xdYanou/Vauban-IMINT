import { useState } from "react";
import api from "../utils/api";
import DetectionOverlay from "./DetectionOverlay";

export default function HighResCapture({ airbaseId, airbase, onObservationCreated }) {
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const zoneCount = airbase?.capture_zones?.length || 0;

  async function handleFetch() {
    setFetching(true);
    setError(null);
    setResult(null);
    try {
      const { data } = await api.post(`/api/tiles/fetch/${airbaseId}`, null, { timeout: 120000 });
      setResult(data);
      onObservationCreated(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to fetch imagery");
    } finally {
      setFetching(false);
    }
  }

  return (
    <div>
      <h3>High-Resolution Capture</h3>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
        color: "#4a5a70", marginBottom: 14,
      }}>
        {zoneCount > 0
          ? `${zoneCount} capture zone${zoneCount > 1 ? "s" : ""} defined`
          : "No zones — will use single default capture. Configure in Settings."
        }
      </div>

      <button
        onClick={handleFetch}
        disabled={fetching}
        style={{
          padding: "10px 24px",
          background: fetching ? "#1b2535" : "#2d7dd2",
          color: "white", border: "none", borderRadius: 3,
          cursor: fetching ? "wait" : "pointer",
          fontFamily: "'JetBrains Mono', monospace",
          fontWeight: 600, fontSize: 11,
          textTransform: "uppercase", letterSpacing: "1px",
        }}
      >
        {fetching
          ? `Capturing ${zoneCount || 1} zone${(zoneCount || 1) > 1 ? "s" : ""}...`
          : `Capture ${zoneCount || 1} Zone${(zoneCount || 1) > 1 ? "s" : ""}`
        }
      </button>

      {error && <p style={{ color: "#c0392b", marginTop: 10, fontSize: 12 }}>{error}</p>}

      {result && (
        <div style={{ marginTop: 14 }}>
          {/* Summary bar */}
          <div style={{
            padding: 10, background: "#0d1118", borderRadius: "4px 4px 0 0",
            border: "1px solid #1b2535", borderBottom: "none",
            fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
            display: "flex", gap: 16,
          }}>
            <span style={{ color: "#27ae60" }}>
              {result.zones_captured} zone{result.zones_captured > 1 ? "s" : ""} captured
            </span>
            <span style={{ color: "#2d7dd2" }}>
              {result.total_aircraft} aircraft total
            </span>
            {Object.keys(result.aircraft_types || {}).length > 0 && (
              <span style={{ color: "#7a8ba0" }}>
                {Object.entries(result.aircraft_types).map(([t, c]) => `${t}:${c}`).join(" ")}
              </span>
            )}
          </div>

          {/* Zone images */}
          {(result.zones || []).map((zone, i) => (
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
                  borderRadius: i === (result.zones || []).length - 1 ? "0 0 4px 4px" : 0,
                  overflow: "hidden",
                }}>
                  <DetectionOverlay
                    imageUrl={`http://localhost:8000${zone.image_url}`}
                    detections={zone.detections_full || []}
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
