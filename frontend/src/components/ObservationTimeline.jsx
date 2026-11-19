import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
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
  unknown: "#6b7a8d",
};

export default function ObservationTimeline({ observations }) {
  if (!observations || !observations.length) {
    return <p style={{ color: "#4a5567", fontSize: 13 }}>No observation data yet.</p>;
  }

  const chartData = observations.map((obs) => ({
    date: new Date(obs.observation_date).toLocaleDateString(),
    ...obs.aircraft_types,
    total: obs.aircraft_count,
  }));

  const allTypes = [...new Set(observations.flatMap((o) => Object.keys(o.aircraft_types || {})))];

  return (
    <div style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2733" />
          <XAxis dataKey="date" stroke="#4a5567" fontSize={11} />
          <YAxis stroke="#4a5567" fontSize={11} />
          <Tooltip
            contentStyle={{
              background: "#12171e",
              border: "1px solid #1e2733",
              borderRadius: 6,
              fontSize: 12,
            }}
            labelStyle={{ color: "#c8d1db" }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {allTypes.map((type) => (
            <Bar key={type} dataKey={type} stackId="a" fill={TYPE_COLORS[type] || "#4a5567"} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
