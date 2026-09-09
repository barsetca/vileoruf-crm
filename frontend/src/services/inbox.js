import { requireApiBaseUrl } from "./api.js";

async function request(path, accessToken, options = {}) {
  const response = await fetch(`${requireApiBaseUrl()}${path}`, { ...options, headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json", ...options.headers } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail || "Inbox request failed");
  return body;
}

export const listInboxMessages = (accessToken, signal) => request("/inbox/external-messages?limit=25&offset=0", accessToken, { signal });
export const linkInboxMessage = (accessToken, messageId, clientId) => request(`/inbox/external-messages/${messageId}/link`, accessToken, { method: "POST", body: JSON.stringify({ client_id: clientId }) });
