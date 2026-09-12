import { requireApiBaseUrl } from "./api.js";


export class ClientApiError extends Error {
  constructor(status, detail) {
    super(`Client request failed with ${status}`);
    this.name = "ClientApiError";
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
  if (!response.ok) {
    throw new ClientApiError(response.status, body?.detail);
  }
  return body;
}


export function listClients(accessToken, { limit, offset, archived = false }, signal) {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset), archived: String(archived) });
  return request(`/clients?${query}`, accessToken, { signal });
}

export const getClient = (accessToken, clientId) => request(`/clients/${clientId}`, accessToken);
export const createClient = (accessToken, payload) => request("/clients", accessToken, {
  method: "POST",
  body: JSON.stringify(payload),
});
export const updateClient = (accessToken, clientId, payload) => request(`/clients/${clientId}`, accessToken, {
  method: "PATCH",
  body: JSON.stringify(payload),
});
export const archiveClient = (accessToken, clientId) => request(`/clients/${clientId}/archive`, accessToken, { method: "POST" });
export const restoreClient = (accessToken, clientId) => request(`/clients/${clientId}/restore`, accessToken, { method: "POST" });
