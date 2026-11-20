import {
  BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
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

const FALLBACK_COLOR = "#4a5a70";

function getColor(type) {
  return TYPE_COLORS[type] || FALLBACK_COLOR;
}

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

  // Aggregate totals across all captures
  const totalsByType = {};
  let grandTotal = 0;
  timeline.forEach((cap) => {
    Object.entries(cap.aircraft_types || {}).forEach(([type, count]) => {
      totalsByType[type] = (totalsByType[type] || 0) + count;
      grandTotal += count;
    });
  });

  const sortedTypes = Object.entries(totalsByType).sort((a, b) => b[1] - a[1]);

  // Latest capture
  const latest = timeline[timeline.length - 1];
  const latestTotal = latest?.total_aircraft || 0;

  // Pie chart data
  const pieData = sortedTypes.map(([type, count]) => ({
    name: type,
    value: count,
  }));

  // Area chart data (timeline)
  const allTypes = [...new Set(timeline.flatMap((t) => Object.keys(t.aircraft_types || {})))];
  const areaData = timeline.map((cap) => ({
    date: new Date(cap.date).toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    }),
    total: cap.total_aircraft,
    ...cap.aircraft_types,
  }));

  // Bar chart for latest capture breakdown
  const latestBarData = Object.entries(latest?.aircraft_types || {})
    .sort((a, b) => b[1] - a[1])
    .map(([type, count]) => ({ type, count }));

  return (
    <div>
      {/* Top stats row */}
      <div className="analytics-stats-row">
        <div className="analytics-stat-card">
          <div className="analytics-stat-value">{timeline.length}</div>
          <div className="analytics-stat-label">Total Captures</div>
        </div>
        <div className="analytics-stat-card accent">
          <div className="analytics-stat-value">{grandTotal}</div>
          <div className="analytics-stat-label">Total Detections</div>
        </div>
        <div className="analytics-stat-card">
          <div className="analytics-stat-value">{sortedTypes.length}</div>
          <div className="analytics-stat-label">Unique Types</div>
        </div>
        <div className="analytics-stat-card">
          <div className="analytics-stat-value">{latestTotal}</div>
          <div className="analytics-stat-label">Last Capture Count</div>
        </div>
      </div>

      {/* Charts row */}
      <div className="analytics-charts-row">
        {/* Timeline area chart */}
        <div className="card" style={{ flex: 2 }}>
          <h3>Detection Timeline</h3>
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <AreaChart data={areaData}>
                <defs>
                  <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2d7dd2" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#2d7dd2" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1b2535" />
                <XAxis dataKey="date" stroke="#4a5a70" fontSize={9} fontFamily="JetBrains Mono" angle={-20} textAnchor="end" height={45} />
                <YAxis stroke="#4a5a70" fontSize={10} fontFamily="JetBrains Mono" allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: "#d0d8e4" }} />
                <Area type="monotone" dataKey="total" stroke="#2d7dd2" strokeWidth={2} fill="url(#totalGrad)" name="Total" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pie chart */}
        <div className="card" style={{ flex: 1 }}>
          <h3>Type Distribution</h3>
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="none"
                >
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={getColor(entry.name)} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
                <Legend
                  wrapperStyle={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10 }}
                  formatter={(value) => <span style={{ color: "#7a8ba0" }}>{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="analytics-charts-row">
        {/* Per-type stacked bar chart across captures */}
        <div className="card" style={{ flex: 2 }}>
          <h3>Type Breakdown Per Capture</h3>
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={areaData} barCategoryGap="20%">
                <CartesianGrid strokeDasharray="3 3" stroke="#1b2535" />
                <XAxis dataKey="date" stroke="#4a5a70" fontSize={9} fontFamily="JetBrains Mono" angle={-20} textAnchor="end" height={45} />
                <YAxis stroke="#4a5a70" fontSize={10} fontFamily="JetBrains Mono" allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: "#d0d8e4" }} />
                <Legend wrapperStyle={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9 }} />
                {allTypes.map((type) => (
                  <Bar key={type} dataKey={type} stackId="a" fill={getColor(type)} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Latest capture detail */}
        <div className="card" style={{ flex: 1 }}>
          <h3>Latest Capture</h3>
          {latestBarData.length === 0 ? (
            <p style={{ color: "#4a5a70", fontSize: 11 }}>No detections in latest capture.</p>
          ) : (
            <div className="analytics-latest-list">
              {latestBarData.map(({ type, count }) => (
                <div key={type} className="analytics-latest-item">
                  <div className="analytics-latest-bar" style={{ width: `${(count / latestBarData[0].count) * 100}%`, background: getColor(type) }} />
                  <span className="analytics-latest-type">{type}</span>
                  <span className="analytics-latest-count">{count}</span>
                </div>
              ))}
            </div>
          )}
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
