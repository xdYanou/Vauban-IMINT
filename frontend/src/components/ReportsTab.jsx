import { useState, useEffect } from "react";
import api from "../utils/api";

export default function ReportsTab({ airbaseId, airbaseName }) {
  const [reports, setReports] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);

  function loadReports() {
    api.get(`/api/reports/list/${airbaseId}`).then(({ data }) => setReports(data)).catch(() => {});
  }

  async function handleDelete(reportId) {
    if (!confirm("Delete this report?")) return;
    try {
      await api.delete(`/api/reports/${reportId}`);
      loadReports();
    } catch {}
  }

  useEffect(() => { loadReports(); }, [airbaseId]);

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      await api.post(`/api/reports/generate/${airbaseId}`);
      loadReports();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to generate report");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <h3 style={{ margin: 0 }}>Intelligence Reports</h3>
          <p style={{ fontSize: 11, color: "#4a5a70", margin: "4px 0 0 0", fontFamily: "'JetBrains Mono', monospace" }}>
            Generate INTSUM PDF reports from captured imagery and detections
          </p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          style={{
            padding: "10px 24px",
            background: generating ? "#1b2535" : "#c0392b",
            color: "white",
            border: "none",
            borderRadius: 3,
            cursor: generating ? "wait" : "pointer",
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 600,
            fontSize: 11,
            textTransform: "uppercase",
            letterSpacing: "1px",
          }}
        >
          {generating ? "Generating..." : "Generate Report"}
        </button>
      </div>

      {error && <p style={{ color: "#c0392b", fontSize: 12 }}>{error}</p>}

      {reports.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: 40 }}>
          <p style={{ color: "#4a5a70", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
            No reports generated yet. Run captures first, then generate a report.
          </p>
        </div>
      ) : (
        <div className="reports-list">
          {reports.map((report) => (
            <div key={report.id} className="report-card">
              <div className="report-card-header">
                <div className="report-card-badge">INTSUM</div>
                <div className="report-card-date">
                  {new Date(report.generated_at).toLocaleString()}
                </div>
              </div>
              <div className="report-card-title">{report.airbase}</div>
              <div className="report-card-stats">
                <span>{report.total_detections} aircraft detected</span>
                <span>{Object.keys(report.aircraft_types || {}).length} types</span>
              </div>
              {Object.keys(report.aircraft_types || {}).length > 0 && (
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 8 }}>
                  {Object.entries(report.aircraft_types).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([type, count]) => (
                    <span key={type} className={`type-badge type-${type}`}>{type}: {count}</span>
                  ))}
                </div>
              )}
              <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                <a
                  href={`http://localhost:8000/api/reports/download/${report.filename}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="report-download"
                >
                  Download PDF
                </a>
                <button
                  onClick={() => handleDelete(report.id)}
                  style={{
                    padding: "6px 12px", background: "rgba(192,57,43,0.1)",
                    color: "#c0392b", border: "1px solid rgba(192,57,43,0.2)",
                    borderRadius: 3, cursor: "pointer", fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10, fontWeight: 600, textTransform: "uppercase",
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
