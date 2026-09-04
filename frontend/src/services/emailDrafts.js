import { requireApiBaseUrl } from "./api.js";

async function request(path, token, options = {}) {
  const response = await fetch(`${requireApiBaseUrl()}${path}`, {
    ...options,
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...options.headers },
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail ?? `Email Draft request failed with ${response.status}`);
  return body;
}

export const getEmailGeneration = (token, dealId, signal) => request(`/deals/${dealId}/email-draft`, token, { signal });
export const generateEmailDraft = (token, dealId, payload) => request(`/deals/${dealId}/email-draft`, token, { method: "POST", body: JSON.stringify(payload) });
export const listEmailDrafts = (token, dealId, signal) => request(`/deals/${dealId}/email-drafts`, token, { signal });
export const createEmailDraft = (token, dealId, payload) => request(`/deals/${dealId}/email-drafts`, token, { method: "POST", body: JSON.stringify(payload) });
export const updateEmailDraft = (token, dealId, draftId, payload) => request(`/deals/${dealId}/email-drafts/${draftId}`, token, { method: "PATCH", body: JSON.stringify(payload) });
export const deleteEmailDraft = (token, dealId, draftId) => request(`/deals/${dealId}/email-drafts/${draftId}`, token, { method: "DELETE" });
