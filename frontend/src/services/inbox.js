import { requireApiBaseUrl } from "./api.js";

async function request(path, accessToken, options = {}) {
  const response = await fetch(`${requireApiBaseUrl()}${path}`, { ...options, headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json", ...options.headers } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail || "Inbox request failed");
  return body;
}

export const listInboxMessages = (accessToken, signal, channel = "") => request(`/inbox/external-messages?limit=25&offset=0${channel ? `&channel=${channel}` : ""}`, accessToken, { signal });
export const linkInboxMessage = (accessToken, messageId, clientId, dealId = null) => request(`/inbox/external-messages/${messageId}/link`, accessToken, { method: "POST", body: JSON.stringify({ client_id: clientId, deal_id: dealId }) });
export const getInboxSummary = (accessToken, signal) => request("/inbox/summary", accessToken, { signal });
export const bulkDeleteInboxMessages = (accessToken, ids) => request("/inbox/external-messages/bulk-delete", accessToken, { method: "POST", body: JSON.stringify({ external_message_ids: ids }) });
