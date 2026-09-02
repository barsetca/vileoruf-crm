import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import CommunicationTimeline from "./CommunicationTimeline.jsx";
import { createClient, getClient, listClients, updateClient } from "../services/clients.js";


const EMPTY_FORM = { name: "", contact_person: "", email: "", phone: "", telegram: "", whatsapp: "", company: "", lead_source: "", notes: "" };
const PAGE_SIZE = 10;
const FIELDS = ["name", "company", "contact_person", "email", "phone", "telegram", "whatsapp", "lead_source", "notes"];

function toPayload(form) {
  return Object.fromEntries(Object.entries(form).map(([field, value]) => [field, field === "name" ? value.trim() : value.trim() || null]));
}

function dateLabel(value, locale) {
  return new Intl.DateTimeFormat(locale, { year: "numeric", month: "short", day: "numeric" }).format(new Date(value));
}

function ClientForm({ form, onChange, error, submitting, onSubmit, submitLabel }) {
  const { t } = useTranslation();
  return <form className="client-form" onSubmit={onSubmit}>
    <div className="client-form-grid">
      {FIELDS.map((field) => <label className={field === "notes" ? "field field--full" : "field"} key={field}>
        <span>{t(`clients.fields.${field}`)}{field === "name" && <em aria-hidden="true"> *</em>}</span>
        {field === "notes" ? <textarea name={field} value={form[field]} onChange={onChange} rows="4" disabled={submitting} /> : <input name={field} type={field === "email" ? "email" : "text"} value={form[field]} onChange={onChange} disabled={submitting} required={field === "name"} />}
      </label>)}
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="primary-button" type="submit" disabled={submitting}>{submitLabel}</button>
  </form>;
}

function ClientsPage() {
  const { t, i18n } = useTranslation();
  const { accessToken, user } = useAuth();
  const [clients, setClients] = useState([]);
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState("loading");
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const load = useCallback((nextOffset = offset) => {
    const controller = new AbortController();
    setState("loading");
    listClients(accessToken, { limit: PAGE_SIZE, offset: nextOffset }, controller.signal)
      .then((data) => { setClients(data); setOffset(nextOffset); setState("ready"); })
      .catch((error) => { if (error.name !== "AbortError") setState("error"); });
    return controller;
  }, [accessToken, offset]);

  useEffect(() => {
    const controller = load(0);
    return () => controller.abort();
  }, [accessToken]); // Load only when the authenticated session changes.

  function openCreate() { setForm(EMPTY_FORM); setFormError(""); setModal({ mode: "create" }); }
  async function openEdit(clientId) {
    setModal({ mode: "loading" }); setFormError("");
    try {
      const client = await getClient(accessToken, clientId);
      setForm(Object.fromEntries(FIELDS.map((field) => [field, client[field] ?? ""])));
      setModal({ mode: "edit", client });
    } catch { setModal(null); setState("error"); }
  }
  function changeField(event) { setForm((previous) => ({ ...previous, [event.target.name]: event.target.value })); }
  async function submit(event) {
    event.preventDefault();
    if (!form.name.trim()) { setFormError(t("clients.validation.nameRequired")); return; }
    setIsSubmitting(true); setFormError("");
    try {
      if (modal.mode === "create") await createClient(accessToken, toPayload(form));
      else await updateClient(accessToken, modal.client.id, toPayload(form));
      setModal(null); load(modal.mode === "create" ? 0 : offset);
    } catch { setFormError(t("clients.errors.save")); }
    finally { setIsSubmitting(false); }
  }
  const locale = i18n.resolvedLanguage ?? "ru";

  return <>
    <section className="page-header">
      <div><p className="eyebrow">{t("crm.navigation.clients")}</p><h1>{t("clients.title")}</h1><p>{t("clients.subtitle")}</p></div>
      <button className="primary-button page-action" type="button" onClick={openCreate}>+ {t("clients.create")}</button>
    </section>
    <section className="content-surface clients-surface" aria-live="polite">
      {state === "loading" && <div className="state-panel"><span className="loading-spinner" aria-hidden="true" /><p>{t("clients.loading")}</p></div>}
      {state === "error" && <div className="state-panel"><p className="form-error">{t("clients.errors.load")}</p><button className="secondary-button" type="button" onClick={() => load(offset)}>{t("common.retry")}</button></div>}
      {state === "ready" && clients.length === 0 && <div className="state-panel"><h2>{t("clients.empty.title")}</h2><p>{t("clients.empty.description")}</p><button className="primary-button" type="button" onClick={openCreate}>{t("clients.empty.action")}</button></div>}
      {state === "ready" && clients.length > 0 && <>
        <div className="clients-table-wrap"><table className="clients-table"><thead><tr><th>{t("clients.fields.name")}</th><th>{t("clients.fields.company")}</th><th>{t("clients.fields.contact_person")}</th><th>{t("clients.fields.email")}</th><th>{t("clients.fields.phone")}</th><th>{t("clients.statusLabel")}</th><th>{t("clients.fields.lead_source")}</th><th>{t("clients.createdAt")}</th></tr></thead><tbody>{clients.map((client) => <tr key={client.id} tabIndex="0" onClick={() => openEdit(client.id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") openEdit(client.id); }}><td><strong>{client.name}</strong></td><td>{client.company || "—"}</td><td>{client.contact_person || "—"}</td><td>{client.email || "—"}</td><td>{client.phone || "—"}</td><td><span className={`status-badge status-badge--${client.status.toLowerCase()}`}>{t(`clients.status.${client.status}`)}</span></td><td>{client.lead_source || "—"}</td><td>{dateLabel(client.created_at, locale)}</td></tr>)}</tbody></table></div>
        <nav className="pagination" aria-label={t("clients.pagination.label")}><button className="secondary-button" type="button" disabled={offset === 0} onClick={() => load(Math.max(0, offset - PAGE_SIZE))}>{t("clients.pagination.previous")}</button><span>{t("clients.pagination.page", { page: Math.floor(offset / PAGE_SIZE) + 1 })}</span><button className="secondary-button" type="button" disabled={clients.length < PAGE_SIZE} onClick={() => load(offset + PAGE_SIZE)}>{t("clients.pagination.next")}</button></nav>
      </>}
    </section>
    {modal && <div className="modal-backdrop" role="presentation"><section className="client-modal" role="dialog" aria-modal="true" aria-labelledby="client-modal-title"><div className="modal-header"><div><p className="eyebrow">{modal.mode === "edit" ? t("clients.edit") : t("clients.create")}</p><h2 id="client-modal-title">{modal.mode === "edit" ? modal.client?.name : t("clients.create")}</h2></div><button className="icon-button" type="button" onClick={() => setModal(null)} aria-label={t("common.close")}>×</button></div>{modal.mode === "loading" ? <div className="state-panel"><span className="loading-spinner" /><p>{t("clients.loading")}</p></div> : <>{modal.mode === "edit" && <div className="readonly-status"><span>{t("clients.statusLabel")}</span><span className={`status-badge status-badge--${modal.client.status.toLowerCase()}`}>{t(`clients.status.${modal.client.status}`)}</span></div>}<ClientForm form={form} onChange={changeField} error={formError} submitting={isSubmitting} onSubmit={submit} submitLabel={t(isSubmitting ? "common.saving" : "common.save")} />{modal.mode === "edit" && <CommunicationTimeline clientId={modal.client.id} />}</>}</section></div>}
    {user.role === "ADMIN" && <p className="clients-permission-note">{t("clients.permissions.admin")}</p>}
  </>;
}


export default ClientsPage;
