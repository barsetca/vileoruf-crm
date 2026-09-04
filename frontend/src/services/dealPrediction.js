import { requireApiBaseUrl } from "./api.js";

async function request(path, token, options = {}) {
  const response = await fetch(`${requireApiBaseUrl()}${path}`, { ...options, headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...options.headers } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail ?? `Deal Prediction request failed with ${response.status}`);
  return body;
}

export const getDealPrediction = (token, dealId, signal) => request(`/deals/${dealId}/deal-prediction`, token, { signal });
export const launchDealPrediction = (token, dealId, language) => request(`/deals/${dealId}/deal-prediction`, token, { method:"POST", body:JSON.stringify({ language:language.toUpperCase() }) });
