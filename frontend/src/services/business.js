import { requireApiBaseUrl } from "./api.js";


async function request(path, accessToken, options = {}) {
  const response = await fetch(`${requireApiBaseUrl()}${path}`, { ...options, headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json", ...options.headers } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail ?? `Business request failed with ${response.status}`);
  return body;
}


export const listCategories = (token, signal) => request("/business/categories", token, { signal });
export const createCategory = (token, payload) => request("/business/categories", token, { method: "POST", body: JSON.stringify(payload) });
export const updateCategory = (token, id, payload) => request(`/business/categories/${id}`, token, { method: "PATCH", body: JSON.stringify(payload) });
export const listServices = (token, signal) => request("/business/services", token, { signal });
export const createService = (token, payload) => request("/business/services", token, { method: "POST", body: JSON.stringify(payload) });
export const updateService = (token, id, payload) => request(`/business/services/${id}`, token, { method: "PATCH", body: JSON.stringify(payload) });
export const getLeadScoringSettings = (token, signal) => request("/business/lead-scoring-settings", token, { signal });
export const updateLeadScoringSettings = (token, payload) => request("/business/lead-scoring-settings", token, { method: "PUT", body: JSON.stringify(payload) });


export async function listPublicServices(signal) {
  const response = await fetch(`${requireApiBaseUrl()}/public/services`, { signal });
  if (!response.ok) throw new Error("Public services unavailable");
  return response.json();
}
