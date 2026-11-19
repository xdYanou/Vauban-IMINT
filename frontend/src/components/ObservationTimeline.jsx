import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const TYPE_COLORS = {
  fighter: "#e74c3c",
  bomber: "#e67e22",
  attack: "#f1c40f",
  transport: "#2ecc71",
  tanker: "#3498db",
  surveillance: "#9b59b6",
  rotary: "#1abc9c",
  helicopter: "#1abc9c",
  trainer: "#95a5a6",
  unknown: "#7a8ba0",
  Su24: "#e74c3c",
  Su25: "#e67e22",
  Su34: "#e74c3c",
  Su57: "#9b59b6",
  Mig29: "#3498db",
  Mig31: "#2d7dd2",
  Tu95: "#e67e22",
  Tu160: "#c0392b",
  Tu22M: "#d4780a",
  Il76: "#27ae60",
  Ka52: "#1abc9c",
  Mi8: "#27ae60",
  Mi24: "#e67e22",
  Mi28: "#e74c3c",
  An124: "#2d7dd2",
};

export default function ObservationTimeline({ observations }) {
  if (!observations || !observations.length) {
    return <p style={{ color: "#4a5a70", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>No observation data yet.</p>;
  }

  const chartData = observations.map((obs) => ({
    date: new Date(obs.observation_date).toLocaleDateString(),
    total: obs.aircraft_count,
    ...obs.aircraft_types,
  }));

  const allTypes = [...new Set(observations.flatMap((o) => Object.keys(o.aircraft_types || {})))];

  return (
    <div style={{ width: "100%", height: 300 }}>
      <ResponsiveContainer>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1b2535" />
          <XAxis
            dataKey="date"
            stroke="#4a5a70"
            fontSize={10}
            fontFamily="JetBrains Mono"
          />
          <YAxis
            stroke="#4a5a70"
            fontSize={10}
            fontFamily="JetBrains Mono"
          />
          <Tooltip
            contentStyle={{
              background: "#0d1118",
              border: "1px solid #1b2535",
              borderRadius: 4,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
            }}
            labelStyle={{ color: "#d0d8e4", marginBottom: 4 }}
          />
          <Legend
            wrapperStyle={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10,
            }}
          />
          {/* Total line — thicker, white */}
          <Line
            type="monotone"
            dataKey="total"
            stroke="#d0d8e4"
            strokeWidth={2.5}
            dot={{ r: 3, fill: "#d0d8e4" }}
            name="Total"
          />
          {/* Per-type lines */}
          {allTypes.map((type) => (
            <Line
              key={type}
              type="monotone"
              dataKey={type}
              stroke={TYPE_COLORS[type] || "#4a5a70"}
              strokeWidth={1.5}
              dot={{ r: 2, fill: TYPE_COLORS[type] || "#4a5a70" }}
              strokeDasharray={allTypes.length > 5 ? "4 2" : undefined}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
