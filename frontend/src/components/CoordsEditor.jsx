import { useState } from "react";
import { MapContainer, TileLayer, Marker, useMapEvents } from "react-leaflet";
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
  useMapEvents({
    click(e) {
      onMove(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

export default function CoordsEditor({ airbase, onUpdated }) {
  const [lat, setLat] = useState(airbase.latitude);
  const [lng, setLng] = useState(airbase.longitude);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const changed = lat !== airbase.latitude || lng !== airbase.longitude;

  async function handleSave() {
    setSaving(true);
    try {
      await api.patch(`/api/airbases/${airbase.id}/coords`, {
        latitude: lat,
        longitude: lng,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      onUpdated({ ...airbase, latitude: lat, longitude: lng });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h3>Adjust Coordinates</h3>
      <p style={{ fontSize: 12, color: "#4a5567", marginBottom: 10 }}>
        Click on the satellite map to move the target point to the aircraft parking area.
      </p>
      <div style={{ height: 350, borderRadius: 6, overflow: "hidden", marginBottom: 12, border: "1px solid #1e2733" }}>
        <MapContainer
          center={[lat, lng]}
          zoom={15}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution="Esri"
            maxZoom={19}
          />
          <Marker position={[lat, lng]} />
          <ClickHandler onMove={(newLat, newLng) => { setLat(newLat); setLng(newLng); }} />
        </MapContainer>
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 13, color: "#c8d1db" }}>
          {lat.toFixed(5)}, {lng.toFixed(5)}
        </span>
        {changed && (
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              padding: "6px 16px",
              background: "#1a7f37",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontWeight: 600,
              fontSize: 12,
            }}
          >
            {saving ? "Saving..." : "Save New Coordinates"}
          </button>
        )}
        {saved && <span style={{ color: "#2ecc71", fontSize: 12 }}>Saved</span>}
      </div>
    </div>
  );
}
