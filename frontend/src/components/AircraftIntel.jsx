import { useEffect, useState } from "react";
import api from "../utils/api";

export default function AircraftIntel({ detectionSummary }) {
  const [specs, setSpecs] = useState({});
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    api.get("/api/aircraft/specs").then(({ data }) => setSpecs(data)).catch(() => {});
  }, []);

  if (!detectionSummary || Object.keys(detectionSummary).length === 0) {
    return (
      <div style={{ color: "#4a5a70", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
        No aircraft detected yet. Run a capture to populate this section.
      </div>
    );
  }

  const sorted = Object.entries(detectionSummary).sort((a, b) => b[1] - a[1]);

  return (
    <div className="aircraft-intel-grid">
      {sorted.map(([type, count]) => {
        const info = specs[type] || { name: type, description: "Unknown aircraft type." };
        const isExpanded = expanded === type;

        return (
          <div
            key={type}
            className={`aircraft-card ${isExpanded ? "expanded" : ""}`}
            onClick={() => setExpanded(isExpanded ? null : type)}
          >
            {/* Header with image */}
            <div className="aircraft-card-header">
              {info.image_url ? (
                <img src={info.image_url} alt={info.name} className="aircraft-img" />
              ) : (
                <div className="aircraft-img-placeholder">
                  <span>{type}</span>
                </div>
              )}
              <div className="aircraft-card-overlay">
                <div className="aircraft-count">{count}</div>
                <div className="aircraft-name">{info.name}</div>
                {info.nato_name && <div className="aircraft-nato">NATO: {info.nato_name}</div>}
              </div>
            </div>

            {/* Brief info always visible */}
            <div className="aircraft-card-brief">
              <div className="aircraft-role">{info.role}</div>
              <div className="aircraft-tags">
                {info.generation && <span className="aircraft-tag">GEN {info.generation}</span>}
                {info.country && <span className="aircraft-tag">{info.country}</span>}
              </div>
            </div>

            {/* Expanded detail */}
            {isExpanded && info.specs && (
              <div className="aircraft-card-detail">
                <p className="aircraft-desc">{info.description}</p>

                {Object.keys(info.specs).length > 0 && (
                  <div className="aircraft-specs-grid">
                    {info.specs.max_speed_kmh && (
                      <div className="spec-item">
                        <span className="spec-label">Max Speed</span>
                        <span className="spec-value">{info.specs.max_speed_kmh} km/h</span>
                      </div>
                    )}
                    {info.specs.combat_radius_km && (
                      <div className="spec-item">
                        <span className="spec-label">Combat Radius</span>
                        <span className="spec-value">{info.specs.combat_radius_km} km</span>
                      </div>
                    )}
                    {info.specs.service_ceiling_m && (
                      <div className="spec-item">
                        <span className="spec-label">Ceiling</span>
                        <span className="spec-value">{(info.specs.service_ceiling_m / 1000).toFixed(1)}km</span>
                      </div>
                    )}
                    {info.specs.max_payload_kg && (
                      <div className="spec-item">
                        <span className="spec-label">Payload</span>
                        <span className="spec-value">{(info.specs.max_payload_kg / 1000).toFixed(0)}t</span>
                      </div>
                    )}
                    {info.specs.crew && (
                      <div className="spec-item">
                        <span className="spec-label">Crew</span>
                        <span className="spec-value">{info.specs.crew}</span>
                      </div>
                    )}
                    {info.specs.length_m && (
                      <div className="spec-item">
                        <span className="spec-label">Length</span>
                        <span className="spec-value">{info.specs.length_m}m</span>
                      </div>
                    )}
                  </div>
                )}

                {info.weapons && info.weapons.length > 0 && (
                  <div className="aircraft-weapons">
                    <span className="spec-label">Weapons Systems</span>
                    <ul>
                      {info.weapons.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
