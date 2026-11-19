import { useState } from "react";
import api from "../utils/api";
import DetectionOverlay from "./DetectionOverlay";

export default function SentinelSearch({ airbaseId, onObservationCreated }) {
  const [mode, setMode] = useState("latest"); // "latest" or "month"
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function handleFetch() {
    setFetching(true);
    setError(null);
    setResult(null);

    let dateFrom, dateTo;
    if (mode === "latest") {
      // Last 30 days
      const to = new Date();
      const from = new Date();
      from.setDate(from.getDate() - 30);
      dateFrom = from.toISOString().slice(0, 10);
      dateTo = to.toISOString().slice(0, 10);
    } else {
      // Specific month
      dateFrom = `${year}-${String(month).padStart(2, "0")}-01`;
      const lastDay = new Date(year, month, 0).getDate();
      dateTo = `${year}-${String(month).padStart(2, "0")}-${lastDay}`;
    }

    try {
      const { data } = await api.post(
        `/api/sentinel/fetch/${airbaseId}`,
        null,
        { params: { date_from: dateFrom, date_to: dateTo } }
      );
      setResult(data);
      onObservationCreated(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Fetch failed — no imagery available for this period.");
    } finally {
      setFetching(false);
    }
  }

  const months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];

  return (
    <div>
      <h3>Sentinel-2 Imagery</h3>
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button
          onClick={() => setMode("latest")}
          className={mode === "latest" ? "mode-btn active" : "mode-btn"}
        >
          Latest (30 days)
        </button>
        <button
          onClick={() => setMode("month")}
          className={mode === "month" ? "mode-btn active" : "mode-btn"}
        >
          By Month
        </button>
      </div>

      {mode === "month" && (
        <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            style={{ padding: "6px 10px", background: "#0d1117", color: "#e0e0e0", border: "1px solid #30363d", borderRadius: 4 }}
          >
            {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i).map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            {months.map((m, i) => (
              <button
                key={i}
                onClick={() => setMonth(i + 1)}
                className={month === i + 1 ? "month-btn active" : "month-btn"}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={handleFetch}
        disabled={fetching}
        style={{
          padding: "10px 24px",
          background: fetching ? "#333" : "#238636",
          color: "white",
          border: "none",
          borderRadius: 6,
          cursor: fetching ? "wait" : "pointer",
          fontWeight: 600,
          fontSize: 14,
        }}
      >
        {fetching
          ? "Fetching Satellite Image..."
          : mode === "latest"
            ? "Fetch Latest Imagery"
            : `Fetch ${months[month - 1]} ${year} Imagery`}
      </button>

      {error && <p style={{ color: "#e74c3c", marginTop: 12 }}>{error}</p>}

      {result && (
        <div style={{ marginTop: 16 }}>
          <div style={{ padding: 12, background: "#21262d", borderRadius: "6px 6px 0 0" }}>
            <p style={{ color: "#2ecc71", marginBottom: 4 }}>
              Image fetched — {result.aircraft_count} aircraft detected
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
                detections={(result.detections || []).map((d) => ({
                  aircraft_type: d.type,
                  confidence: d.confidence,
                  bbox: d.bbox,
                }))}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
