import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { CalendarDays, Mail, MessageCircle } from "lucide-react";

import { useAuth } from "../auth/AuthContext.jsx";
import CommunicationTimeline from "./CommunicationTimeline.jsx";
import CalendarEventsDialogContent from "./CalendarEventsDialogContent.jsx";
import {
  archiveClient,
  createClient,
  getClient,
  listClients,
  restoreClient,
  updateClient,
} from "../services/clients.js";

const EMPTY_FORM = {
  name: "",
  contact_person: "",
  email: "",
  phone: "",
  telegram: "",
  whatsapp: "",
  company: "",
  lead_source: "",
  notes: "",
  preferred_communication_language: "RU",
};
const PAGE_SIZE = 10;
const FIELDS = [
  "name",
  "company",
  "contact_person",
  "email",
  "phone",
  "telegram",
  "whatsapp",
  "lead_source",
  "preferred_communication_language",
  "notes",
];

function toPayload(form) {
  return Object.fromEntries(
    Object.entries(form).map(([field, value]) => [
      field,
      field === "name" ? value.trim() : value.trim() || null,
    ]),
  );
}

function dateLabel(value, locale) {
  return new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}

function ClientForm({
  form,
  onChange,
  error,
  submitting,
  onSubmit,
  submitLabel,
  operationalActions,
}) {
  const { t } = useTranslation();
  return (
    <form className="client-form" onSubmit={onSubmit}>
      <div className="client-form-grid">
        {FIELDS.map((field) => (
          <label
            className={field === "notes" ? "field field--full" : "field"}
            key={field}
          >
            <span>
              {field === "preferred_communication_language"
                ? t("d4.preferredCommunicationLanguage")
                : t(`clients.fields.${field}`)}
              {field === "name" && <em aria-hidden="true"> *</em>}
            </span>
            {field === "notes" ? (
              <textarea
                name={field}
                value={form[field]}
                onChange={onChange}
                rows="4"
                disabled={submitting}
              />
            ) : field === "preferred_communication_language" ? (
              <select
                name={field}
                value={form[field]}
                onChange={onChange}
                disabled={submitting}
              >
                {["RU", "EN", "ES"].map((language) => (
                  <option key={language}>{language}</option>
                ))}
              </select>
            ) : (
              <input
                name={field}
                type={field === "email" ? "email" : "text"}
                value={form[field]}
                onChange={onChange}
                disabled={submitting}
                required={field === "name"}
              />
            )}
          </label>
        ))}
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="client-actions">
        <button className="primary-button" type="submit" disabled={submitting}>
          {submitLabel}
        </button>
        {operationalActions}
      </div>
    </form>
  );
}

function ClientRelatedDialog({ view, client, refreshKey, showCalendarCreate, setShowCalendarCreate, onCalendarAccepted, onClose }) {
  const { t } = useTranslation();
  if (!view) return null;

  return (
    <div className="modal-backdrop client-related-backdrop" role="presentation">
      <section className="client-modal client-related-modal" role="dialog" aria-modal="true" aria-labelledby="client-related-title">
        <div className="modal-header">
          <h2 id="client-related-title">{view === "events" ? t("dealRelated.calendar") : t(`clientRelated.${view}`)}</h2>
          <button className="icon-button" type="button" onClick={onClose} aria-label={t("common.close")}>×</button>
        </div>
        {view === "communications" && <CommunicationTimeline clientId={client.id} />}
        {view === "events" && <CalendarEventsDialogContent clientId={client.id} refreshKey={refreshKey} showCreate={showCalendarCreate} setShowCreate={setShowCalendarCreate} onAccepted={onCalendarAccepted} />}
        {view === "email" && <div className="state-panel client-email-unavailable"><p>{t("clientRelated.emailUnavailable")}</p></div>}
      </section>
    </div>
  );
}

