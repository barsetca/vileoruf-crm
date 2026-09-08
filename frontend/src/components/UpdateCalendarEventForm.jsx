import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import { localDateTimeValue } from "./CreateCalendarEventForm.jsx";
import { CalendarEventApiError, updateCalendarEvent } from "../services/calendarEvents.js";


export function initialCalendarEventUpdateForm(event) {
  return {
    title: event.title,
    description: event.description ?? "",
    startAt: localDateTimeValue(new Date(event.start_at)),
    endAt: localDateTimeValue(new Date(event.end_at)),
    timezone: event.timezone,
  };
}

export function calendarEventUpdatePayload(form) {
  return {
    title: form.title.trim(),
    description: form.description.trim() || null,
    start_at: new Date(form.startAt).toISOString(),
    end_at: new Date(form.endAt).toISOString(),
    timezone: form.timezone.trim(),
  };
}

export default function UpdateCalendarEventForm({ event, onAccepted, onClose }) {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [form, setForm] = useState(() => initialCalendarEventUpdateForm(event));
  const [formError, setFormError] = useState("");
  const [state, setState] = useState("idle");

  function changeField(input) {
    setForm((previous) => ({ ...previous, [input.target.name]: input.target.value }));
  }

  function validate() {
    if (!form.title.trim()) return "calendar.create.validation.title";
    if (!form.startAt) return "calendar.create.validation.start";
    if (!form.endAt) return "calendar.create.validation.end";
    if (!form.timezone.trim()) return "calendar.create.validation.timezone";
    try {
      Intl.DateTimeFormat(undefined, { timeZone: form.timezone.trim() });
    } catch {
      return "calendar.create.validation.timezone";
    }
    const start = new Date(form.startAt);
    const end = new Date(form.endAt);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end <= start) return "calendar.create.validation.range";
    return null;
  }

  async function submit(input) {
    input.preventDefault();
    const validationKey = validate();
    if (validationKey) {
      setFormError(t(validationKey));
      return;
    }
    setState("submitting");
    setFormError("");
    try {
      const accepted = await updateCalendarEvent(accessToken, event.id, calendarEventUpdatePayload(form));
      setForm(initialCalendarEventUpdateForm(event));
      setState("accepted");
      onAccepted?.(accepted);
    } catch (error) {
      setState("idle");
      setFormError(t(error instanceof CalendarEventApiError && error.status === 409 ? "calendar.update.conflict" : "calendar.update.error"));
    }
  }

  return <form className="communication-form" data-testid="calendar-event-update-form" onSubmit={submit}>
    <h3>{t("calendar.update.title")}</h3>
    <div className="client-form-grid">
      <label className="field field--full"><span>{t("calendar.create.fields.title")} <em aria-hidden="true">*</em></span><input name="title" data-testid="calendar-event-update-title" value={form.title} onChange={changeField} disabled={state === "submitting"} required /></label>
      <label className="field field--full"><span>{t("calendar.create.fields.description")}</span><textarea name="description" data-testid="calendar-event-update-description" value={form.description} onChange={changeField} rows="3" disabled={state === "submitting"} /></label>
      <label className="field"><span>{t("calendar.create.fields.start")}</span><input name="startAt" data-testid="calendar-event-update-start" type="datetime-local" value={form.startAt} onChange={changeField} disabled={state === "submitting"} required /></label>
      <label className="field"><span>{t("calendar.create.fields.end")}</span><input name="endAt" data-testid="calendar-event-update-end" type="datetime-local" value={form.endAt} onChange={changeField} disabled={state === "submitting"} required /></label>
      <label className="field field--full"><span>{t("calendar.create.fields.timezone")}</span><input name="timezone" data-testid="calendar-event-update-timezone" value={form.timezone} onChange={changeField} disabled={state === "submitting"} required /></label>
    </div>
    {formError && <p className="form-error" role="alert">{formError}</p>}
    <div className="deal-actions"><button className="primary-button" type="submit" data-testid="calendar-event-update-submit" disabled={state === "submitting"}>{t(state === "submitting" ? "calendar.update.submitting" : "calendar.update.submit")}</button>{onClose && <button className="secondary-button" type="button" onClick={onClose} disabled={state === "submitting"}>{t("calendar.create.close")}</button>}</div>
  </form>;
}
