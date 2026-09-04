import { requireApiBaseUrl } from "./api.js";

export async function getAIHistory(token, filters = {}, signal) {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => { if (value !== "" && value !== null && value !== undefined && value !== false) query.set(key, String(value)); });
  const path = filters.dealPath ? `/deals/${filters.dealPath}/ai-history` : "/ai-history";
  query.delete("dealPath");
  const response = await fetch(`${requireApiBaseUrl()}${path}?${query}`, { signal, headers: { Authorization: `Bearer ${token}` } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail ?? `AI History request failed with ${response.status}`);
  return body;
}
