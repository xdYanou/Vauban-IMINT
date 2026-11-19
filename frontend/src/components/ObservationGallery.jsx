import { useState } from "react";
import DetectionOverlay from "./DetectionOverlay";

export default function ObservationGallery({ timeline }) {
  const [selected, setSelected] = useState(null);

  if (!timeline.length) {
    return (
      <div className="card" style={{ textAlign: "center", padding: 40 }}>
        <p style={{ color: "#8b949e" }}>No observations yet. Use the Capture tab to fetch imagery.</p>
      </div>
    );
  }

  const obs = selected ? timeline.find((t) => t.id === selected) : null;

  return (
    <div>
      {/* Gallery grid */}
      <div className="gallery-grid">
        {timeline.slice().reverse().map((item) => (
          <div
            key={item.id}
            className={`gallery-item ${selected === item.id ? "selected" : ""}`}
            onClick={() => setSelected(selected === item.id ? null : item.id)}
          >
            <img src={`http://localhost:8000${item.image_url}`} alt={`Observation ${item.id}`} />
            <div className="gallery-item-overlay">
              <div className="gallery-date">
                {new Date(item.date).toLocaleDateString()}
              </div>
              <div className="gallery-meta">
                <span className="gallery-source">{item.source}</span>
                {item.total_aircraft > 0 && (
                  <span className="gallery-count">{item.total_aircraft} aircraft</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Detail view */}
      {obs && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="obs-detail">
            <div className="obs-detail-image">
              <DetectionOverlay
                imageUrl={`http://localhost:8000${obs.image_url}`}
                detections={obs.detections}
              />
            </div>
            <div className="obs-detail-info">
              <h3>Observation #{obs.id}</h3>
              <div className="detail-row">
                <label>Date</label>
                <span>{new Date(obs.date).toLocaleString()}</span>
              </div>
              <div className="detail-row">
                <label>Source</label>
                <span>{obs.source}</span>
              </div>
              <div className="detail-row">
                <label>Aircraft Detected</label>
                <span className="count-highlight">{obs.total_aircraft}</span>
              </div>
              {Object.keys(obs.aircraft_types).length > 0 && (
                <div className="detail-row">
                  <label>Types</label>
                  <div className="type-breakdown">
                    {Object.entries(obs.aircraft_types).map(([type, count]) => (
                      <span key={type} className={`type-badge type-${type}`}>
                        {type}: {count}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {obs.detections.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <label style={{ display: "block", fontSize: 11, color: "#8b949e", marginBottom: 6, textTransform: "uppercase" }}>
                    Detections
                  </label>
                  <table className="obs-table" style={{ fontSize: 12 }}>
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th>Category</th>
                        <th>Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {obs.detections.map((d) => (
                        <tr key={d.id}>
                          <td>{d.aircraft_type}</td>
                          <td>{d.broad_category || "—"}</td>
                          <td>{(d.confidence * 100).toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
