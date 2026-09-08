import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import { createCalendarEvent } from "../services/calendarEvents.js";

export function localDateTimeValue(date) {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export function browserTimeZone() {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  return typeof timezone === "string" && timezone.trim() ? timezone : "";
}

export function initialCalendarEventForm() {
  const start = new Date();
  const end = new Date(start.getTime() + 60 * 60_000);
  return { title: "", description: "", startAt: localDateTimeValue(start), endAt: localDateTimeValue(end), timezone: browserTimeZone() };
}

export function calendarEventPayload(form, { clientId, dealId, taskId }) {
  return {
    title: form.title.trim(),
    description: form.description.trim() || null,
    start_at: new Date(form.startAt).toISOString(),
    end_at: new Date(form.endAt).toISOString(),
    timezone: form.timezone,
    ...(clientId ? { client_id: clientId } : {}),
    ...(dealId ? { deal_id: dealId } : {}),
    ...(taskId ? { task_id: taskId } : {}),
  };
}

function nextRequestKey() {
  if (typeof crypto?.randomUUID !== "function") throw new Error("Browser crypto is unavailable");
  return crypto.randomUUID();
}

export default function CreateCalendarEventForm({ clientId, dealId, taskId, onAccepted, onClose }) {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [form, setForm] = useState(initialCalendarEventForm);
  const [formError, setFormError] = useState("");
  const [state, setState] = useState("idle");
  const submission = useRef(null);

  function changeField(event) {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
  }

  function validate() {
    if (!form.title.trim()) return "calendar.create.validation.title";
    if (!form.startAt) return "calendar.create.validation.start";
    if (!form.endAt) return "calendar.create.validation.end";
    if (!form.timezone) return "calendar.create.validation.timezone";
    const start = new Date(form.startAt);
    const end = new Date(form.endAt);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end <= start) return "calendar.create.validation.range";
    return null;
  }

  async function submit(event) {
    event.preventDefault();
    const validationKey = validate();
    if (validationKey) { setFormError(t(validationKey)); return; }
    const payload = calendarEventPayload(form, { clientId, dealId, taskId });
    const fingerprint = JSON.stringify(payload);
    const requestKey = submission.current?.fingerprint === fingerprint ? submission.current.key : nextRequestKey();
    submission.current = { fingerprint, key: requestKey };
    setState("submitting"); setFormError("");
    try {
      const accepted = await createCalendarEvent(accessToken, payload, requestKey);
      submission.current = null;
      setForm(initialCalendarEventForm());
      setState("accepted");
      onAccepted?.(accepted);
    } catch {
      setState("idle");
      setFormError(t("calendar.create.error"));
    }
  }

  return <form className="communication-form" onSubmit={submit}>
    <h3>{t("calendar.create.title")}</h3>
    <div className="client-form-grid">
      <label className="field field--full"><span>{t("calendar.create.fields.title")} <em aria-hidden="true">*</em></span><input name="title" value={form.title} onChange={changeField} disabled={state === "submitting"} required /></label>
      <label className="field field--full"><span>{t("calendar.create.fields.description")}</span><textarea name="description" value={form.description} onChange={changeField} rows="3" disabled={state === "submitting"} /></label>
      <label className="field"><span>{t("calendar.create.fields.start")}</span><input name="startAt" type="datetime-local" value={form.startAt} onChange={changeField} disabled={state === "submitting"} required /></label>
      <label className="field"><span>{t("calendar.create.fields.end")}</span><input name="endAt" type="datetime-local" value={form.endAt} onChange={changeField} disabled={state === "submitting"} required /></label>
      <label className="field field--full"><span>{t("calendar.create.fields.timezone")}</span><input value={form.timezone} disabled /></label>
    </div>
    {formError && <p className="form-error" role="alert">{formError}</p>}
    {state === "accepted" && <p className="status-note">{t("calendar.create.accepted")}</p>}
    <div className="deal-actions"><button className="primary-button" type="submit" disabled={state === "submitting"}>{t(state === "submitting" ? "calendar.create.submitting" : "calendar.create.submit")}</button>{onClose && <button className="secondary-button" type="button" onClick={onClose} disabled={state === "submitting"}>{t("calendar.create.close")}</button>}</div>
  </form>;
}
