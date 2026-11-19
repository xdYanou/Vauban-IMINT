import { useState, useCallback } from "react";
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

function zoneBounds(lat, lon, zoom, gridSize) {
  const mpp = 156543.03 * Math.cos((lat * Math.PI) / 180) / Math.pow(2, zoom);
  const halfM = (gridSize * 256 * mpp) / 2;
  const dLat = halfM / 111320;
  const dLon = halfM / (111320 * Math.cos((lat * Math.PI) / 180));
  return [[lat - dLat, lon - dLon], [lat + dLat, lon + dLon]];
}

function ClickHandler({ onAdd }) {
  useMapEvents({ click(e) { onAdd(e.latlng.lat, e.latlng.lng); } });
  return null;
}

// Draggable zone rectangle — uses a draggable center marker to move the rectangle
function DraggableZone({ zone, color, onMove, onDelete, isDraft }) {
  const [pos, setPos] = useState([zone.latitude, zone.longitude]);
  const bounds = zoneBounds(pos[0], pos[1], zone.zoom, zone.grid_size);

  const markerIcon = L.divIcon({
    className: "",
    html: `<div style="
      width: 12px; height: 12px; border-radius: 50%;
      background: ${color}; border: 2px solid white;
      box-shadow: 0 0 6px rgba(0,0,0,0.5);
      cursor: grab;
    "></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });

  const handleDrag = useCallback((e) => {
    const { lat, lng } = e.target.getLatLng();
    setPos([lat, lng]);
    onMove(lat, lng);
  }, [onMove]);

  return (
    <>
      <Rectangle
        bounds={bounds}
        pathOptions={{
          color,
          fillColor: color,
          fillOpacity: isDraft ? 0.15 : 0.08,
          weight: isDraft ? 2.5 : 1.5,
          dashArray: isDraft ? undefined : "6 3",
        }}
      />
      <Marker
        position={pos}
        icon={markerIcon}
        draggable={true}
        eventHandlers={{ dragend: handleDrag }}
      >
        <Popup>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
            background: "#0d1118", color: "#d0d8e4", padding: 8, margin: -14,
            borderRadius: 3, minWidth: 140,
          }}>
            <div style={{ fontWeight: 700, color, marginBottom: 4 }}>
              {zone.label || "New Zone"}
            </div>
            <div style={{ fontSize: 10, color: "#7a8ba0" }}>
              Z{zone.zoom} {zone.grid_size}x{zone.grid_size} — {ZOOM_PRESETS[zone.zoom]?.mpp}
            </div>
            <div style={{ fontSize: 10, color: "#4a5a70", marginTop: 2 }}>
              Drag marker to reposition
            </div>
            {!isDraft && (
              <button
                onClick={onDelete}
                style={{
                  marginTop: 6, padding: "3px 10px", background: "#c0392b",
                  color: "white", border: "none", borderRadius: 2, cursor: "pointer",
                  fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
                  fontWeight: 600, width: "100%",
                }}
              >
                Delete Zone
              </button>
            )}
          </div>
        </Popup>
      </Marker>
    </>
  );
}

export default function CoordsEditor({ airbase, onUpdated }) {
  const [zones, setZones] = useState(airbase.capture_zones || []);
  const [addMode, setAddMode] = useState(false);
  const [newZoom, setNewZoom] = useState(17);
  const [draft, setDraft] = useState(null); // Unsaved zone being positioned
  const [saving, setSaving] = useState(false);

  const newGridSize = ZOOM_PRESETS[newZoom]?.gridSize || 6;
  const zoneColors = ["#2d7dd2", "#27ae60", "#e67e22", "#9b59b6", "#e74c3c", "#1abc9c", "#f39c12", "#8e44ad"];

  function handleMapClick(lat, lng) {
    if (!addMode) return;
    // Create a draft zone (not saved yet)
    setDraft({
      latitude: lat,
      longitude: lng,
      zoom: newZoom,
      grid_size: newGridSize,
      label: `zone-${zones.length + 1}`,
    });
  }

  function handleDraftMove(lat, lng) {
    setDraft((prev) => prev ? { ...prev, latitude: lat, longitude: lng } : null);
  }

  async function handleSaveDraft() {
    if (!draft) return;
    setSaving(true);
    try {
      const { data } = await api.post(`/api/airbases/${airbase.id}/zones`, {
        latitude: draft.latitude,
        longitude: draft.longitude,
        zoom: draft.zoom,
        grid_size: draft.grid_size,
        label: draft.label,
      });
      setZones([...zones, data]);
      setDraft(null);
      setAddMode(false);
      const { data: updated } = await api.get(`/api/airbases/${airbase.id}`);
      onUpdated(updated);
    } finally {
      setSaving(false);
    }
  }

  function handleCancelDraft() {
    setDraft(null);
  }

  async function handleDeleteZone(zoneId) {
    await api.delete(`/api/airbases/${airbase.id}/zones/${zoneId}`);
    setZones(zones.filter((z) => z.id !== zoneId));
    const { data: updated } = await api.get(`/api/airbases/${airbase.id}`);
    onUpdated(updated);
  }

  return (
    <div>
      <h3>Capture Zones</h3>
      <p style={{ fontSize: 11, color: "#4a5a70", marginBottom: 12 }}>
        Place capture zones to cover the full base. Drag the center marker to reposition.
      </p>

      {/* Zone list */}
      <div style={{ marginBottom: 12 }}>
        {zones.length === 0 && !draft && (
          <div style={{
            padding: 12, background: "#0d1118", borderRadius: 3, border: "1px solid #1b2535",
            fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#4a5a70",
          }}>
            No zones defined. Without zones, capture uses a single default tile at the base center.
          </div>
        )}
        {zones.map((z, i) => (
          <div key={z.id} style={{
            display: "flex", alignItems: "center", gap: 10,
            padding: "6px 10px", marginBottom: 3,
            background: "#0d1118", borderRadius: 3,
            borderLeft: `3px solid ${zoneColors[i % zoneColors.length]}`,
            border: `1px solid ${zoneColors[i % zoneColors.length]}22`,
          }}>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
              color: zoneColors[i % zoneColors.length], fontWeight: 600,
              textTransform: "uppercase", minWidth: 70,
            }}>
              {z.label}
            </span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#7a8ba0" }}>
              z{z.zoom} {z.grid_size}x{z.grid_size}
            </span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#4a5a70", flex: 1 }}>
              {z.latitude.toFixed(4)}, {z.longitude.toFixed(4)}
            </span>
            <button
              onClick={() => handleDeleteZone(z.id)}
              style={{
                background: "none", border: "none", color: "#c0392b",
                cursor: "pointer", fontSize: 13, padding: "0 4px",
                fontFamily: "'JetBrains Mono', monospace", fontWeight: 700,
              }}
            >
              x
            </button>
          </div>
        ))}
      </div>

      {/* Controls */}
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12, flexWrap: "wrap" }}>
        {!addMode && !draft && (
          <button onClick={() => setAddMode(true)} style={btnPrimary}>+ Add Zone</button>
        )}

        {addMode && !draft && (
          <>
            <span style={statusText("#27ae60")}>Click map to place zone</span>
            <div style={{ display: "flex", gap: 3 }}>
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
            <button onClick={() => setAddMode(false)} style={btnCancel}>Cancel</button>
          </>
        )}

        {draft && (
          <>
            <span style={statusText("#e67e22")}>Drag to position, then save</span>
            <button onClick={handleSaveDraft} disabled={saving} style={btnSave}>
              {saving ? "Saving..." : "Save Zone"}
            </button>
            <button onClick={handleCancelDraft} style={btnCancel}>Discard</button>
          </>
        )}
      </div>

      {/* Map */}
      <div style={{
        height: 600, borderRadius: 4, overflow: "hidden",
        border: addMode ? "2px solid #27ae60" : draft ? "2px solid #e67e22" : "1px solid #1b2535",
      }}>
        <MapContainer
          center={[airbase.latitude, airbase.longitude]}
          zoom={14}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            maxZoom={19}
          />

          {/* Saved zones */}
          {zones.map((z, i) => (
            <DraggableZone
              key={z.id}
              zone={z}
              color={zoneColors[i % zoneColors.length]}
              onMove={() => {}} // Saved zones don't move (would need PATCH endpoint)
              onDelete={() => handleDeleteZone(z.id)}
              isDraft={false}
            />
          ))}

          {/* Draft zone (draggable) */}
          {draft && (
            <DraggableZone
              zone={draft}
              color="#f39c12"
              onMove={handleDraftMove}
              onDelete={handleCancelDraft}
              isDraft={true}
            />
          )}

          {/* Click to add */}
          {addMode && !draft && <ClickHandler onAdd={handleMapClick} />}
        </MapContainer>
      </div>
    </div>
  );
}

const btnPrimary = {
  padding: "7px 16px", background: "#2d7dd2", color: "white",
  border: "none", borderRadius: 3, cursor: "pointer",
  fontFamily: "'JetBrains Mono', monospace", fontWeight: 600,
  fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px",
};

const btnSave = {
  padding: "7px 16px", background: "#27ae60", color: "white",
  border: "none", borderRadius: 3, cursor: "pointer",
  fontFamily: "'JetBrains Mono', monospace", fontWeight: 600,
  fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px",
};

const btnCancel = {
  padding: "5px 10px", background: "none", border: "1px solid #1b2535",
  color: "#7a8ba0", borderRadius: 3, cursor: "pointer",
  fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
};

const statusText = (color) => ({
  fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
  color, textTransform: "uppercase", letterSpacing: "1px",
});
