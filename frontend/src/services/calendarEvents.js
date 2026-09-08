import { requireApiBaseUrl } from "./api.js";

export class CalendarEventApiError extends Error {
  constructor(status, detail) {
    super(`Calendar event request failed with ${status}`);
    this.name = "CalendarEventApiError";
    this.status = status;
    this.detail = detail;
  }
}

export async function listCalendarEvents(token, context, signal) { const q=new URLSearchParams({limit:"10",offset:"0"}); Object.entries(context).forEach(([k,v])=>v&&q.set(k,v)); const r=await fetch(`${requireApiBaseUrl()}/calendar-events?${q}`,{signal,headers:{Authorization:`Bearer ${token}`}}); const b=await r.json().catch(()=>null); if(!r.ok) throw new Error(b?.detail||"Calendar events request failed"); return b; }

export async function createCalendarEvent(accessToken, payload, idempotencyKey) {
  const response = await fetch(`${requireApiBaseUrl()}/calendar-events`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new CalendarEventApiError(response.status, body?.detail);
  return body;
}

export async function updateCalendarEvent(accessToken, eventId, payload) {
  const response = await fetch(`${requireApiBaseUrl()}/calendar-events/${eventId}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new CalendarEventApiError(response.status, body?.detail);
  return body;
}

export async function cancelCalendarEvent(accessToken, eventId) {
  const response = await fetch(`${requireApiBaseUrl()}/calendar-events/${eventId}/cancel`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new CalendarEventApiError(response.status, body?.detail);
  return body;
}
