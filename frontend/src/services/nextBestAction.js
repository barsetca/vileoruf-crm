import { requireApiBaseUrl } from "./api.js";


async function request(path, token, options = {}) {
  const response = await fetch(`${requireApiBaseUrl()}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail ?? `Next Best Action request failed with ${response.status}`);
  return body;
}


export const getNextBestAction = (token, dealId, signal) => request(`/deals/${dealId}/next-best-action`, token, { signal });
export const launchNextBestAction = (token, dealId, language) => request(`/deals/${dealId}/next-best-action`, token, {
  method: "POST",
  body: JSON.stringify({ language: language.toUpperCase() }),
});
