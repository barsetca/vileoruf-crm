import { requireApiBaseUrl } from "./api.js";

async function request(token, options = {}) {
  const response = await fetch(`${requireApiBaseUrl()}/settings/ai`, { ...options, headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail ?? `AI Settings request failed with ${response.status}`);
  return body;
}

export const getAISettings = (token, signal) => request(token, { signal });
export const updateAISettings = (token, payload) => request(token, { method: "PATCH", body: JSON.stringify(payload) });
