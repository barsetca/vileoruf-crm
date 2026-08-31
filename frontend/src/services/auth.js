import { requireApiBaseUrl } from "./api.js";


export class AuthApiError extends Error {
  constructor(status) {
    super(`Authentication request failed with ${status}`);
    this.name = "AuthApiError";
    this.status = status;
  }
}

async function authRequest(path, options = {}) {
  const response = await fetch(`${requireApiBaseUrl()}${path}`, options);

  if (!response.ok) {
    throw new AuthApiError(response.status);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export function login(email, password) {
  return authRequest("/auth/login", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export function refresh() {
  return authRequest("/auth/refresh", {
    method: "POST",
    credentials: "include",
  });
}

export function logout() {
  return authRequest("/auth/logout", {
    method: "POST",
    credentials: "include",
  });
}

export function getMe(accessToken) {
  return authRequest("/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
