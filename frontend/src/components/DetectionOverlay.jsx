import { useState } from "react";

const TYPE_COLORS = {
  fighter: "#e74c3c",
  bomber: "#e67e22",
  attack: "#f1c40f",
  transport: "#2ecc71",
  tanker: "#3498db",
  surveillance: "#9b59b6",
  rotary: "#1abc9c",
  helicopter: "#1abc9c",
  trainer: "#95a5a6",
  unknown: "#7a8ba0",
};

export default function DetectionOverlay({ imageUrl, detections = [], width = "100%" }) {
  const [showBoxes, setShowBoxes] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [imgDims, setImgDims] = useState({ w: 0, h: 0, natW: 0, natH: 0 });
  const [hovered, setHovered] = useState(null);

  function handleImgLoad(e) {
    const img = e.target;
    setImgDims({
      w: img.clientWidth,
      h: img.clientHeight,
      natW: img.naturalWidth,
      natH: img.naturalHeight,
    });
  }

  // Convert bbox from pixel coords (cx, cy, w, h) to percentage positions
  function bboxToStyle(det) {
    if (!imgDims.natW) return null;
    const scaleX = imgDims.w / imgDims.natW;
    const scaleY = imgDims.h / imgDims.natH;

    const x = (det.bbox[0] - det.bbox[2] / 2) * scaleX;
    const y = (det.bbox[1] - det.bbox[3] / 2) * scaleY;
    const w = det.bbox[2] * scaleX;
    const h = det.bbox[3] * scaleY;

    return { left: x, top: y, width: w, height: h };
  }

  const color = (det) => TYPE_COLORS[det.aircraft_type] || TYPE_COLORS[det.broad_category] || "#7a8ba0";

  return (
    <div>
      {/* Controls */}
      {detections.length > 0 && (
        <div style={{
          display: "flex", gap: 12, marginBottom: 8, alignItems: "center",
          fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
        }}>
          <label style={{ display: "flex", alignItems: "center", gap: 4, cursor: "pointer", color: "#7a8ba0" }}>
            <input type="checkbox" checked={showBoxes} onChange={() => setShowBoxes(!showBoxes)} />
            BOXES
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 4, cursor: "pointer", color: "#7a8ba0" }}>
            <input type="checkbox" checked={showLabels} onChange={() => setShowLabels(!showLabels)} />
            LABELS
          </label>
          <span style={{ color: "#4a5a70" }}>
            {detections.length} DETECTION{detections.length !== 1 ? "S" : ""}
          </span>
        </div>
      )}

      {/* Image with overlay */}
      <div style={{ position: "relative", display: "inline-block", width, background: "#000", borderRadius: 4, overflow: "hidden" }}>
        <img
          src={imageUrl}
          alt="Satellite observation"
          onLoad={handleImgLoad}
          style={{ width: "100%", display: "block" }}
        />

        {/* Detection boxes */}
        {showBoxes && detections.map((det, i) => {
          const style = bboxToStyle(det);
          if (!style) return null;
          const c = color(det);
          const isHovered = hovered === i;

          return (
            <div key={det.id || i}>
              {/* Bounding box */}
              <div
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
                style={{
                  position: "absolute",
                  left: style.left,
                  top: style.top,
                  width: style.width,
                  height: style.height,
                  border: `2px solid ${c}`,
                  background: isHovered ? `${c}22` : "transparent",
                  cursor: "pointer",
                  transition: "background 0.1s",
                  zIndex: isHovered ? 10 : 1,
                }}
              />

              {/* Label */}
              {showLabels && (
                <div style={{
                  position: "absolute",
                  left: style.left,
                  top: style.top - 18,
                  background: c,
                  color: "#fff",
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 9,
                  fontWeight: 700,
                  padding: "1px 5px",
                  borderRadius: "2px 2px 0 0",
                  whiteSpace: "nowrap",
                  letterSpacing: "0.5px",
                  textTransform: "uppercase",
                  zIndex: isHovered ? 11 : 2,
                  opacity: isHovered ? 1 : 0.85,
                }}>
                  {det.aircraft_type}
                  {det.confidence && ` ${(det.confidence * 100).toFixed(0)}%`}
                </div>
              )}

              {/* Hover tooltip */}
              {isHovered && (
                <div style={{
                  position: "absolute",
                  left: style.left + style.width + 6,
                  top: style.top,
                  background: "#0d1118ee",
                  border: `1px solid ${c}44`,
                  borderRadius: 3,
                  padding: "6px 10px",
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10,
                  color: "#d0d8e4",
                  whiteSpace: "nowrap",
                  zIndex: 20,
                  pointerEvents: "none",
                }}>
                  <div style={{ fontWeight: 700, color: c, marginBottom: 3, textTransform: "uppercase" }}>
                    {det.aircraft_type}
                  </div>
                  {det.broad_category && det.broad_category !== det.aircraft_type && (
                    <div style={{ color: "#7a8ba0" }}>Category: {det.broad_category}</div>
                  )}
                  <div style={{ color: "#7a8ba0" }}>
                    Detect: {(det.confidence * 100).toFixed(1)}%
                  </div>
                  {det.classification_conf && (
                    <div style={{ color: "#7a8ba0" }}>
                      Classify: {(det.classification_conf * 100).toFixed(1)}%
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {/* Crosshair overlay when no detections */}
        {detections.length === 0 && imgDims.w > 0 && (
          <div style={{
            position: "absolute", top: 8, left: 8,
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 9, color: "#4a5a70",
            textTransform: "uppercase", letterSpacing: "1px",
          }}>
            No detections
          </div>
        )}
      </div>
    </div>
  );
}
