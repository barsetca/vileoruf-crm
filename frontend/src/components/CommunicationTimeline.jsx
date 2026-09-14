import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import {
  CommunicationApiError,
  createCommunication,
  assignCommunicationDeal,
  detachCommunicationDeal,
  listCommunications,
  markCommunicationRead,
} from "../services/communications.js";
import { listDeals } from "../services/deals.js";
import { sendTelegram } from "../services/integrations.js";
import { getClient } from "../services/clients.js";
import { getTelegramAvailability } from "../services/integrations.js";


const PAGE_SIZE = 10;
const CHANNELS = ["EMAIL", "TELEGRAM", "WHATSAPP", "MANUAL", "OTHER"];
const DIRECTIONS = ["INCOMING", "OUTGOING"];

function currentLocalDateTime() {
  const date = new Date();
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function initialForm() {
  return {
    channel: "MANUAL",
    direction: "OUTGOING",
    content: "",
    occurredAt: currentLocalDateTime(),
  };
}

function formatDateTime(value, locale) {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function CommunicationTimeline({ clientId, dealId = null, canCreate = true }) {
  const { t, i18n } = useTranslation();
  const { accessToken } = useAuth();
  const [communications, setCommunications] = useState([]);
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState("loading");
  const [form, setForm] = useState(initialForm);
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [telegramText, setTelegramText] = useState("");
  const [telegramRequestKey, setTelegramRequestKey] = useState(null);
  const [telegramState, setTelegramState] = useState("idle");
  const [telegramAvailable, setTelegramAvailable] = useState(false);
  const [clientDeals, setClientDeals] = useState([]);
  const [assigning, setAssigning] = useState({});

  useEffect(() => {
    let active = true;
    setTelegramAvailable(false);
    Promise.all([getClient(accessToken, clientId), getTelegramAvailability(accessToken)])
      .then(([client, integration]) => { if (active) setTelegramAvailable(Boolean(client.telegram_provider_user_id) && integration.available === true); })
      .catch(() => { if (active) setTelegramAvailable(false); });
    return () => { active = false; };
  }, [accessToken, clientId]);

  useEffect(() => {
    if (dealId) return;
    const controller = new AbortController();
    listDeals(accessToken, { limit: 100, offset: 0 }, controller.signal)
      .then((items) => setClientDeals(items.filter((item) => item.client_id === clientId)))
      .catch(() => setClientDeals([]));
    return () => controller.abort();
  }, [accessToken, clientId, dealId]);

  const load = useCallback((nextOffset = 0, append = false) => {
    const controller = new AbortController();
    setState(append ? "loading-more" : "loading");
    listCommunications(
      accessToken,
      { limit: PAGE_SIZE, offset: nextOffset, clientId, dealId },
      controller.signal,
    ).then((data) => {
      setCommunications((previous) => append ? [...previous, ...data] : data);
      setOffset(nextOffset);
      setState("ready");
    }).catch((error) => {
      if (error.name !== "AbortError") setState("error");
    });
    return controller;
  }, [accessToken, clientId, dealId]);

  useEffect(() => {
    const controller = load();
    return () => controller.abort();
  }, [load]);

  function changeField(event) {
    setForm((previous) => ({ ...previous, [event.target.name]: event.target.value }));
  }
  async function submitTelegram(event) { event.preventDefault(); if (!telegramText.trim()) return; const requestKey=telegramRequestKey ?? crypto.randomUUID(); setTelegramRequestKey(requestKey); setTelegramState("sending"); try { await sendTelegram(accessToken, { client_id: clientId, ...(dealId ? { deal_id: dealId } : {}), content: telegramText.trim() }, requestKey); setTelegramText(""); setTelegramRequestKey(null); setTelegramState("pending"); } catch { setTelegramState("error"); } }

  async function submit(event) {
    event.preventDefault();
    if (!form.content.trim()) {
      setFormError(t("communications.validation.contentRequired"));
      return;
    }
    setIsSubmitting(true);
    setFormError("");
    try {
      await createCommunication(accessToken, {
        client_id: clientId,
        ...(dealId ? { deal_id: dealId } : {}),
        channel: form.channel,
        direction: form.direction,
        content: form.content.trim(),
        occurred_at: new Date(form.occurredAt).toISOString(),
      });
      setForm(initialForm());
      load();
    } catch (error) {
      if (error instanceof CommunicationApiError && error.status === 403) {
        setFormError(t("communications.errors.forbidden"));
      } else if (error instanceof CommunicationApiError && error.status === 404) {
        setFormError(t("communications.errors.contextMissing"));
      } else if (error instanceof CommunicationApiError && error.status === 422) {
        setFormError(t("communications.errors.validation"));
      } else {
        setFormError(t("communications.errors.save"));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function action(communication, type, targetDealId = null) {
    setAssigning((previous) => ({ ...previous, [communication.id]: type }));
    try {
      if (type === "read") await markCommunicationRead(accessToken, communication.id);
      if (type === "assign") await assignCommunicationDeal(accessToken, communication.id, targetDealId);
      if (type === "detach") await detachCommunicationDeal(accessToken, communication.id);
      load();
    } catch { setFormError(t("p1_7.actionError")); }
    finally { setAssigning((previous) => ({ ...previous, [communication.id]: "" })); }
  }

  const locale = i18n.resolvedLanguage ?? "ru";
  const hasMore = communications.length > 0 && communications.length % PAGE_SIZE === 0;
  const telegramSendAvailable = telegramAvailable && canCreate;

  return <section className="communication-timeline" aria-live="polite">
    {canCreate ? <form className="communication-form" onSubmit={submit}>
      <h3>{t("communications.create")}</h3>
      <div className="client-form-grid">
        <label className="field"><span>{t("communications.fields.channel")}</span><select name="channel" value={form.channel} onChange={changeField} disabled={isSubmitting}>{CHANNELS.map((channel) => <option key={channel} value={channel}>{t(`communications.channels.${channel}`)}</option>)}</select></label>
        <label className="field"><span>{t("communications.fields.direction")}</span><select name="direction" value={form.direction} onChange={changeField} disabled={isSubmitting}>{DIRECTIONS.map((direction) => <option key={direction} value={direction}>{t(`communications.directions.${direction}`)}</option>)}</select></label>
        <label className="field"><span>{t("communications.fields.occurredAt")}</span><input name="occurredAt" type="datetime-local" value={form.occurredAt} onChange={changeField} disabled={isSubmitting} required /></label>
        <label className="field field--full"><span>{t("communications.fields.content")} <em aria-hidden="true">*</em></span><textarea name="content" value={form.content} onChange={changeField} rows="3" disabled={isSubmitting} required /></label>
      </div>
      {formError && <p className="form-error" role="alert">{formError}</p>}
      <button className="primary-button" type="submit" disabled={isSubmitting}>{t(isSubmitting ? "common.saving" : "communications.submit")}</button>
    </form> : <p className="readonly-note">{t("communications.permissions.dealCreateForbidden")}</p>}
    {telegramSendAvailable ? <form className="communication-form" onSubmit={submitTelegram}><h3>{t("telegram.send")}</h3><label className="field field--full"><span>{t("telegram.message")}</span><textarea value={telegramText} onChange={(event) => { setTelegramText(event.target.value); setTelegramRequestKey(null); }} rows="3" disabled={telegramState === "sending"} required /></label>{telegramState === "pending" && <p className="status-note">{t("telegram.pending")}</p>}{telegramState === "error" && <p className="form-error">{t("telegram.error")}</p>}<button className="secondary-button" disabled={telegramState === "sending"}>{t(telegramState === "sending" ? "telegram.sending" : "telegram.send")}</button></form> : <p className="readonly-note">{t("telegram.unavailable")}</p>}
    <div className="communication-history">
      <div className="communication-timeline-header">
        <div><h3>{t("communications.title")}</h3><p>{t(dealId ? "communications.dealSubtitle" : "communications.clientSubtitle")}</p></div>
      </div>
      {state === "loading" && <div className="timeline-state"><span className="loading-spinner" aria-hidden="true" /><p>{t("communications.loading")}</p></div>}
      {state === "error" && <div className="timeline-state"><p className="form-error">{t("communications.errors.load")}</p><button className="secondary-button" type="button" onClick={() => load()}>{t("common.retry")}</button></div>}
      {state === "ready" && communications.length === 0 && <div className="timeline-state"><p>{t("communications.empty")}</p></div>}
      {state !== "loading" && state !== "error" && communications.length > 0 && <ol className="communication-list">{communications.map((communication) => <li key={communication.id} className="communication-item"><div className="communication-item-meta"><span className="stage-badge">{t(`communications.channels.${communication.channel}`)}</span><span>{t(`communications.directions.${communication.direction}`)}</span><time dateTime={communication.occurred_at}>{formatDateTime(communication.occurred_at, locale)}</time></div><p>{communication.content}</p>{communication.direction === "INCOMING" && <div className="button-group">{communication.read_at ? <span className="readonly-note">✓ {t("p1_7.read")}</span> : <button className="secondary-button" type="button" disabled={assigning[communication.id]} onClick={() => action(communication, "read")}>{t("p1_7.read")}</button>}{dealId ? <button className="secondary-button" type="button" disabled={assigning[communication.id]} onClick={() => action(communication, "detach")}>{t("p1_7.detach")}</button> : communication.deal_id ? <button className="secondary-button" type="button" disabled={assigning[communication.id]} onClick={() => action(communication, "detach")}>{t("p1_7.detach")}</button> : <label className="field"><span>{t("p1_7.assign")}</span><select defaultValue="" disabled={assigning[communication.id]} onChange={(event) => { if (event.target.value) action(communication, "assign", event.target.value); }}><option value="">{t("p1_7.dealPlaceholder")}</option>{clientDeals.map((deal) => <option key={deal.id} value={deal.id}>{deal.name}</option>)}</select></label>}</div>}</li>)}</ol>}
      {state !== "error" && hasMore && <button className="secondary-button timeline-load-more" type="button" disabled={state === "loading-more"} onClick={() => load(offset + PAGE_SIZE, true)}>{t(state === "loading-more" ? "communications.loadingMore" : "communications.loadMore")}</button>}
    </div>
  </section>;
}


export default CommunicationTimeline;
