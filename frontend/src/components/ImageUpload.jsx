import { useState } from "react";
import { uploadObservation } from "../utils/api";

export default function ImageUpload({ airbaseId, onUploaded }) {
  const [file, setFile] = useState(null);
  const [date, setDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file || !date) return;

    setLoading(true);
    setError(null);
    try {
      const result = await uploadObservation(airbaseId, date, file);
      onUploaded(result);
      setFile(null);
      setDate("");
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="upload-form">
      <h3>Upload Satellite Image</h3>
      <div style={{ display: "flex", gap: 12, alignItems: "end", flexWrap: "wrap" }}>
        <label>
          Date
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
          />
        </label>
        <label>
          Image
          <input
            type="file"
            accept="image/*,.tif,.tiff"
            onChange={(e) => setFile(e.target.files[0])}
            required
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Analyzing..." : "Upload & Detect"}
        </button>
      </div>
      {error && <p style={{ color: "#e74c3c" }}>{error}</p>}
    </form>
  );
}
