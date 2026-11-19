import { useState } from "react";
import DetectionOverlay from "./DetectionOverlay";

export default function ObservationGallery({ timeline }) {
  const [selected, setSelected] = useState(null);

  if (!timeline.length) {
    return (
      <div className="card" style={{ textAlign: "center", padding: 40 }}>
        <p style={{ color: "#4a5a70", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
          No captures yet. Use the Capture tab to fetch imagery.
        </p>
      </div>
    );
  }

  const capture = selected !== null ? timeline[selected] : null;

  return (
    <div>
      {/* Capture cards */}
      <div className="gallery-grid">
        {timeline.slice().reverse().map((item, reverseIdx) => {
          const idx = timeline.length - 1 - reverseIdx;
          const firstImage = item.images?.[0]?.image_url;
          return (
            <div
              key={idx}
              className={`gallery-item ${selected === idx ? "selected" : ""}`}
              onClick={() => setSelected(selected === idx ? null : idx)}
            >
              {firstImage ? (
                <img src={`http://localhost:8000${firstImage}`} alt={`Capture ${idx}`} />
              ) : (
                <div style={{ width: "100%", height: "100%", background: "#131a24", display: "flex", alignItems: "center", justifyContent: "center", color: "#4a5a70", fontSize: 11 }}>
                  No image
                </div>
              )}
              <div className="gallery-item-overlay">
                <div className="gallery-date">
                  {new Date(item.date).toLocaleDateString()}
                </div>
                <div className="gallery-meta">
                  <span className="gallery-source">{item.source}</span>
                  <span className="gallery-source">{item.zones}z</span>
                  {item.total_aircraft > 0 && (
                    <span className="gallery-count">{item.total_aircraft} aircraft</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Capture detail */}
      {capture && (
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <h3 style={{ margin: 0 }}>Capture — {new Date(capture.date).toLocaleString()}</h3>
            <div style={{ display: "flex", gap: 12, fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
              <span style={{ color: "#7a8ba0" }}>{capture.zones} zones</span>
              <span style={{ color: "#2d7dd2" }}>{capture.total_aircraft} aircraft</span>
              <span style={{ color: "#4a5a70" }}>{capture.source}</span>
            </div>
          </div>

          {/* Type summary */}
          {Object.keys(capture.aircraft_types || {}).length > 0 && (
            <div style={{ display: "flex", gap: 5, marginBottom: 14, flexWrap: "wrap" }}>
              {Object.entries(capture.aircraft_types).map(([type, count]) => (
                <span key={type} className={`type-badge type-${type}`}>
                  {type}: {count}
                </span>
              ))}
            </div>
          )}

          {/* Zone images with detections */}
          <div style={{ display: "grid", gridTemplateColumns: capture.images.length > 1 ? "repeat(auto-fit, minmax(400px, 1fr))" : "1fr", gap: 10 }}>
            {capture.images.map((img, i) => (
              <div key={i}>
                {img.zone_label && (
                  <div style={{
                    padding: "4px 10px", background: "#131a24",
                    fontFamily: "'JetBrains Mono', monospace", fontSize: 9,
                    color: "#7a8ba0", textTransform: "uppercase", letterSpacing: "1px",
                    borderRadius: "4px 4px 0 0", border: "1px solid #1b2535", borderBottom: "none",
                  }}>
                    {img.zone_label}
                  </div>
                )}
                <div style={{ borderRadius: img.zone_label ? "0 0 4px 4px" : "4px", overflow: "hidden" }}>
                  <DetectionOverlay
                    imageUrl={`http://localhost:8000${img.image_url}`}
                    detections={(img.detections || []).map((d) => ({
                      aircraft_type: d.aircraft_type,
                      confidence: d.confidence,
                      bbox: d.bbox,
                    }))}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
