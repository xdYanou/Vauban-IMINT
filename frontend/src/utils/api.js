import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
});

export async function fetchAirbases() {
  const { data } = await api.get("/api/airbases/");
  return data;
}

export async function fetchAirbase(id) {
  const { data } = await api.get(`/api/airbases/${id}`);
  return data;
}

export async function fetchObservations(airbaseId) {
  const { data } = await api.get(`/api/observations/airbase/${airbaseId}`);
  return data;
}

export async function fetchObservation(id) {
  const { data } = await api.get(`/api/observations/${id}`);
  return data;
}

export async function uploadObservation(airbaseId, date, file, source = "manual") {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post(
    `/api/observations/upload/${airbaseId}?observation_date=${date}&source=${source}`,
    form
  );
  return data;
}

export async function fetchOverview() {
  const { data } = await api.get("/api/analytics/overview");
  return data;
}

export async function fetchAirbaseTimeline(airbaseId) {
  const { data } = await api.get(`/api/analytics/airbase/${airbaseId}/timeline`);
  return data;
}

export async function fetchAirbaseSummary(airbaseId) {
  const { data } = await api.get(`/api/analytics/airbase/${airbaseId}/summary`);
  return data;
}

export default api;
