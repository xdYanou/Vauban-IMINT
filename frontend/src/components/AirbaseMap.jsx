import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import { useNavigate } from "react-router-dom";
import { useEffect } from "react";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

const COUNTRY_FLAGS = {
  Russia: "\u{1F1F7}\u{1F1FA}",
  Iran: "\u{1F1EE}\u{1F1F7}",
  NATO: "\u{1F310}",
  USA: "\u{1F1FA}\u{1F1F8}",
  UK: "\u{1F1EC}\u{1F1E7}",
  France: "\u{1F1EB}\u{1F1F7}",
  Germany: "\u{1F1E9}\u{1F1EA}",
  Italy: "\u{1F1EE}\u{1F1F9}",
  Japan: "\u{1F1EF}\u{1F1F5}",
  "South Korea": "\u{1F1F0}\u{1F1F7}",
  Norway: "\u{1F1F3}\u{1F1F4}",
  Netherlands: "\u{1F1F3}\u{1F1F1}",
  Belgium: "\u{1F1E7}\u{1F1EA}",
  Poland: "\u{1F1F5}\u{1F1F1}",
  Turkey: "\u{1F1F9}\u{1F1F7}",
  "Czech Republic": "\u{1F1E8}\u{1F1FF}",
  Lithuania: "\u{1F1F1}\u{1F1F9}",
  Estonia: "\u{1F1EA}\u{1F1EA}",
  Bulgaria: "\u{1F1E7}\u{1F1EC}",
  Romania: "\u{1F1F7}\u{1F1F4}",
};

const COUNTRY_COLORS = {
  Russia: "#2d7dd2",
  Iran: "#27ae60",
  NATO: "#e67e22",
  USA: "#3498db",
  UK: "#e74c3c",
  France: "#2d7dd2",
  Germany: "#f1c40f",
  Italy: "#27ae60",
  Japan: "#e74c3c",
  "South Korea": "#3498db",
};

function createFlagIcon(country) {
  const flag = COUNTRY_FLAGS[country] || "\u{1F4CD}";
  const color = COUNTRY_COLORS[country] || "#2d7dd2";
  return L.divIcon({
    className: "",
    html: `<div style="
      font-size: 20px;
      line-height: 1;
      text-align: center;
      filter: drop-shadow(0 1px 3px rgba(0,0,0,0.6));
      cursor: pointer;
    ">${flag}</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -14],
  });
}

function FitBounds({ airbases }) {
  const map = useMap();
  useEffect(() => {
    if (airbases.length === 0) return;
    const bounds = airbases.map((b) => [b.latitude, b.longitude]);
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 8 });
  }, [airbases, map]);
  return null;
}

export default function AirbaseMap({ airbases }) {
  const navigate = useNavigate();

  return (
    <MapContainer
      center={[42, 50]}
      zoom={4}
      style={{ height: "100%", width: "100%" }}
      zoomControl={false}
    >
      <TileLayer
        attribution='&copy; Stadia Maps'
        url="https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png"
      />
      <FitBounds airbases={airbases} />
      {airbases.map((base) => (
        <Marker
          key={base.id}
          position={[base.latitude, base.longitude]}
          icon={createFlagIcon(base.country)}
          eventHandlers={{ click: () => navigate(`/airbase/${base.id}`) }}
        >
          <Popup>
            <div style={{
              fontFamily: "'JetBrains Mono', monospace",
              background: "#0d1118",
              color: "#d0d8e4",
              padding: 10,
              margin: -14,
              borderRadius: 3,
              minWidth: 200,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <span style={{ fontSize: 16 }}>{COUNTRY_FLAGS[base.country] || ""}</span>
                <span style={{ fontSize: 13, fontWeight: 700 }}>{base.name}</span>
              </div>
              {base.icao_code && (
                <span style={{
                  fontSize: 10, background: "#1a4878", color: "#3d9cf0",
                  padding: "1px 6px", borderRadius: 2, display: "inline-block", marginBottom: 4,
                }}>{base.icao_code}</span>
              )}
              <div style={{ fontSize: 10, color: "#7a8ba0", marginTop: 2 }}>{base.region}</div>
              <div style={{ fontSize: 9, color: "#4a5a70", marginTop: 2 }}>{base.known_units}</div>
              <button
                onClick={() => navigate(`/airbase/${base.id}`)}
                style={{
                  marginTop: 8, padding: "4px 12px", cursor: "pointer",
                  background: COUNTRY_COLORS[base.country] || "#2d7dd2",
                  color: "#fff", border: "none", borderRadius: 2,
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10, fontWeight: 600, textTransform: "uppercase",
                  letterSpacing: "1px", width: "100%",
                }}
              >
                Intel Report
              </button>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
