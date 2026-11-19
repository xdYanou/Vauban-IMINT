import { useState } from "react";
import { MapContainer, TileLayer, Marker, Circle, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import api from "../utils/api";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

function ClickHandler({ onMove }) {
  useMapEvents({ click(e) { onMove(e.latlng.lat, e.latlng.lng); } });
  return null;
}

export default function CoordsEditor({ airbase, onUpdated }) {
  const [lat, setLat] = useState(airbase.latitude);
  const [lng, setLng] = useState(airbase.longitude);
  const [radius, setRadius] = useState(airbase.capture_radius_km || 1.5);
  const [zoom, setZoom] = useState(airbase.capture_zoom || 17);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const changed =
    lat !== airbase.latitude ||
    lng !== airbase.longitude ||
    radius !== (airbase.capture_radius_km || 1.5) ||
    zoom !== (airbase.capture_zoom || 17);

  async function handleSave() {
    setSaving(true);
    try {
      const { data } = await api.patch(`/api/airbases/${airbase.id}/settings`, {
        latitude: lat,
        longitude: lng,
        capture_radius_km: radius,
        capture_zoom: zoom,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      onUpdated(data);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h3>Capture Settings</h3>
      <p style={{ fontSize: 11, color: "#4a5a70", marginBottom: 12 }}>
        Click the map to set center point. The circle shows the capture coverage area.
      </p>

      <div style={{ height: 350, borderRadius: 4, overflow: "hidden", marginBottom: 14, border: "1px solid #1b2535" }}>
        <MapContainer center={[lat, lng]} zoom={14} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution="Esri"
            maxZoom={19}
          />
          <Marker position={[lat, lng]} />
          <Circle
            center={[lat, lng]}
            radius={radius * 1000}
            pathOptions={{
              color: "#2d7dd2",
              fillColor: "#2d7dd2",
              fillOpacity: 0.1,
              weight: 1.5,
              dashArray: "6 4",
            }}
          />
          <ClickHandler onMove={(newLat, newLng) => { setLat(newLat); setLng(newLng); }} />
        </MapContainer>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 14 }}>
        <div>
          <label style={labelStyle}>Coordinates</label>
          <span style={valueStyle}>{lat.toFixed(5)}, {lng.toFixed(5)}</span>
        </div>
        <div>
          <label style={labelStyle}>Capture Radius (km)</label>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              type="range"
              min={0.5}
              max={5}
              step={0.25}
              value={radius}
              onChange={(e) => setRadius(parseFloat(e.target.value))}
              style={{ flex: 1 }}
            />
            <span style={valueStyle}>{radius} km</span>
          </div>
        </div>
        <div>
          <label style={labelStyle}>Zoom Level</label>
          <div style={{ display: "flex", gap: 4 }}>
            {[16, 17, 18].map((z) => (
              <button
                key={z}
                onClick={() => setZoom(z)}
                className={zoom === z ? "mode-btn active" : "mode-btn"}
                style={{ padding: "4px 10px", fontSize: 11 }}
              >
                {z} {z === 16 ? "(wide)" : z === 17 ? "(default)" : "(detail)"}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label style={labelStyle}>Coverage</label>
          <span style={{ ...valueStyle, color: "#4a5a70" }}>
            ~{(radius * 2).toFixed(1)}km area, {zoom === 16 ? "~2.4" : zoom === 17 ? "~1.2" : "~0.6"}m/px
          </span>
        </div>
      </div>

      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        {changed && (
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              padding: "7px 18px",
              background: "#1a7f37",
              color: "white",
              border: "none",
              borderRadius: 3,
              cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              fontWeight: 600,
              fontSize: 11,
              textTransform: "uppercase",
              letterSpacing: "0.5px",
            }}
          >
            {saving ? "Saving..." : "Save Settings"}
          </button>
        )}
        {saved && <span style={{ color: "#27ae60", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>Saved</span>}
      </div>
    </div>
  );
}

const labelStyle = {
  display: "block",
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 9,
  textTransform: "uppercase",
  letterSpacing: "1px",
  color: "#4a5a70",
  marginBottom: 4,
};

const valueStyle = {
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 12,
  color: "#d0d8e4",
};
