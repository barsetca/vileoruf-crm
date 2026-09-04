import { requireApiBaseUrl } from "./api.js";


async function request(path, token, options = {}) {
  const response = await fetch(`${requireApiBaseUrl()}${path}`, { ...options, headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...options.headers } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail ?? `Lead Scoring request failed with ${response.status}`);
  return body;
}


export const getLeadScoring = (token, dealId, signal) => request(`/deals/${dealId}/lead-scoring`, token, { signal });
export const launchLeadScoring = (token, dealId, language) => request(`/deals/${dealId}/lead-scoring`, token, { method: "POST", body: JSON.stringify({ language: language.toUpperCase() }) });
