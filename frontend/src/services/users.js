import { AuthApiError } from "./auth.js";
import { requireApiBaseUrl } from "./api.js";


async function request(path, accessToken, options = {}) {
  const response = await fetch(`${requireApiBaseUrl()}${path}`, {
    ...options,
    headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new AuthApiError(response.status);
    error.detail = body.detail;
    throw error;
  }
  return response.json();
}

export const listUsers = (token) => request("/users", token);
export const createUser = (token, payload) => request("/users", token, { method: "POST", body: JSON.stringify(payload) });
export const updateUser = (token, id, payload) => request(`/users/${id}`, token, { method: "PATCH", body: JSON.stringify(payload) });
