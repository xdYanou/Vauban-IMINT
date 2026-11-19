import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const TYPE_COLORS = {
  fighter: "#e74c3c", bomber: "#e67e22", attack: "#f1c40f",
  transport: "#2ecc71", tanker: "#3498db", surveillance: "#9b59b6",
  rotary: "#1abc9c", helicopter: "#1abc9c", trainer: "#95a5a6",
  unknown: "#7a8ba0",
  Su24: "#e74c3c", Su25: "#e67e22", Su34: "#ef5350", Su57: "#9b59b6",
  Mig29: "#3498db", Mig31: "#2d7dd2", Tu95: "#ff9800", Tu160: "#c0392b",
  Tu22M: "#d4780a", Il76: "#27ae60", Ka52: "#1abc9c", Mi8: "#66bb6a",
  Mi24: "#e67e22", Mi28: "#e74c3c", An124: "#2d7dd2", An22: "#3498db",
  bench: "#4a5a70",
};

export default function ObservationTimeline({ observations }) {
  if (!observations || !observations.length) {
    return <p style={{ color: "#4a5a70", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>No observation data yet.</p>;
  }

  const chartData = observations.map((obs) => ({
    date: new Date(obs.observation_date).toLocaleString(undefined, {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    }),
    total: obs.aircraft_count,
    ...obs.aircraft_types,
  }));

  const allTypes = [...new Set(observations.flatMap((o) => Object.keys(o.aircraft_types || {})))];

  return (
    <div style={{ width: "100%", height: 320 }}>
      <ResponsiveContainer>
        <BarChart data={chartData} barCategoryGap="20%">
          <CartesianGrid strokeDasharray="3 3" stroke="#1b2535" />
          <XAxis
            dataKey="date"
            stroke="#4a5a70"
            fontSize={10}
            fontFamily="JetBrains Mono"
            angle={-30}
            textAnchor="end"
            height={50}
          />
          <YAxis
            stroke="#4a5a70"
            fontSize={10}
            fontFamily="JetBrains Mono"
            allowDecimals={false}
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
          {/* Total bar — semi-transparent white behind */}
          <Bar dataKey="total" fill="#d0d8e422" stroke="#d0d8e4" strokeWidth={1} name="Total" />
          {/* Stacked type bars */}
          {allTypes.map((type) => (
            <Bar
              key={type}
              dataKey={type}
              stackId="types"
              fill={TYPE_COLORS[type] || "#4a5a70"}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
