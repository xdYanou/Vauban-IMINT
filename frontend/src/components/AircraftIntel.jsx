import { useEffect, useState } from "react";
import api from "../utils/api";

const TYPE_SILHOUETTES = {
  Su24: "SU-24",
  Su25: "SU-25",
  Su34: "SU-34",
  Su57: "SU-57",
  Mig29: "MIG-29",
  Mig31: "MIG-31",
  Tu95: "TU-95",
  Tu160: "TU-160",
  Tu22M: "TU-22M",
  Il76: "IL-76",
  Ka52: "KA-52",
  Mi8: "MI-8",
  Mi24: "MI-24",
  Mi28: "MI-28",
  An124: "AN-124",
  An22: "AN-22",
  fighter: "FIGHTER",
  bomber: "BOMBER",
  transport: "TRANSPORT",
  tanker: "TANKER",
  surveillance: "ISR",
  rotary: "HELO",
  trainer: "TRAINER",
};

const TYPE_ACCENT = {
  Su24: "#e74c3c", Su25: "#e67e22", Su34: "#e74c3c", Su57: "#9b59b6",
  Mig29: "#3498db", Mig31: "#2d7dd2", Tu95: "#e67e22", Tu160: "#c0392b",
  Tu22M: "#d4780a", Il76: "#27ae60", Ka52: "#1abc9c", Mi8: "#27ae60",
  Mi24: "#e67e22", Mi28: "#e74c3c", An124: "#2d7dd2", An22: "#3498db",
  fighter: "#e74c3c", bomber: "#e67e22", transport: "#27ae60",
};

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
        const accent = TYPE_ACCENT[type] || "#2d7dd2";

        return (
          <div
            key={type}
            className={`aircraft-card ${isExpanded ? "expanded" : ""}`}
            onClick={() => setExpanded(isExpanded ? null : type)}
            style={{ borderColor: isExpanded ? accent : undefined }}
          >
            {/* Header with silhouette */}
            <div className="aircraft-card-header" style={{ background: `linear-gradient(135deg, #0a0e14 0%, ${accent}15 100%)` }}>
              <div className="aircraft-silhouette" style={{ color: `${accent}40` }}>
                {TYPE_SILHOUETTES[type] || type.toUpperCase()}
              </div>
              <div className="aircraft-card-overlay">
                <div className="aircraft-count" style={{ color: accent }}>{count}</div>
                <div className="aircraft-name">{info.name}</div>
                {info.nato_name && <div className="aircraft-nato">NATO: {info.nato_name}</div>}
              </div>
            </div>

            {/* Brief */}
            <div className="aircraft-card-brief">
              <div className="aircraft-role">{info.role}</div>
              <div className="aircraft-tags">
                {info.generation && info.generation !== "Unknown" && (
                  <span className="aircraft-tag" style={{ borderColor: `${accent}33`, color: accent }}>
                    GEN {info.generation}
                  </span>
                )}
                {info.country && info.country !== "Unknown" && (
                  <span className="aircraft-tag">{info.country}</span>
                )}
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
                        <span className="spec-value">{info.specs.max_speed_kmh} <small>km/h</small></span>
                      </div>
                    )}
                    {info.specs.combat_radius_km && (
                      <div className="spec-item">
                        <span className="spec-label">Combat Radius</span>
                        <span className="spec-value">{info.specs.combat_radius_km} <small>km</small></span>
                      </div>
                    )}
                    {info.specs.service_ceiling_m && (
                      <div className="spec-item">
                        <span className="spec-label">Ceiling</span>
                        <span className="spec-value">{(info.specs.service_ceiling_m / 1000).toFixed(1)} <small>km</small></span>
                      </div>
                    )}
                    {info.specs.max_payload_kg && (
                      <div className="spec-item">
                        <span className="spec-label">Payload</span>
                        <span className="spec-value">{(info.specs.max_payload_kg / 1000).toFixed(0)} <small>t</small></span>
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
                        <span className="spec-value">{info.specs.length_m} <small>m</small></span>
                      </div>
                    )}
                  </div>
                )}

                {info.weapons && info.weapons.length > 0 && (
                  <div className="aircraft-weapons">
                    <span className="spec-label">Weapons Systems</span>
                    <ul>
                      {info.weapons.map((w, i) => <li key={i}>{w}</li>)}
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
