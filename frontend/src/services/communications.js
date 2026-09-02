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
