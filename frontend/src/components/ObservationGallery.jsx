import { useState } from "react";
import DetectionOverlay from "./DetectionOverlay";
import api from "../utils/api";

export default function ObservationGallery({ timeline, airbaseId, onDataChanged }) {
  const [selected, setSelected] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [selectMode, setSelectMode] = useState(false);
  const [checked, setChecked] = useState(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  if (!timeline.length) {
    return (
      <div className="card" style={{ textAlign: "center", padding: 40 }}>
        <p style={{ color: "#4a5a70", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
          No captures yet. Use the Capture tab to fetch imagery.
        </p>
      </div>
    );
  }

  async function handleDelete(captureDate, idx) {
    if (!confirm("Delete this entire capture and all its detections?")) return;
    setDeleting(idx);
    try {
      await api.delete(`/api/observations/capture/${airbaseId}/${captureDate}`);
      if (selected === idx) setSelected(null);
      onDataChanged();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to delete");
    } finally {
      setDeleting(null);
    }
  }

  function toggleCheck(idx) {
    const next = new Set(checked);
    if (next.has(idx)) next.delete(idx);
    else next.add(idx);
    setChecked(next);
  }

  function selectAll() {
    if (checked.size === timeline.length) setChecked(new Set());
    else setChecked(new Set(timeline.map((_, i) => i)));
  }

  async function handleBulkDelete() {
    if (!confirm(`Delete ${checked.size} capture(s) and all their detections?`)) return;
    setBulkDeleting(true);
    for (const idx of checked) {
      try {
        await api.delete(`/api/observations/capture/${airbaseId}/${timeline[idx].date}`);
      } catch {}
    }
    setChecked(new Set());
    setSelectMode(false);
    setSelected(null);
    setBulkDeleting(false);
    onDataChanged();
  }

  const capture = selected !== null ? timeline[selected] : null;

  return (
    <div>
      {/* Toolbar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#4a5a70" }}>
          {timeline.length} capture{timeline.length !== 1 ? "s" : ""}
          {selectMode && checked.size > 0 && ` — ${checked.size} selected`}
        </span>
        <div style={{ display: "flex", gap: 6 }}>
          {!selectMode ? (
            <button onClick={() => { setSelectMode(true); setChecked(new Set()); }} className="gallery-toolbar-btn">
              Select
            </button>
          ) : (
            <>
              <button onClick={selectAll} className="gallery-toolbar-btn">
                {checked.size === timeline.length ? "Deselect All" : "Select All"}
              </button>
              <button
                onClick={handleBulkDelete}
                disabled={checked.size === 0 || bulkDeleting}
                className="gallery-toolbar-btn delete"
              >
                {bulkDeleting ? "Deleting..." : `Delete (${checked.size})`}
              </button>
              <button onClick={() => { setSelectMode(false); setChecked(new Set()); }} className="gallery-toolbar-btn">
                Cancel
              </button>
            </>
          )}
        </div>
      </div>

      {/* Capture cards */}
      <div className="gallery-grid">
        {timeline.slice().reverse().map((item, reverseIdx) => {
          const idx = timeline.length - 1 - reverseIdx;
          const firstImage = item.images?.[0]?.image_url;
          return (
            <div
              key={idx}
              className={`gallery-item ${selected === idx ? "selected" : ""} ${checked.has(idx) ? "checked" : ""}`}
            >
              {selectMode && (
                <div
                  className="gallery-checkbox"
                  onClick={(e) => { e.stopPropagation(); toggleCheck(idx); }}
                >
                  {checked.has(idx) ? "✓" : ""}
                </div>
              )}
              <div onClick={() => selectMode ? toggleCheck(idx) : setSelected(selected === idx ? null : idx)} style={{ width: "100%", height: "100%" }}>
                {firstImage ? (
                  <img src={`http://localhost:8000${firstImage}`} alt={`Capture ${idx}`} />
                ) : (
                  <div style={{ width: "100%", height: "100%", background: "#131a24", display: "flex", alignItems: "center", justifyContent: "center", color: "#4a5a70", fontSize: 11 }}>
                    No image
                  </div>
                )}
              </div>
              <div className="gallery-item-overlay">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div className="gallery-date">{new Date(item.date).toLocaleDateString()}</div>
                    <div className="gallery-meta">
                      <span className="gallery-source">{item.source}</span>
                      <span className="gallery-source">{item.zones}z</span>
                      {item.total_aircraft > 0 && (
                        <span className="gallery-count">{item.total_aircraft} aircraft</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(item.date, idx); }}
                    disabled={deleting === idx}
                    className="gallery-delete-btn"
                  >
                    {deleting === idx ? "..." : "x"}
                  </button>
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
            <div style={{ display: "flex", gap: 12, alignItems: "center", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
              <span style={{ color: "#7a8ba0" }}>{capture.zones} zones</span>
              <span style={{ color: "#2d7dd2" }}>{capture.total_aircraft} aircraft</span>
              <span style={{ color: "#4a5a70" }}>{capture.source}</span>
              <button
                onClick={() => handleDelete(capture.date, selected)}
                disabled={deleting === selected}
                style={{
                  padding: "4px 12px", background: "rgba(192,57,43,0.15)",
                  color: "#c0392b", border: "1px solid rgba(192,57,43,0.3)",
                  borderRadius: 3, cursor: "pointer", fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10, fontWeight: 600, textTransform: "uppercase",
                }}
              >
                Delete Capture
              </button>
            </div>
          </div>

          {Object.keys(capture.aircraft_types || {}).length > 0 && (
            <div style={{ display: "flex", gap: 5, marginBottom: 14, flexWrap: "wrap" }}>
              {Object.entries(capture.aircraft_types).map(([type, count]) => (
                <span key={type} className={`type-badge type-${type}`}>{type}: {count}</span>
              ))}
            </div>
          )}

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
