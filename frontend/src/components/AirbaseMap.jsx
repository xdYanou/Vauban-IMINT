import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { useNavigate } from "react-router-dom";
import "leaflet/dist/leaflet.css";

export default function AirbaseMap({ airbases }) {
  const navigate = useNavigate();

  return (
    <MapContainer
      center={[52, 45]}
      zoom={4}
      style={{ height: "100%", width: "100%" }}
      zoomControl={false}
    >
      {/* Dark tactical map tiles */}
      <TileLayer
        attribution='&copy; Stadia Maps'
        url="https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png"
      />
      {airbases.map((base) => (
        <CircleMarker
          key={base.id}
          center={[base.latitude, base.longitude]}
          radius={6}
          pathOptions={{
            color: "#2d7dd2",
            fillColor: "#3d9cf0",
            fillOpacity: 0.7,
            weight: 1.5,
          }}
          eventHandlers={{
            click: () => navigate(`/airbase/${base.id}`),
          }}
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
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>{base.name}</div>
              {base.icao_code && (
                <span style={{
                  fontSize: 10, background: "#1a4878", color: "#3d9cf0",
                  padding: "1px 6px", borderRadius: 2, marginBottom: 6, display: "inline-block"
                }}>{base.icao_code}</span>
              )}
              <div style={{ fontSize: 10, color: "#7a8ba0", marginTop: 4 }}>{base.region}</div>
              <div style={{ fontSize: 9, color: "#4a5a70", marginTop: 2 }}>{base.known_units}</div>
              <button
                onClick={() => navigate(`/airbase/${base.id}`)}
                style={{
                  marginTop: 8,
                  padding: "4px 12px",
                  cursor: "pointer",
                  background: "#2d7dd2",
                  color: "#fff",
                  border: "none",
                  borderRadius: 2,
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10,
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "1px",
                  width: "100%",
                }}
              >
                Intel Report
              </button>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
