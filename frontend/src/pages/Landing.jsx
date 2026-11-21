import { useNavigate } from "react-router-dom";

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="landing">
      {/* Grid background */}
      <div className="landing-grid" />


      {/* Content */}
      <div className="landing-content">
        {/* Logo + Title */}
        <div className="landing-header">
          <img src="/logo.png" alt="République Française" className="landing-logo" />
          <h1 className="landing-title">VAUBAN</h1>
          <div className="landing-subtitle">IMINT & Military Intelligence Platform</div>
          <div className="landing-tricolor" />
        </div>

        {/* Description */}
        <p className="landing-desc">
          Satellite imagery analysis system for monitoring global military airbases.
          Powered by computer vision, real-time detection, and geospatial intelligence.
        </p>

        {/* Stats */}
        <div className="landing-stats">
          <div className="landing-stat">
            <span className="landing-stat-value">159</span>
            <span className="landing-stat-label">Airbases Monitored</span>
          </div>
          <div className="landing-stat">
            <span className="landing-stat-value">35</span>
            <span className="landing-stat-label">Countries</span>
          </div>
          <div className="landing-stat">
            <span className="landing-stat-value">20</span>
            <span className="landing-stat-label">Aircraft Types</span>
          </div>
          <div className="landing-stat">
            <span className="landing-stat-value">3</span>
            <span className="landing-stat-label">Imagery Sources</span>
          </div>
        </div>

        {/* Capabilities */}
        <div className="landing-capabilities">
          <div className="landing-cap">
            <div className="landing-cap-icon">01</div>
            <div>
              <div className="landing-cap-title">Multi-Source Satellite Capture</div>
              <div className="landing-cap-desc">High-resolution imagery from Esri, Google, and Bing tile servers with multi-zone capture coverage</div>
            </div>
          </div>
          <div className="landing-cap">
            <div className="landing-cap-icon">02</div>
            <div>
              <div className="landing-cap-title">YOLOv8 Aircraft Detection</div>
              <div className="landing-cap-desc">Custom-trained model detecting 20 aircraft types with country-aware intelligent reclassification</div>
            </div>
          </div>
          <div className="landing-cap">
            <div className="landing-cap-icon">03</div>
            <div>
              <div className="landing-cap-title">Change Detection Analytics</div>
              <div className="landing-cap-desc">Temporal comparison across captures with force composition analysis and deployment tracking</div>
            </div>
          </div>
          <div className="landing-cap">
            <div className="landing-cap-icon">04</div>
            <div>
              <div className="landing-cap-title">Aircraft Intelligence Database</div>
              <div className="landing-cap-desc">Complete specs, weapons loadouts, and operational context for every detected aircraft type</div>
            </div>
          </div>
        </div>

        {/* Enter button */}
        <button className="landing-enter" onClick={() => navigate("/dashboard")}>
          Access Platform
        </button>

        {/* Footer */}
        <div className="landing-footer">
          <span>Defence Proof of Work</span>
          <span className="landing-dot" />
          <span>Educational & Research Use</span>
          <span className="landing-dot" />
          <span>Named after Sébastien Le Prestre de Vauban, Marshal of France</span>
        </div>
      </div>
    </div>
  );
}
