import { useState, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Rectangle, useMapEvents, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import api from "../utils/api";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

const ZOOM_PRESETS = {
  16: { label: "Wide", gridSize: 4, mpp: "~2.4m/px" },
  17: { label: "Standard", gridSize: 6, mpp: "~1.2m/px" },
  18: { label: "Detail", gridSize: 6, mpp: "~0.6m/px" },
};

// Calculate rectangle bounds from center point, zoom, and grid size
function zoneBounds(lat, lon, zoom, gridSize) {
  const tileSize = 256;
  const mpp = 156543.03 * Math.cos((lat * Math.PI) / 180) / Math.pow(2, zoom);
  const halfM = (gridSize * tileSize * mpp) / 2;
  const dLat = halfM / 111320;
  const dLon = halfM / (111320 * Math.cos((lat * Math.PI) / 180));
  return [
    [lat - dLat, lon - dLon],
    [lat + dLat, lon + dLon],
  ];
}

function AddZoneClick({ onAdd }) {
  useMapEvents({
    click(e) {
      onAdd(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

export default function CoordsEditor({ airbase, onUpdated }) {
  const [zones, setZones] = useState(airbase.capture_zones || []);
  const [addMode, setAddMode] = useState(false);
  const [newZoom, setNewZoom] = useState(17);
  const [saving, setSaving] = useState(false);

  const newGridSize = ZOOM_PRESETS[newZoom]?.gridSize || 6;

  async function handleAddZone(lat, lng) {
    if (!addMode) return;
    setSaving(true);
    try {
      const { data } = await api.post(`/api/airbases/${airbase.id}/zones`, {
        latitude: lat,
        longitude: lng,
        zoom: newZoom,
        grid_size: newGridSize,
        label: `zone-${zones.length + 1}`,
      });
      setZones([...zones, data]);
      setAddMode(false);
      // Refresh parent
      const { data: updated } = await api.get(`/api/airbases/${airbase.id}`);
      onUpdated(updated);
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteZone(zoneId) {
    await api.delete(`/api/airbases/${airbase.id}/zones/${zoneId}`);
    setZones(zones.filter((z) => z.id !== zoneId));
    const { data: updated } = await api.get(`/api/airbases/${airbase.id}`);
    onUpdated(updated);
  }

  const zoneColors = ["#2d7dd2", "#27ae60", "#e67e22", "#9b59b6", "#e74c3c", "#1abc9c"];

  return (
    <div>
      <h3>Capture Zones</h3>
      <p style={{ fontSize: 11, color: "#4a5a70", marginBottom: 12 }}>
        Define rectangular capture areas that cover the full airbase facility.
        Each zone is fetched and analyzed independently, then results are aggregated.
      </p>

      {/* Zone list */}
      <div style={{ marginBottom: 12 }}>
        {zones.length === 0 && (
          <div style={{
            padding: 12, background: "#0d1118", borderRadius: 3, border: "1px solid #1b2535",
            fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#4a5a70",
          }}>
            No zones defined. Click "Add Zone" then click on the map.
            <br />Without zones, capture uses a single default tile at the base center.
          </div>
        )}
        {zones.map((z, i) => (
          <div
            key={z.id}
            style={{
              display: "flex", alignItems: "center", gap: 10,
              padding: "6px 10px", marginBottom: 4,
              background: "#0d1118", borderRadius: 3,
              border: `1px solid ${zoneColors[i % zoneColors.length]}33`,
              borderLeft: `3px solid ${zoneColors[i % zoneColors.length]}`,
            }}
          >
            <span style={{
              fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
              color: zoneColors[i % zoneColors.length], fontWeight: 600,
              textTransform: "uppercase", minWidth: 60,
            }}>
              {z.label || `Zone ${i + 1}`}
            </span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#7a8ba0" }}>
              z{z.zoom} {z.grid_size}x{z.grid_size}
            </span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#4a5a70" }}>
              {z.latitude.toFixed(4)}, {z.longitude.toFixed(4)}
            </span>
            <button
              onClick={() => handleDeleteZone(z.id)}
              style={{
                marginLeft: "auto", background: "none", border: "none",
                color: "#c0392b", cursor: "pointer", fontSize: 14, padding: "0 4px",
              }}
            >
              x
            </button>
          </div>
        ))}
      </div>

      {/* Add zone controls */}
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12 }}>
        {!addMode ? (
          <button
            onClick={() => setAddMode(true)}
            style={{
              padding: "7px 16px", background: "#2d7dd2", color: "white",
              border: "none", borderRadius: 3, cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace", fontWeight: 600,
              fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px",
            }}
          >
            + Add Zone
          </button>
        ) : (
          <>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
              color: "#27ae60", textTransform: "uppercase", letterSpacing: "1px",
            }}>
              Click map to place zone
            </span>
            <div style={{ display: "flex", gap: 4 }}>
              {Object.entries(ZOOM_PRESETS).map(([z, { label }]) => (
                <button
                  key={z}
                  onClick={() => setNewZoom(Number(z))}
                  className={newZoom === Number(z) ? "mode-btn active" : "mode-btn"}
                  style={{ padding: "3px 8px", fontSize: 10 }}
                >
                  Z{z} {label}
                </button>
              ))}
            </div>
            <button
              onClick={() => setAddMode(false)}
              style={{
                padding: "4px 10px", background: "none", border: "1px solid #1b2535",
                color: "#7a8ba0", borderRadius: 3, cursor: "pointer", fontSize: 10,
              }}
            >
              Cancel
            </button>
          </>
        )}
      </div>

      {/* Map */}
      <div style={{
        height: 400, borderRadius: 4, overflow: "hidden",
        border: addMode ? "2px solid #27ae60" : "1px solid #1b2535",
      }}>
        <MapContainer center={[airbase.latitude, airbase.longitude]} zoom={14} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution="Esri"
            maxZoom={19}
          />
          {/* Base center marker */}
          <Marker position={[airbase.latitude, airbase.longitude]} />

          {/* Existing zones as rectangles */}
          {zones.map((z, i) => {
            const bounds = zoneBounds(z.latitude, z.longitude, z.zoom, z.grid_size);
            return (
              <Rectangle
                key={z.id}
                bounds={bounds}
                pathOptions={{
                  color: zoneColors[i % zoneColors.length],
                  fillColor: zoneColors[i % zoneColors.length],
                  fillOpacity: 0.1,
                  weight: 2,
                  dashArray: z.zoom === 18 ? undefined : "6 3",
                }}
              >
                <Popup>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
                    <strong>{z.label}</strong><br />
                    Z{z.zoom} {z.grid_size}x{z.grid_size}<br />
                    {ZOOM_PRESETS[z.zoom]?.mpp}
                  </div>
                </Popup>
              </Rectangle>
            );
          })}

          {/* Click handler for adding zones */}
          {addMode && <AddZoneClick onAdd={handleAddZone} />}
        </MapContainer>
      </div>
    </div>
  );
}
