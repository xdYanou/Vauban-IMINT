import { useState } from "react";
import api from "../utils/api";
import DetectionOverlay from "./DetectionOverlay";

export default function HighResCapture({ airbaseId, onObservationCreated }) {
  const [zoom, setZoom] = useState(17);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function handleFetch() {
    setFetching(true);
    setError(null);
    setResult(null);

    try {
      const { data } = await api.post(
        `/api/tiles/fetch/${airbaseId}`,
        null,
        { params: { zoom, grid_size: zoom >= 18 ? 6 : 8 } }
      );
      setResult(data);
      onObservationCreated(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to fetch imagery");
    } finally {
      setFetching(false);
    }
  }

  const zoomInfo = {
    16: "~2.4 m/px — wide area overview",
    17: "~1.2 m/px — aircraft visible",
    18: "~0.6 m/px — aircraft detail",
  };

  return (
    <div>
      <h3>High-Resolution Imagery</h3>
      <p style={{ fontSize: 13, color: "#8b949e", marginBottom: 12 }}>
        Fetches satellite tiles at high zoom. Best for aircraft detection.
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {[16, 17, 18].map((z) => (
          <button
            key={z}
            onClick={() => setZoom(z)}
            className={zoom === z ? "mode-btn active" : "mode-btn"}
            style={{ flexDirection: "column", padding: "8px 16px" }}
          >
            <div>Zoom {z}</div>
            <div style={{ fontSize: 11, opacity: 0.7 }}>{zoomInfo[z]}</div>
          </button>
        ))}
      </div>

      <button
        onClick={handleFetch}
        disabled={fetching}
        style={{
          padding: "10px 24px",
          background: fetching ? "#333" : "#1a6dd4",
          color: "white",
          border: "none",
          borderRadius: 6,
          cursor: fetching ? "wait" : "pointer",
          fontWeight: 600,
          fontSize: 14,
        }}
      >
        {fetching ? "Fetching High-Res Image..." : `Capture at Zoom ${zoom}`}
      </button>

      {error && <p style={{ color: "#e74c3c", marginTop: 12 }}>{error}</p>}

      {result && (
        <div style={{ marginTop: 16 }}>
          <div style={{ padding: 12, background: "#21262d", borderRadius: "6px 6px 0 0" }}>
            <p style={{ color: "#2ecc71", marginBottom: 4 }}>
              Captured at zoom {result.zoom} — {result.aircraft_count} aircraft detected
            </p>
            {result.aircraft_count > 0 && (
              <p style={{ fontSize: 13, color: "#8b949e" }}>
                {result.detections.map((d) => `${d.type} (${(d.confidence * 100).toFixed(0)}%)`).join(", ")}
              </p>
            )}
          </div>
          {result.image_url && (
            <div style={{ borderRadius: "0 0 4px 4px", overflow: "hidden" }}>
              <DetectionOverlay
                imageUrl={`http://localhost:8000${result.image_url}`}
                detections={result.detections_full || []}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
