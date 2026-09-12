import { requireApiBaseUrl } from "./api.js";


export class CommunicationApiError extends Error {
  constructor(status, detail) {
    super(`Communication request failed with ${status}`);
    this.name = "CommunicationApiError";
    this.status = status;
    this.detail = detail;
  }
}


async function request(path, accessToken, options = {}) {
  const response = await fetch(`${requireApiBaseUrl()}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new CommunicationApiError(response.status, body?.detail);
  return body;
}


export function listCommunications(accessToken, { limit, offset, clientId, dealId }, signal) {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (clientId) query.set("client_id", clientId);
  if (dealId) query.set("deal_id", dealId);
  return request(`/communications?${query}`, accessToken, { signal });
}


export function createCommunication(accessToken, payload) {
  return request("/communications", accessToken, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function markCommunicationRead(accessToken, communicationId) {
  return request(`/communications/${communicationId}/read`, accessToken, { method: "POST" });
}

export function assignCommunicationDeal(accessToken, communicationId, dealId) {
  return request(`/communications/${communicationId}/assign-deal?deal_id=${encodeURIComponent(dealId)}`, accessToken, { method: "POST" });
}

export function detachCommunicationDeal(accessToken, communicationId) {
  return request(`/communications/${communicationId}/detach-deal`, accessToken, { method: "POST" });
}

export function getIncomingCommunicationSummary(accessToken, signal) {
  return request("/communications/incoming-summary", accessToken, { signal });
}