function ClientsPage({ initialClientId = null }) {
  const { t, i18n } = useTranslation();
  const { accessToken, user } = useAuth();
  const [clients, setClients] = useState([]);
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState("loading");
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showCalendarCreate, setShowCalendarCreate] = useState(false);
  const [calendarRefreshKey, setCalendarRefreshKey] = useState(0);
  const [relatedView, setRelatedView] = useState(null);
  const [archived, setArchived] = useState(false);
  const [confirmArchive, setConfirmArchive] = useState(false);

  const load = useCallback(
    (nextOffset = offset) => {
      const controller = new AbortController();
      setState("loading");
      listClients(
        accessToken,
        { limit: PAGE_SIZE, offset: nextOffset, archived },
        controller.signal,
      )
        .then((data) => {
          setClients(data);
          setOffset(nextOffset);
          setState("ready");
        })
        .catch((error) => {
          if (error.name !== "AbortError") setState("error");
        });
      return controller;
    },
    [accessToken, offset, archived],
  );

  useEffect(() => {
    const controller = load(0);
    return () => controller.abort();
  }, [accessToken, archived]); // Reload when the authenticated view changes.

  useEffect(() => {
    if (initialClientId) openEdit(initialClientId);
  }, [initialClientId]);

  function openCreate() {
    setForm(EMPTY_FORM);
    setFormError("");
    setRelatedView(null);
    setModal({ mode: "create" });
  }
  async function openEdit(clientId) {
    setModal({ mode: "loading" });
    setFormError("");
    try {
      const client = await getClient(accessToken, clientId);
      setForm(
        Object.fromEntries(FIELDS.map((field) => [field, client[field] ?? ""])),
      );
      setShowCalendarCreate(false);
      setRelatedView(null);
      setModal({ mode: "edit", client });
    } catch {
      setModal(null);
      setState("error");
    }
  }
  function changeField(event) {
    setForm((previous) => ({
      ...previous,
      [event.target.name]: event.target.value,
    }));
  }
  async function submit(event) {
    event.preventDefault();
    if (!form.name.trim()) {
      setFormError(t("clients.validation.nameRequired"));
      return;
    }
    setIsSubmitting(true);
    setFormError("");
    try {
      if (modal.mode === "create")
        await createClient(accessToken, toPayload(form));
      else await updateClient(accessToken, modal.client.id, toPayload(form));
      setModal(null);
      load(modal.mode === "create" ? 0 : offset);
    } catch {
      setFormError(t("clients.errors.save"));
    } finally {
      setIsSubmitting(false);
    }
  }
  async function changeArchive() {
    if (!modal?.client) return;
    setIsSubmitting(true);
    setFormError("");
    try {
      await (modal.client.archived_at
        ? restoreClient(accessToken, modal.client.id)
        : archiveClient(accessToken, modal.client.id));
      setConfirmArchive(false);
      setModal(null);
      load(0);
    } catch {
      setFormError(t("archive.error"));
    } finally {
      setIsSubmitting(false);
    }
  }
  const locale = i18n.resolvedLanguage ?? "ru";

  const archiveAction = modal?.mode === "edit" && user.role === "ADMIN" && (
    confirmArchive ? (
      <div className="warning-box" role="alert">
        <p>{t(modal.client.archived_at ? "archive.restoreConfirmClient" : "archive.confirmClient")}</p>
        <div className="client-actions">
          <button className="primary-button" type="button" disabled={isSubmitting} onClick={changeArchive}>{t(modal.client.archived_at ? "archive.restore" : "archive.confirm")}</button>
          <button className="secondary-button" type="button" disabled={isSubmitting} onClick={() => setConfirmArchive(false)}>{t("common.cancel")}</button>
        </div>
      </div>
    ) : (
      <button className="secondary-button" type="button" disabled={isSubmitting} onClick={() => setConfirmArchive(true)}>{t(modal.client.archived_at ? "archive.restoreClient" : "archive.archiveClient")}</button>
    )
  );

  return (
    <>
      <section className="page-header">
        <div>
          <p className="eyebrow">{t("crm.navigation.clients")}</p>
          <h1>{t("clients.title")}</h1>
          <p>{t("clients.subtitle")}</p>
        </div>
        <div className="page-actions">
          {user.role === "ADMIN" && (
            <div className="client-archive-toggle">
              <button
                className={`secondary-button ${!archived ? "is-selected" : ""}`}
                type="button"
                aria-pressed={!archived}
                onClick={() => setArchived(false)}
              >
                {t("archive.active")}
              </button>
              <button
                className={`secondary-button ${archived ? "is-selected" : ""}`}
                type="button"
                aria-pressed={archived}
                onClick={() => setArchived(true)}
              >
                {t("archive.archived")}
              </button>
            </div>
          )}
          <button
            className="primary-button page-action"
            type="button"
            onClick={openCreate}
          >
            + {t("clients.create")}
          </button>
        </div>
      </section>
      <section className="content-surface clients-surface" aria-live="polite">
        {state === "loading" && (
          <div className="state-panel">
            <span className="loading-spinner" aria-hidden="true" />
            <p>{t("clients.loading")}</p>
          </div>
        )}
        {state === "error" && (
          <div className="state-panel">
            <p className="form-error">{t("clients.errors.load")}</p>
            <button
              className="secondary-button"
              type="button"
              onClick={() => load(offset)}
            >
              {t("common.retry")}
            </button>
          </div>
        )}
        {state === "ready" && clients.length === 0 && (
          <div className="state-panel">
            <h2>{t("clients.empty.title")}</h2>
            <p>{t("clients.empty.description")}</p>
            <button
              className="primary-button"
              type="button"
              onClick={openCreate}
            >
              {t("clients.empty.action")}
            </button>
          </div>
        )}
        {state === "ready" && clients.length > 0 && (
          <>
            <div className="clients-table-wrap">
              <table className="clients-table">
                <thead>
                  <tr>
                    <th>{t("clients.fields.name")}</th>
                    <th>{t("clients.fields.company")}</th>
                    <th>{t("clients.fields.contact_person")}</th>
                    <th>{t("clients.fields.email")}</th>
                    <th>{t("clients.fields.phone")}</th>
                    <th>{t("clients.statusLabel")}</th>
                    <th>{t("clients.fields.lead_source")}</th>
                    <th>{t("clients.createdAt")}</th>
                  </tr>
                </thead>
                <tbody>
                  {clients.map((client) => (
                    <tr
                      key={client.id}
                      tabIndex="0"
                      onClick={() => openEdit(client.id)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ")
                          openEdit(client.id);
                      }}
                    >
                      <td>
                        <strong>{client.name}</strong>
                      </td>
                      <td>{client.company || "—"}</td>
                      <td>{client.contact_person || "—"}</td>
                      <td>{client.email || "—"}</td>
                      <td>{client.phone || "—"}</td>
                      <td>
                        <span
                          className={`status-badge status-badge--${client.status.toLowerCase()}`}
                        >
                          {t(`clients.status.${client.status}`)}
                        </span>
                      </td>
                      <td>{client.lead_source || "—"}</td>
                      <td>{dateLabel(client.created_at, locale)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <nav
              className="pagination"
              aria-label={t("clients.pagination.label")}
            >
              <button
                className="secondary-button"
                type="button"
                disabled={offset === 0}
                onClick={() => load(Math.max(0, offset - PAGE_SIZE))}
              >
                {t("clients.pagination.previous")}
              </button>
              <span>
                {t("clients.pagination.page", {
                  page: Math.floor(offset / PAGE_SIZE) + 1,
                })}
              </span>
              <button
                className="secondary-button"
                type="button"
                disabled={clients.length < PAGE_SIZE}
                onClick={() => load(offset + PAGE_SIZE)}
              >
                {t("clients.pagination.next")}
              </button>
            </nav>
          </>
        )}
      </section>
      {modal && (
        <div className="modal-backdrop" role="presentation">
          <section
            className="client-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="client-modal-title"
          >
            <div className="modal-header">
              <div>
                <p className="eyebrow">
                  {modal.mode === "edit"
                    ? t("clients.edit")
                    : t("clients.create")}
                </p>
                <h2 id="client-modal-title">
                  {modal.mode === "edit"
                    ? modal.client?.name
                    : t("clients.create")}
                </h2>
              </div>
              <button
                className="icon-button"
                type="button"
                onClick={() => setModal(null)}
                aria-label={t("common.close")}
              >
                ×
              </button>
            </div>
            {modal.mode === "loading" ? (
              <div className="state-panel">
                <span className="loading-spinner" />
                <p>{t("clients.loading")}</p>
              </div>
            ) : (
              <>
                {modal.mode === "edit" && (
                  <div className="readonly-status">
                    <span>{t("clients.statusLabel")}</span>
                    <span
                      className={`status-badge status-badge--${modal.client.status.toLowerCase()}`}
                    >
                      {t(`clients.status.${modal.client.status}`)}
                    </span>
                  </div>
                )}
                <ClientForm
                  form={form}
                  onChange={changeField}
                  error={formError}
                  submitting={isSubmitting}
                  onSubmit={submit}
                  submitLabel={t(
                    isSubmitting ? "common.saving" : "common.save",
                  )}
                  operationalActions={archiveAction}
                />
                {modal.mode === "edit" && (
                  <div className="client-actions client-actions--related">
                    <button className="secondary-button" type="button" onClick={() => setRelatedView("communications")}><MessageCircle aria-hidden="true" size={18} />{t("clientRelated.communications")}</button>
                    <button className="secondary-button" type="button" onClick={() => setRelatedView("email")}><Mail aria-hidden="true" size={18} />{t("clientRelated.email")}</button>
                    <button className="secondary-button" type="button" onClick={() => setRelatedView("events")}><CalendarDays aria-hidden="true" size={18} />{t("dealRelated.calendar")}</button>
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      )}
      {modal?.mode === "edit" && <ClientRelatedDialog view={relatedView} client={modal.client} refreshKey={calendarRefreshKey} showCalendarCreate={showCalendarCreate} setShowCalendarCreate={setShowCalendarCreate} onCalendarAccepted={() => { setShowCalendarCreate(false); setCalendarRefreshKey((value) => value + 1); }} onClose={() => { setRelatedView(null); setShowCalendarCreate(false); }} />}
      {user.role === "ADMIN" && (
        <p className="clients-permission-note">
          {t("clients.permissions.admin")}
        </p>
      )}
    </>
  );
}

export default ClientsPage;
