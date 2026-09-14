import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ExternalLink, Pencil, X } from "lucide-react";

import { useAuth } from "../auth/AuthContext.jsx";
import { CalendarEventApiError, cancelCalendarEvent, listCalendarEvents } from "../services/calendarEvents.js";
import UpdateCalendarEventForm from "./UpdateCalendarEventForm.jsx";


const POLL_INTERVAL_MS = 2_500;
const MAX_PENDING_POLL_ATTEMPTS = 6;

export default function CalendarEventsSection({ clientId, dealId, taskId, refreshKey = 0 }) {
  const { t, i18n } = useTranslation();
  const { accessToken } = useAuth();
  const [state, setState] = useState("loading");
  const [items, setItems] = useState([]);
  const [updateEvent, setUpdateEvent] = useState(null);
  const [cancelEvent, setCancelEvent] = useState(null);
  const [cancelState, setCancelState] = useState("idle");
  const [cancelError, setCancelError] = useState("");
  const [updateRefreshKey, setUpdateRefreshKey] = useState(0);
  const [readRefreshKey, setReadRefreshKey] = useState(0);
  const attempts = useRef(0);
  const context = useMemo(() => ({ client_id: clientId, deal_id: dealId, task_id: taskId }), [clientId, dealId, taskId]);
  const contextKey = `${clientId ?? ""}:${dealId ?? ""}:${taskId ?? ""}`;
  const hasValidContext = [clientId, dealId, taskId].filter(Boolean).length === 1;
  const hasPending = items.some((event) => event.status === "PENDING");

  useEffect(() => {
    setUpdateEvent(null);
    setCancelEvent(null);
    setCancelState("idle");
    setCancelError("");
  }, [contextKey]);

  useEffect(() => {
    attempts.current = 0;
    if (!hasValidContext) {
      setItems([]);
      setState("ready");
      return undefined;
    }
    const controller = new AbortController();
    let active = true;
    setState("loading");
    listCalendarEvents(accessToken, context, controller.signal)
      .then((nextItems) => {
        if (active) {
          setItems(nextItems);
          setState("ready");
        }
      })
      .catch((error) => {
        if (active && error.name !== "AbortError") setState("error");
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [accessToken, context, contextKey, hasValidContext, refreshKey, updateRefreshKey, readRefreshKey]);

  useEffect(() => {
    if (!hasValidContext || state !== "ready" || !hasPending || attempts.current >= MAX_PENDING_POLL_ATTEMPTS) return undefined;
    let cancelled = false;
    let controller = null;
    const timer = window.setTimeout(() => {
      controller = new AbortController();
      attempts.current += 1;
      listCalendarEvents(accessToken, context, controller.signal)
        .then((nextItems) => {
          if (!cancelled) setItems(nextItems);
        })
        .catch((error) => {
          if (!cancelled && error.name !== "AbortError") setState("error");
        });
    }, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      controller?.abort();
    };
  }, [accessToken, context, contextKey, hasPending, hasValidContext, items, state]);

  const formatDateTime = (value) => new Intl.DateTimeFormat(i18n.resolvedLanguage || "ru", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  const beginCancel = (event) => {
    setCancelError("");
    setCancelEvent(event);
  };
  const confirmCancel = async () => {
    if (!cancelEvent || cancelState === "submitting") return;
    setCancelState("submitting");
    setCancelError("");
    try {
      const cancelled = await cancelCalendarEvent(accessToken, cancelEvent.id);
      setItems((current) => current.map((event) => event.id === cancelled.id ? cancelled : event));
      setCancelEvent(null);
      setCancelState("idle");
      setUpdateEvent(null);
      setUpdateRefreshKey((value) => value + 1);
    } catch (error) {
      setCancelState("idle");
      setCancelError(error instanceof CalendarEventApiError && error.status === 503 ? t("calendar.cancel.uncertain") : t("calendar.cancel.error"));
    }
  };

  return <section className="content-surface">
    <h3>{t("calendar.title")}</h3>
    {state === "loading" ? <p>{t("calendar.loading")}</p> : state === "error" ? <div className="state-panel"><p className="form-error">{t("calendar.error")}</p><button className="secondary-button" type="button" onClick={() => setReadRefreshKey((value) => value + 1)}>{t("common.retry")}</button></div> : items.length === 0 ? <p>{t("calendar.empty")}</p> : items.map((event) => <article key={event.id} data-testid={`calendar-event-${event.id}`}>
      <strong>{event.title}</strong>
      <p>{formatDateTime(event.start_at)} — {formatDateTime(event.end_at)} · {event.timezone}</p>
      <span className="status-note">{t(`calendar.status.${event.status}`)}</span>
      {event.description && <p>{event.description}</p>}
      {event.status === "SYNCED" && <div className="calendar-event-actions">
        {event.external_url && <a className="secondary-button" href={event.external_url} target="_blank" rel="noreferrer"><ExternalLink aria-hidden="true" size={16} />{t("calendar.open")}</a>}
        <button className="secondary-button" type="button" data-testid={`calendar-event-edit-${event.id}`} onClick={() => setUpdateEvent(event)}><Pencil aria-hidden="true" size={16} />{t("calendar.update.open")}</button>
        <button className="secondary-button" type="button" data-testid={`calendar-event-cancel-${event.id}`} disabled={cancelState === "submitting"} onClick={() => beginCancel(event)}><X aria-hidden="true" size={16} />{t("calendar.cancel.open")}</button>
      </div>}
      {cancelEvent?.id === event.id && <div className="form-grid" role="alertdialog" aria-live="polite" aria-label={t("calendar.cancel.title")} data-testid={`calendar-event-cancel-confirmation-${event.id}`}>
        <p className="field--full">{t("calendar.cancel.confirmation")}</p>
        {cancelError && <p className="form-error field--full" role="alert">{cancelError}</p>}
        <div className="deal-actions field--full">
          <button className="primary-button" type="button" data-testid={`calendar-event-cancel-confirm-${event.id}`} disabled={cancelState === "submitting"} onClick={confirmCancel}>{t(cancelState === "submitting" ? "calendar.cancel.submitting" : "calendar.cancel.confirm")}</button>
          <button className="secondary-button" type="button" disabled={cancelState === "submitting"} onClick={() => { setCancelEvent(null); setCancelError(""); }}>{t("common.close")}</button>
        </div>
      </div>}
    </article>)}
    {updateEvent && <UpdateCalendarEventForm event={updateEvent} onClose={() => setUpdateEvent(null)} onAccepted={() => { setUpdateEvent(null); setUpdateRefreshKey((value) => value + 1); }} />}
  </section>;
}
