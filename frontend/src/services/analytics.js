import { requireApiBaseUrl } from "./api.js";

export async function getAnalyticsSummary(token, signal) {
  const response = await fetch(`${requireApiBaseUrl()}/analytics/summary`, { signal, headers: { Authorization: `Bearer ${token}` } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail ?? `Analytics request failed with ${response.status}`);
  return body;
}
