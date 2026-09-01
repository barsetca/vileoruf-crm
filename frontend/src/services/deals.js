import { requireApiBaseUrl } from "./api.js";


export class DealApiError extends Error {
  constructor(status, detail) {
    super(`Deal request failed with ${status}`);
    this.name = "DealApiError";
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
  if (!response.ok) throw new DealApiError(response.status, body?.detail);
  return body;
}


export function listDeals(accessToken, { limit, offset }, signal) {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return request(`/deals?${query}`, accessToken, { signal });
}

export const getDeal = (accessToken, dealId) => request(`/deals/${dealId}`, accessToken);
export const createDeal = (accessToken, payload) => request("/deals", accessToken, {
  method: "POST",
  body: JSON.stringify(payload),
});
export const updateDeal = (accessToken, dealId, payload) => request(`/deals/${dealId}`, accessToken, {
  method: "PATCH",
  body: JSON.stringify(payload),
});
export const transitionDeal = (accessToken, dealId, stageId) => request(`/deals/${dealId}/transition`, accessToken, {
  method: "POST",
  body: JSON.stringify({ stage_id: stageId }),
});
