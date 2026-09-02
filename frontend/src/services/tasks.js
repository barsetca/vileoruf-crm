import { requireApiBaseUrl } from "./api.js";


export class TaskApiError extends Error {
  constructor(status, detail) {
    super(`Task request failed with ${status}`);
    this.name = "TaskApiError";
    this.status = status;
    this.detail = detail;
  }
}


async function request(path, accessToken, options = {}) {
  const response = await fetch(`${requireApiBaseUrl()}${path}`, {
    ...options,
    headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json", ...options.headers },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new TaskApiError(response.status, body?.detail);
  return body;
}


export function listTasks(accessToken, { limit, offset, status, responsibleUserId, clientId, dealId }, signal) {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (status) query.set("status", status);
  if (responsibleUserId) query.set("responsible_user_id", responsibleUserId);
  if (clientId) query.set("client_id", clientId);
  if (dealId) query.set("deal_id", dealId);
  return request(`/tasks?${query}`, accessToken, { signal });
}


export const createTask = (accessToken, payload) => request("/tasks", accessToken, { method: "POST", body: JSON.stringify(payload) });
export const updateTask = (accessToken, taskId, payload) => request(`/tasks/${taskId}`, accessToken, { method: "PATCH", body: JSON.stringify(payload) });
export const completeTask = (accessToken, taskId) => request(`/tasks/${taskId}/complete`, accessToken, { method: "POST" });
