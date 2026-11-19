import { useState } from "react";
import api from "../utils/api";
import DetectionOverlay from "./DetectionOverlay";

export default function HighResCapture({ airbaseId, airbase, onObservationCreated }) {
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const zoom = airbase?.capture_zoom || 17;
  const radius = airbase?.capture_radius_km || 1.5;

  async function handleFetch() {
    setFetching(true);
    setError(null);
    setResult(null);

    try {
      const { data } = await api.post(
        `/api/tiles/fetch/${airbaseId}`,
        null,
        { params: { zoom, radius_km: radius }, timeout: 120000 }
      );
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
        display: "flex", gap: 12, alignItems: "center", marginBottom: 14,
        fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#4a5a70",
      }}>
        <span>Z{zoom}</span>
        <span>{radius}km radius</span>
        <span>{zoom === 16 ? "~2.4" : zoom === 17 ? "~1.2" : "~0.6"}m/px</span>
        <span style={{ color: "#7a8ba0" }}>Configure in Settings tab</span>
      </div>

      <button
        onClick={handleFetch}
        disabled={fetching}
        style={{
          padding: "10px 24px",
          background: fetching ? "#1b2535" : "#2d7dd2",
          color: "white",
          border: "none",
          borderRadius: 3,
          cursor: fetching ? "wait" : "pointer",
          fontFamily: "'JetBrains Mono', monospace",
          fontWeight: 600,
          fontSize: 11,
          textTransform: "uppercase",
          letterSpacing: "1px",
        }}
      >
        {fetching ? "Capturing..." : "Capture Image"}
      </button>

      {error && <p style={{ color: "#c0392b", marginTop: 10, fontSize: 12 }}>{error}</p>}

      {result && (
        <div style={{ marginTop: 14 }}>
          <div style={{
            padding: 10, background: "#0d1118", borderRadius: "4px 4px 0 0",
            border: "1px solid #1b2535", borderBottom: "none",
            fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
          }}>
            <span style={{ color: "#27ae60" }}>
              {result.zones?.length || 1} zone{(result.zones?.length || 1) > 1 ? "s" : ""} captured
            </span>
            <span style={{ color: "#4a5a70", marginLeft: 12 }}>
              {result.total_aircraft} aircraft detected
            </span>
          </div>
          {(result.zones || [result]).map((zone, i) => (
            <div key={i} style={{ marginBottom: 2 }}>
              {zone.zone && (
                <div style={{
                  padding: "4px 10px", background: "#131a24",
                  fontFamily: "'JetBrains Mono', monospace", fontSize: 9,
                  color: "#4a5a70", textTransform: "uppercase", letterSpacing: "1px",
                  borderLeft: "1px solid #1b2535", borderRight: "1px solid #1b2535",
                }}>
                  Zone: {zone.zone}
                </div>
              )}
              <div style={{ borderRadius: i === (result.zones || [result]).length - 1 ? "0 0 4px 4px" : 0, overflow: "hidden" }}>
                <DetectionOverlay
                  imageUrl={`http://localhost:8000${zone.image_url}`}
                  detections={zone.detections_full || []}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
