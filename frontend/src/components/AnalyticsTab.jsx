import {
  BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from "recharts";

const TYPE_COLORS = {
  "Su-35": "#e74c3c", "Su-34": "#ef5350", "Su-24": "#c0392b",
  "Tu-95": "#ff9800", "Tu-160": "#e65100", "Tu-22M": "#d4780a",
  "F-15": "#2d7dd2", "F-16": "#1e88e5", "F-22": "#7c4dff", "FA-18": "#42a5f5",
  "B-52": "#8d6e63", "B-1B": "#6d4c41",
  "C-130": "#27ae60", "C-17": "#2e7d32", "C-5": "#1b5e20",
  "KC-135": "#26a69a", "KC-10": "#00897b",
  "E-3": "#9b59b6", "E-8": "#7b1fa2",
  "P-3C": "#78909c",
};

// Map aircraft types to role categories
const ROLE_MAP = {
  "Su-35": "Fighter", "Su-35S": "Fighter", "Su-30SM": "Fighter", "Su-27SM": "Fighter",
  "F-15": "Fighter", "F-16": "Fighter", "F-22": "Fighter", "FA-18": "Fighter",
  "F-35A": "Fighter", "F-35I Adir": "Fighter", "Typhoon": "Fighter", "Eurofighter": "Fighter",
  "Rafale": "Fighter", "EF-18": "Fighter", "F-16V": "Fighter", "F-16C": "Fighter",
  "F-16AM": "Fighter", "F-2A": "Fighter", "KF-21": "Fighter", "Gripen E": "Fighter",
  "CF-18": "Fighter", "MiG-29": "Fighter", "MiG-29SMT": "Fighter", "MiG-31BM": "Fighter",
  "JF-17": "Fighter", "J-20": "Fighter", "F-14A Tomcat": "Fighter",

  "Su-34": "Strike", "Su-24": "Strike", "Su-24M": "Strike",
  "F-15E": "Strike", "F-15I Ra'am": "Strike", "F-15K": "Strike", "F-15SA": "Strike",
  "Tornado": "Strike", "Mirage 2000-5": "Strike", "Mirage 2000-9": "Strike",
  "Su-25": "Strike", "Su-25SM": "Strike", "J-16": "Strike",
  "F-4E Phantom": "Strike", "Saeqeh": "Strike", "Kowsar": "Strike",

  "Tu-95": "Bomber", "Tu-95MS": "Bomber", "Tu-160": "Bomber", "Tu-22M": "Bomber", "Tu-22M3": "Bomber",
  "B-52": "Bomber", "B-1B": "Bomber", "H-6K": "Bomber",

  "C-130": "Transport", "C-17": "Transport", "C-5": "Transport", "C-2": "Transport",
  "Il-76": "Transport", "An-124": "Transport", "An-26": "Transport",
  "A400M": "Transport", "C-130J": "Transport", "CC-130J": "Transport", "CC-177": "Transport",
  "Y-20": "Transport",

  "KC-135": "Tanker/ISR", "KC-10": "Tanker/ISR", "KC-767": "Tanker/ISR",
  "KC-330": "Tanker/ISR", "KC-30A": "Tanker/ISR", "Il-78": "Tanker/ISR",
  "Voyager": "Tanker/ISR", "A330 MRTT": "Tanker/ISR",
  "E-3": "Tanker/ISR", "E-8": "Tanker/ISR", "E-767": "Tanker/ISR", "E-7 Wedgetail": "Tanker/ISR",
  "E-3F": "Tanker/ISR", "E-2K": "Tanker/ISR", "A-50": "Tanker/ISR",
  "P-3C": "Tanker/ISR", "P-1": "Tanker/ISR", "P-8A": "Tanker/ISR", "P-8A Poseidon": "Tanker/ISR",
  "KJ-500": "Tanker/ISR", "G550 CAEW": "Tanker/ISR",
};

const ROLE_COLORS = {
  "Fighter": "#e74c3c",
  "Strike": "#e67e22",
  "Bomber": "#f39c12",
  "Transport": "#27ae60",
  "Tanker/ISR": "#9b59b6",
  "Unknown": "#4a5a70",
};

const FALLBACK_COLOR = "#4a5a70";
function getColor(type) { return TYPE_COLORS[type] || FALLBACK_COLOR; }
function getRole(type) { return ROLE_MAP[type] || "Unknown"; }

export default function AnalyticsTab({ timeline }) {
  if (!timeline || !timeline.length) {
    return (
      <div className="card" style={{ textAlign: "center", padding: 40 }}>
        <p style={{ color: "#4a5a70", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
          No data yet. Run captures to generate analytics.
        </p>
      </div>
    );
  }

  // Aggregate totals
  const totalsByType = {};
  const totalsByRole = {};
  let grandTotal = 0;
  timeline.forEach((cap) => {
    Object.entries(cap.aircraft_types || {}).forEach(([type, count]) => {
      totalsByType[type] = (totalsByType[type] || 0) + count;
      const role = getRole(type);
      totalsByRole[role] = (totalsByRole[role] || 0) + count;
      grandTotal += count;
    });
  });

  const sortedTypes = Object.entries(totalsByType).sort((a, b) => b[1] - a[1]);
  const latest = timeline[timeline.length - 1];
  const prev = timeline.length > 1 ? timeline[timeline.length - 2] : null;

  // Delta calculation
  const latestTotal = latest?.total_aircraft || 0;
  const prevTotal = prev?.total_aircraft || 0;
  const delta = latestTotal - prevTotal;

  // Role pie data
  const rolePieData = Object.entries(totalsByRole).sort((a, b) => b[1] - a[1]).map(([role, count]) => ({
    name: role, value: count,
  }));

  // Timeline area data
  const areaData = timeline.map((cap) => ({
    date: new Date(cap.date).toLocaleString(undefined, { month: "short", day: "numeric" }),
    total: cap.total_aircraft,
    ...cap.aircraft_types,
  }));

  // Role breakdown over time
  const roleTimeData = timeline.map((cap) => {
    const roles = {};
    Object.entries(cap.aircraft_types || {}).forEach(([type, count]) => {
      const role = getRole(type);
      roles[role] = (roles[role] || 0) + count;
    });
    return {
      date: new Date(cap.date).toLocaleString(undefined, { month: "short", day: "numeric" }),
      ...roles,
    };
  });

  // Radar data for role composition
  const radarData = Object.entries(totalsByRole).map(([role, count]) => ({
    role, count, fullMark: Math.max(...Object.values(totalsByRole)) * 1.2,
  }));

  // Delta per type (latest vs previous)
  const deltaData = [];
  if (prev) {
    const allTypes = new Set([
      ...Object.keys(latest?.aircraft_types || {}),
      ...Object.keys(prev?.aircraft_types || {}),
    ]);
    allTypes.forEach((type) => {
      const cur = (latest?.aircraft_types || {})[type] || 0;
      const prv = (prev?.aircraft_types || {})[type] || 0;
      const d = cur - prv;
      if (d !== 0) deltaData.push({ type, current: cur, previous: prv, delta: d });
    });
    deltaData.sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
  }

  return (
    <div>
      {/* Top stats */}
      <div className="analytics-stats-row">
        <div className="analytics-stat-card">
          <div className="analytics-stat-value">{timeline.length}</div>
          <div className="analytics-stat-label">Captures</div>
        </div>
        <div className="analytics-stat-card accent">
          <div className="analytics-stat-value">{latestTotal}</div>
          <div className="analytics-stat-label">Latest Count</div>
        </div>
        <div className="analytics-stat-card">
          <div className="analytics-stat-value" style={{ color: delta > 0 ? "#27ae60" : delta < 0 ? "#e74c3c" : "#7a8ba0" }}>
            {delta > 0 ? `+${delta}` : delta}
          </div>
          <div className="analytics-stat-label">Change</div>
        </div>
        <div className="analytics-stat-card">
          <div className="analytics-stat-value">{sortedTypes.length}</div>
          <div className="analytics-stat-label">Types Seen</div>
        </div>
      </div>

      {/* Row 1: Total timeline + Role composition radar */}
      <div className="analytics-charts-row">
        <div className="card" style={{ flex: 2 }}>
          <h3>Total Aircraft Over Time</h3>
          <div style={{ width: "100%", height: 250 }}>
            <ResponsiveContainer>
              <AreaChart data={areaData}>
                <defs>
                  <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2d7dd2" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#2d7dd2" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1b2535" />
                <XAxis dataKey="date" stroke="#4a5a70" fontSize={10} fontFamily="JetBrains Mono" />
                <YAxis stroke="#4a5a70" fontSize={10} fontFamily="JetBrains Mono" allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Area type="monotone" dataKey="total" stroke="#2d7dd2" strokeWidth={2} fill="url(#totalGrad)" name="Total" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card" style={{ flex: 1 }}>
          <h3>Force Composition</h3>
          <div style={{ width: "100%", height: 250 }}>
            <ResponsiveContainer>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#1b2535" />
                <PolarAngleAxis dataKey="role" stroke="#7a8ba0" fontSize={10} fontFamily="JetBrains Mono" />
                <PolarRadiusAxis stroke="#1b2535" fontSize={9} />
                <Radar dataKey="count" stroke="#2d7dd2" fill="#2d7dd2" fillOpacity={0.2} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Row 2: Role breakdown over time + Role pie */}
      <div className="analytics-charts-row">
        <div className="card" style={{ flex: 2 }}>
          <h3>Role Category Over Time</h3>
          <div style={{ width: "100%", height: 250 }}>
            <ResponsiveContainer>
              <BarChart data={roleTimeData} barCategoryGap="20%">
                <CartesianGrid strokeDasharray="3 3" stroke="#1b2535" />
                <XAxis dataKey="date" stroke="#4a5a70" fontSize={10} fontFamily="JetBrains Mono" />
                <YAxis stroke="#4a5a70" fontSize={10} fontFamily="JetBrains Mono" allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9 }} />
                {Object.keys(ROLE_COLORS).filter((r) => totalsByRole[r]).map((role) => (
                  <Bar key={role} dataKey={role} stackId="a" fill={ROLE_COLORS[role]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card" style={{ flex: 1 }}>
          <h3>Role Distribution</h3>
          <div style={{ width: "100%", height: 250 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie data={rolePieData} cx="50%" cy="50%" innerRadius={50} outerRadius={85} paddingAngle={2} dataKey="value" stroke="none">
                  {rolePieData.map((e) => <Cell key={e.name} fill={ROLE_COLORS[e.name] || FALLBACK_COLOR} />)}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9 }}
                  formatter={(v) => <span style={{ color: "#7a8ba0" }}>{v}</span>} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Row 3: Change detection + Top types */}
      <div className="analytics-charts-row">
        {/* Delta / Change detection */}
        <div className="card" style={{ flex: 1 }}>
          <h3>Change Detection {prev ? `(${new Date(prev.date).toLocaleDateString()} → ${new Date(latest.date).toLocaleDateString()})` : ""}</h3>
          {deltaData.length === 0 ? (
            <p style={{ color: "#4a5a70", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
              {timeline.length < 2 ? "Need 2+ captures for change detection" : "No changes detected"}
            </p>
          ) : (
            <div className="analytics-latest-list">
              {deltaData.map(({ type, current, previous, delta: d }) => (
                <div key={type} className="analytics-latest-item">
                  <div className="analytics-latest-bar" style={{
                    width: `${Math.min(100, Math.abs(d) / Math.max(...deltaData.map((x) => Math.abs(x.delta))) * 100)}%`,
                    background: d > 0 ? "#27ae60" : "#e74c3c",
                  }} />
                  <span className="analytics-latest-type">{type}</span>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", zIndex: 1 }}>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#4a5a70" }}>
                      {previous} → {current}
                    </span>
                    <span style={{
                      fontFamily: "'JetBrains Mono', monospace", fontSize: 14, fontWeight: 700,
                      color: d > 0 ? "#27ae60" : "#e74c3c",
                    }}>
                      {d > 0 ? `+${d}` : d}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top types overall */}
        <div className="card" style={{ flex: 1 }}>
          <h3>Top Aircraft (All Captures)</h3>
          <div className="analytics-latest-list">
            {sortedTypes.slice(0, 8).map(([type, count]) => (
              <div key={type} className="analytics-latest-item">
                <div className="analytics-latest-bar" style={{
                  width: `${(count / sortedTypes[0][1]) * 100}%`,
                  background: getColor(type),
                }} />
                <div style={{ display: "flex", alignItems: "center", gap: 8, zIndex: 1 }}>
                  <span className="analytics-latest-type">{type}</span>
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace", fontSize: 9,
                    color: ROLE_COLORS[getRole(type)] || "#4a5a70",
                    textTransform: "uppercase",
                  }}>
                    {getRole(type)}
                  </span>
                </div>
                <span className="analytics-latest-count">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

const tooltipStyle = {
  background: "#0a0e14",
  border: "1px solid #1b2535",
  borderRadius: 4,
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 11,
};
