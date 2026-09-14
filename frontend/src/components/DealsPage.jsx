import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Archive,
  ArchiveRestore,
  CalendarDays,
  FileText,
  Mail,
  MessageCircle,
  Pencil,
} from "lucide-react";

import { useAuth } from "../auth/AuthContext.jsx";
import CommunicationTimeline from "./CommunicationTimeline.jsx";
import CalendarEventsDialogContent from "./CalendarEventsDialogContent.jsx";
import LeadScoringSection from "./LeadScoringSection.jsx";
import DealPredictionSection from "./DealPredictionSection.jsx";
import NextBestActionSection from "./NextBestActionSection.jsx";
import EmailDraftSection from "./EmailDraftSection.jsx";
import DealAIHistorySection from "./DealAIHistorySection.jsx";
import { listClients } from "../services/clients.js";
import {
  archiveDeal,
  createDeal,
  getDeal,
  getDealPublicRequest,
  listDeals,
  restoreDeal,
  transitionDeal,
  updateDeal,
} from "../services/deals.js";
import {
  listEmployeeReferences,
  listPipelineStages,
} from "../services/referenceData.js";
import { listCategories, listServices } from "../services/business.js";

const PAGE_SIZE = 10;
const EMPTY_FORM = {
  name: "",
  description: "",
  client_id: "",
  stage_id: "",
  service_id: "",
  estimated_budget: "",
  deadline: "",
  manager_effort_estimate: "",
  probability: "",
  responsible_user_id: "",
};

function stageKey(name) {
  return {
    "New Lead": "newLead",
    Contact: "contact",
    Qualification: "qualification",
    Proposal: "proposal",
    Negotiation: "negotiation",
    Won: "won",
    Lost: "lost",
  }[name];
}

function dateLabel(value, locale) {
  return value
    ? new Intl.DateTimeFormat(locale, {
        year: "numeric",
        month: "short",
        day: "numeric",
      }).format(new Date(`${value}T00:00:00`))
    : "—";
}

function moneyLabel(value, locale) {
  return value == null
    ? "—"
    : new Intl.NumberFormat(locale, {
        style: "currency",
        currency: "EUR",
      }).format(Number(value));
}

function percentLabel(value, locale) {
  return value == null
    ? "—"
    : new Intl.NumberFormat(locale, {
        style: "percent",
        maximumFractionDigits: 0,
      }).format(Number(value) / 100);
}

function scoreLabel(value, locale) {
  return value == null
    ? "—"
    : `${new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(
        Number(value),
      )}%`;
}

function DealForm({
  form,
  clients,
  stages,
  employees,
  services,
  categories,
  isAdmin,
  submitting,
  error,
  onChange,
  onSubmit,
  submitLabel,
  mode,
}) {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage ?? "ru";
  const activeEmployees = employees.filter((employee) => employee.is_active);
  return (
    <form className="client-form" onSubmit={onSubmit}>
      <div className="client-form-grid">
        <label className="field field--full">
          <span>
            {t("deals.fields.name")} <em aria-hidden="true">*</em>
          </span>
          <input
            name="name"
            value={form.name}
            onChange={onChange}
            disabled={submitting}
            required
          />
        </label>
        {mode === "create" ? (
          <label className="field">
            <span>
              {t("deals.fields.client")} <em aria-hidden="true">*</em>
            </span>
            <select
              name="client_id"
              value={form.client_id}
              onChange={onChange}
              disabled={submitting}
              required
            >
              <option value="">{t("deals.selectClient")}</option>
              {clients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <label className="field">
            <span>{t("deals.fields.client")}</span>
            <input value={form.client_name} disabled />
          </label>
        )}
        {mode === "create" ? (
          <label className="field">
            <span>
              {t("deals.fields.stage")} <em aria-hidden="true">*</em>
            </span>
            <select
              name="stage_id"
              value={form.stage_id}
              onChange={onChange}
              disabled={submitting}
              required
            >
              <option value="">{t("deals.selectStage")}</option>
              {stages.map((stage) => (
                <option key={stage.id} value={stage.id}>
                  {t(`deals.stages.${stageKey(stage.name)}`, {
                    defaultValue: stage.name,
                  })}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <label className="field">
            <span>{t("deals.fields.stage")}</span>
            <input value={form.stage_name} disabled />
          </label>
        )}
        <label className="field field--full">
          <span>{t("deals.fields.description")}</span>
          <textarea
            name="description"
            value={form.description}
            onChange={onChange}
            rows="3"
            disabled={submitting}
          />
        </label>
        <label className="field">
          <span>{t("d4.service")}</span>
          <select
            name="service_id"
            value={form.service_id}
            onChange={onChange}
            disabled={submitting}
            required
          >
            <option value="">{t("d4.selectService")}</option>
            {services
              .filter(
                (item) =>
                  (item.is_active &&
                    categories.find(
                      (category) => category.id === item.category_id,
                    )?.is_active) ||
                  item.id === form.service_id,
              )
              .map((item) => (
                <option key={item.id} value={item.id}>
                  {item[`name_${language}`] || item.name_ru}
                </option>
              ))}
          </select>
        </label>
        <label className="field">
          <span>{t("d4.category")}</span>
          <input
            value={(() => {
              const item = categories.find(
                (category) =>
                  category.id ===
                  services.find((service) => service.id === form.service_id)
                    ?.category_id,
              );
              return item?.[`name_${language}`] || item?.name_ru || "—";
            })()}
            disabled
          />
        </label>
        <label className="field">
          <span>{t("deals.fields.estimated_budget")}</span>
          <input
            name="estimated_budget"
            type="number"
            min="0"
            step="0.01"
            value={form.estimated_budget}
            onChange={onChange}
            disabled={submitting}
          />
        </label>
        <label className="field">
          <span>{t("deals.fields.deadline")}</span>
          <input
            name="deadline"
            type="date"
            value={form.deadline}
            onChange={onChange}
            disabled={submitting}
          />
        </label>
        <label className="field">
          <span>{t("d4.managerEffort")}</span>
          <input
            name="manager_effort_estimate"
            type="number"
            min="0.01"
            step="0.01"
            value={form.manager_effort_estimate}
            onChange={onChange}
            disabled={submitting}
          />
        </label>
        <label className="field">
          <span>{t("deals.fields.probability")}</span>
          <input
            name="probability"
            type="number"
            min="0"
            max="100"
            value={form.probability}
            onChange={onChange}
            disabled={submitting}
          />
        </label>
        {isAdmin && (
          <label className="field">
            <span>{t("deals.fields.responsible")}</span>
            <select
              name="responsible_user_id"
              value={form.responsible_user_id}
              onChange={onChange}
              disabled={submitting}
            >
              <option value="">{t("deals.unassigned")}</option>
              {activeEmployees.map((employee) => (
                <option key={employee.id} value={employee.id}>
                  {employee.display_name} ·{" "}
                  {t(`employees.roles.${employee.role}`)}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <button className="primary-button" type="submit" disabled={submitting}>
        {submitLabel}
      </button>
    </form>
  );
}

function RelatedDealDialog({ view, onClose, request, deal, client, canRun, refreshKey, showCalendarCreate, setShowCalendarCreate, onCalendarAccepted }) {
  const { t } = useTranslation();
  if (!view) return null;
  return <div className="modal-backdrop"><section className="client-modal" role="dialog" aria-modal="true"><div className="modal-header"><h2>{t(`dealRelated.${view}`)}</h2><button className="icon-button" type="button" onClick={onClose} aria-label={t("common.close")}>×</button></div>
    {view === "request" && (request === undefined ? <div className="state-panel">{t("common.loading")}</div> : request === null ? <div className="state-panel">{t("dealRelated.noRequest")}</div> : <dl className="deal-details">{["name","contact_person","company","email","phone","telegram","whatsapp","preferred_communication_language","deal_name","description","estimated_budget","deadline","created_at"].map((key)=><div key={key}><dt>{t(`dealRelated.fields.${key}`)}</dt><dd>{request[key] ?? "—"}</dd></div>)}</dl>)}
    {view === "communications" && <CommunicationTimeline clientId={deal.client_id} dealId={deal.id} canCreate={canRun}/>} {view === "email" && <EmailDraftSection deal={deal} client={client} canRun={canRun}/>} {view === "calendar" && <CalendarEventsDialogContent dealId={deal.id} canCreate={canRun} refreshKey={refreshKey} showCreate={showCalendarCreate} setShowCreate={setShowCalendarCreate} onAccepted={onCalendarAccepted}/>}</section></div>;
}

function DealsPage({ initialDealId }) {
  const { t, i18n } = useTranslation();
  const { accessToken, user } = useAuth();
  const [deals, setDeals] = useState([]);
  const [references, setReferences] = useState({
    clients: [],
    stages: [],
    employees: [],
    services: [],
    categories: [],
  });
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState("loading");
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showCalendarCreate, setShowCalendarCreate] = useState(false);
  const [calendarRefreshKey, setCalendarRefreshKey] = useState(0);
  const [archived, setArchived] = useState(false);
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [relatedView, setRelatedView] = useState(null);
  const [publicRequest, setPublicRequest] = useState(undefined);

  const load = useCallback(
    (nextOffset = offset) => {
      const controller = new AbortController();
      setState("loading");
      Promise.all([
        listDeals(
          accessToken,
          { limit: PAGE_SIZE, offset: nextOffset, archived },
          controller.signal,
        ),
        listClients(accessToken, { limit: 100, offset: 0 }, controller.signal),
        listPipelineStages(accessToken, controller.signal),
        listEmployeeReferences(accessToken, controller.signal),
        listServices(accessToken, controller.signal),
        listCategories(accessToken, controller.signal),
      ])
        .then(
          ([nextDeals, clients, stages, employees, services, categories]) => {
            setDeals(nextDeals);
            setReferences({ clients, stages, employees, services, categories });
            setOffset(nextOffset);
            setState("ready");
          },
        )
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
  }, [accessToken, archived]);

  useEffect(() => {
    if (initialDealId) openDetail(initialDealId);
  }, [initialDealId]);

  const lookups = useMemo(
    () => ({
      clients: new Map(references.clients.map((item) => [item.id, item])),
      stages: new Map(references.stages.map((item) => [item.id, item])),
      employees: new Map(references.employees.map((item) => [item.id, item])),
    }),
    [references],
  );
  const stageLabel = (stageId) => {
    const stage = lookups.stages.get(stageId);
    return stage
      ? t(`deals.stages.${stageKey(stage.name)}`, { defaultValue: stage.name })
      : t("deals.unknownReference");
  };
  const clientLabel = (clientId) =>
    lookups.clients.get(clientId)?.name ?? t("deals.unknownReference");
  const employeeLabel = (employeeId) =>
    employeeId
      ? (lookups.employees.get(employeeId)?.display_name ??
        t("deals.unknownReference"))
      : t("deals.unassigned");
  const canChange = (deal) =>
    !deal.archived_at &&
    (user.role === "ADMIN" || deal.responsible_user_id === user.id);
  const locale = i18n.resolvedLanguage ?? "ru";
  const serviceLabel = (serviceId) =>
    references.services.find((item) => item.id === serviceId)?.[
      `name_${locale}`
    ] ?? t("deals.unknownReference");
  const categoryLabel = (serviceId) => {
    const service = references.services.find((item) => item.id === serviceId);
    return (
      references.categories.find((item) => item.id === service?.category_id)?.[
        `name_${locale}`
      ] ?? t("deals.unknownReference")
    );
  };
  const hasInactiveBusinessReference = (serviceId) => {
    const service = references.services.find((item) => item.id === serviceId);
    const category = references.categories.find(
      (item) => item.id === service?.category_id,
    );
    return Boolean(service && (!service.is_active || !category?.is_active));
  };

  function openCreate() {
    setForm({
      ...EMPTY_FORM,
      client_id: references.clients[0]?.id ?? "",
      stage_id: references.stages[0]?.id ?? "",
      service_id:
        references.services.find(
          (item) =>
            item.is_active &&
            references.categories.find(
              (category) => category.id === item.category_id,
            )?.is_active,
        )?.id ?? "",
    });
    setFormError("");
    setModal({ mode: "create" });
  }
  async function openDetail(dealId) {
    setModal({ mode: "loading" });
    setFormError("");
    try {
      setShowCalendarCreate(false);
      setModal({ mode: "detail", deal: await getDeal(accessToken, dealId) });
    } catch {
      setModal(null);
      setState("error");
    }
  }
  function openEdit(deal) {
    setForm({
      name: deal.name,
      description: deal.description ?? "",
      client_name: clientLabel(deal.client_id),
      stage_name: stageLabel(deal.stage_id),
      service_id: deal.service_id ?? "",
      estimated_budget: deal.estimated_budget ?? "",
      deadline: deal.deadline ?? "",
      manager_effort_estimate: deal.manager_effort_estimate ?? "",
      probability: deal.probability ?? "",
      responsible_user_id: deal.responsible_user_id ?? "",
    });
    setFormError("");
    setModal({ mode: "edit", deal });
  }
  function changeField(event) {
    setForm((previous) => ({
      ...previous,
      [event.target.name]: event.target.value,
    }));
  }
  function payloadFor(mode) {
    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      estimated_budget:
        form.estimated_budget === "" ? null : form.estimated_budget,
      deadline: form.deadline || null,
      probability: form.probability === "" ? null : Number(form.probability),
      service_id: form.service_id || null,
      manager_effort_estimate:
        form.manager_effort_estimate === ""
          ? null
          : form.manager_effort_estimate,
    };
    if (mode === "create") {
      payload.client_id = form.client_id;
      payload.stage_id = form.stage_id;
      payload.ai_analysis_language = (
        i18n.resolvedLanguage ?? "ru"
      ).toUpperCase();
      if (user.role === "ADMIN")
        payload.responsible_user_id = form.responsible_user_id || null;
    } else if (user.role === "ADMIN")
      payload.responsible_user_id = form.responsible_user_id || null;
    return payload;
  }
  async function submit(event) {
    event.preventDefault();
    if (!form.name.trim()) {
      setFormError(t("deals.validation.nameRequired"));
      return;
    }
    setIsSubmitting(true);
    setFormError("");
    try {
      if (modal.mode === "create")
        await createDeal(accessToken, payloadFor("create"));
      else await updateDeal(accessToken, modal.deal.id, payloadFor("edit"));
      setModal(null);
      load(modal.mode === "create" ? 0 : offset);
    } catch {
      setFormError(t("deals.errors.save"));
    } finally {
      setIsSubmitting(false);
    }
  }
  async function submitTransition(event) {
    event.preventDefault();
    const stageId = event.target.stage_id.value;
    if (!stageId || stageId === modal.deal.stage_id) return;
    setIsSubmitting(true);
    setFormError("");
    try {
      const deal = await transitionDeal(accessToken, modal.deal.id, stageId);
      setModal({ mode: "detail", deal });
      load(offset);
    } catch {
      setFormError(t("deals.errors.transition"));
    } finally {
      setIsSubmitting(false);
    }
  }
  async function changeArchive() {
    if (!modal?.deal) return;
    setIsSubmitting(true);
    setFormError("");
    try {
      await (modal.deal.archived_at
        ? restoreDeal(accessToken, modal.deal.id)
        : archiveDeal(accessToken, modal.deal.id));
      setConfirmArchive(false);
      setModal(null);
      load(0);
    } catch {
      setFormError(t("archive.error"));
    } finally {
      setIsSubmitting(false);
    }
  }
  async function openPublicRequest() {
    setRelatedView("request"); setPublicRequest(undefined);
    try { setPublicRequest(await getDealPublicRequest(accessToken, modal.deal.id)); }
    catch { setPublicRequest(null); }
  }

  return (
    <>
      <section className="page-header">
        <div>
          <p className="eyebrow">{t("crm.navigation.deals")}</p>
          <h1>{t("deals.title")}</h1>
          <p>{t("deals.subtitle")}</p>
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
            disabled={state !== "ready"}
          >
            + {t("deals.create")}
          </button>
        </div>
      </section>
      <section className="content-surface clients-surface" aria-live="polite">
        {state === "loading" && (
          <div className="state-panel">
            <span className="loading-spinner" aria-hidden="true" />
            <p>{t("deals.loading")}</p>
          </div>
        )}
        {state === "error" && (
          <div className="state-panel">
            <p className="form-error">{t("deals.errors.load")}</p>
            <button
              className="secondary-button"
              type="button"
              onClick={() => load(offset)}
            >
              {t("common.retry")}
            </button>
          </div>
        )}
        {state === "ready" && deals.length === 0 && (
          <div className="state-panel">
            <h2>{t("deals.empty.title")}</h2>
            <p>{t("deals.empty.description")}</p>
            <button
              className="primary-button"
              type="button"
              onClick={openCreate}
            >
              {t("deals.empty.action")}
            </button>
          </div>
        )}
        {state === "ready" && deals.length > 0 && (
          <>
            <div className="clients-table-wrap">
              <table className="clients-table deals-table">
                <thead>
                  <tr>
                    <th>{t("deals.fields.name")}</th>
                    <th>{t("deals.fields.client")}</th>
                    <th>{t("deals.fields.stage")}</th>
                    <th>{t("deals.fields.responsible")}</th>
                    <th className="deals-table__metric">{t("deals.fields.estimated_budget")}</th>
                    <th>{t("deals.fields.deadline")}</th>
                    <th className="deals-table__metric">{t("deals.fields.attractiveness")}</th>
                    <th className="deals-table__metric">{t("deals.fields.probability")}</th>
                  </tr>
                </thead>
                <tbody>
                  {deals.map((deal) => (
                    <tr
                      key={deal.id}
                      tabIndex="0"
                      onClick={() => openDetail(deal.id)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ")
                          openDetail(deal.id);
                      }}
                    >
                      <td>
                        <strong>{deal.name}</strong>
                      </td>
                      <td>{clientLabel(deal.client_id)}</td>
                      <td>
                        <span className="stage-badge">
                          {stageLabel(deal.stage_id)}
                        </span>
                      </td>
                      <td>{employeeLabel(deal.responsible_user_id)}</td>
                      <td className="deals-table__metric">{moneyLabel(deal.estimated_budget, locale)}</td>
                      <td>{dateLabel(deal.deadline, locale)}</td>
                      <td className="deals-table__metric">{scoreLabel(deal.latest_lead_scoring_score, locale)}</td>
                      <td className="deals-table__metric">{percentLabel(deal.latest_deal_prediction_probability, locale)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <nav
              className="pagination"
              aria-label={t("deals.pagination.label")}
            >
              <button
                className="secondary-button"
                type="button"
                disabled={offset === 0}
                onClick={() => load(Math.max(0, offset - PAGE_SIZE))}
              >
                {t("deals.pagination.previous")}
              </button>
              <span>
                {t("deals.pagination.page", {
                  page: Math.floor(offset / PAGE_SIZE) + 1,
                })}
              </span>
              <button
                className="secondary-button"
                type="button"
                disabled={deals.length < PAGE_SIZE}
                onClick={() => load(offset + PAGE_SIZE)}
              >
                {t("deals.pagination.next")}
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
            aria-labelledby="deal-modal-title"
          >
            <div className="modal-header">
              <div>
                <p className="eyebrow">
                  {modal.mode === "create"
                    ? t("deals.create")
                    : modal.mode === "edit"
                      ? t("deals.edit")
                      : t("deals.details")}
                </p>
                <h2 id="deal-modal-title">
                  {modal.deal?.name ?? t("deals.create")}
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
                <p>{t("deals.loading")}</p>
              </div>
            ) : modal.mode === "detail" ? (
              <>
                <div className="deal-actions deal-actions--operational">
                  {canChange(modal.deal) && (
                    <button
                      className="secondary-button deal-action-button"
                      type="button"
                      onClick={() => openEdit(modal.deal)}
                    >
                      <Pencil aria-hidden="true" />
                      {t("deals.actionEdit")}
                    </button>
                  )}
                  {user.role === "ADMIN" &&
                    (confirmArchive ? (
                      <div className="warning-box" role="alert">
                        <p>
                          {t(
                            modal.deal.archived_at
                              ? "archive.restoreConfirmDeal"
                              : "archive.confirmDeal",
                          )}
                        </p>
                        <div className="form-actions">
                          <button
                            className="primary-button"
                            type="button"
                            disabled={isSubmitting}
                            onClick={changeArchive}
                          >
                            {t(
                              modal.deal.archived_at
                                ? "archive.restore"
                                : "archive.confirm",
                            )}
                          </button>
                          <button
                            className="secondary-button"
                            type="button"
                            disabled={isSubmitting}
                            onClick={() => setConfirmArchive(false)}
                          >
                            {t("common.cancel")}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        className="secondary-button deal-action-button"
                        type="button"
                        onClick={() => setConfirmArchive(true)}
                      >
                        {modal.deal.archived_at ? (
                          <ArchiveRestore aria-hidden="true" />
                        ) : (
                          <Archive aria-hidden="true" />
                        )}
                        {t(
                          modal.deal.archived_at
                            ? "archive.restoreDeal"
                            : "archive.archiveDeal",
                        )}
                      </button>
                    ))}
                  {canChange(modal.deal) ? (
                    <form className="transition-form deal-stage-action" onSubmit={submitTransition}>
                      <label>
                        <span>{t("deals.transition")}</span>
                        <select
                          name="stage_id"
                          defaultValue={modal.deal.stage_id}
                          disabled={isSubmitting}
                        >
                          {references.stages.map((stage) => (
                            <option key={stage.id} value={stage.id}>
                              {t(`deals.stages.${stageKey(stage.name)}`, {
                                defaultValue: stage.name,
                              })}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        className="primary-button"
                        type="submit"
                        disabled={isSubmitting}
                      >
                        {t("deals.move")}
                      </button>
                    </form>
                  ) : (
                    <p className="readonly-note">{t("deals.readonly")}</p>
                  )}
                </div>
                <dl className="deal-details">
                  <div>
                    <dt>{t("deals.fields.client")}</dt>
                    <dd>{clientLabel(modal.deal.client_id)}</dd>
                  </div>
                  <div>
                    <dt>{t("deals.fields.stage")}</dt>
                    <dd>{stageLabel(modal.deal.stage_id)}</dd>
                  </div>
                  <div>
                    <dt>{t("d4.service")}</dt>
                    <dd>{serviceLabel(modal.deal.service_id)}</dd>
                  </div>
                  <div>
                    <dt>{t("d4.category")}</dt>
                    <dd>{categoryLabel(modal.deal.service_id)}</dd>
                  </div>
                  <div>
                    <dt>{t("deals.fields.responsible")}</dt>
                    <dd>{employeeLabel(modal.deal.responsible_user_id)}</dd>
                  </div>
                  <div>
                    <dt>{t("deals.fields.estimated_budget")}</dt>
                    <dd>{moneyLabel(modal.deal.estimated_budget, locale)}</dd>
                  </div>
                  <div>
                    <dt>{t("deals.fields.deadline")}</dt>
                    <dd>
                      {dateLabel(modal.deal.deadline, locale)}
                      {modal.deal.deadline &&
                        modal.deal.deadline <
                          new Date().toISOString().slice(0, 10) && (
                          <small className="deadline-warning">
                            {t("d4.pastDeadline")}
                          </small>
                        )}
                    </dd>
                  </div>
                  <div>
                    <dt>{t("d4.managerEffort")}</dt>
                    <dd>
                      {modal.deal.manager_effort_estimate
                        ? `${new Intl.NumberFormat(locale).format(Number(modal.deal.manager_effort_estimate))} h · ${new Intl.NumberFormat(locale).format(Number(modal.deal.manager_effort_estimate) / 8)} d`
                        : "—"}
                    </dd>
                  </div>
                  <div>
                    <dt>{t("deals.fields.probability")}</dt>
                    <dd>{percentLabel(modal.deal.probability, locale)}</dd>
                  </div>
                  <div className="field--full">
                    <dt>{t("deals.fields.description")}</dt>
                    <dd>{modal.deal.description || "—"}</dd>
                  </div>
                </dl>
                <div className="deal-actions deal-actions--related" aria-label={t("dealRelated.title")}>
                  <button className="secondary-button deal-action-button" type="button" onClick={openPublicRequest}><FileText aria-hidden="true" />{t("dealRelated.request")}</button>
                  <button className="secondary-button deal-action-button" type="button" onClick={() => setRelatedView("communications")}><MessageCircle aria-hidden="true" />{t("dealRelated.communications")}</button>
                  <button className="secondary-button deal-action-button" type="button" onClick={() => setRelatedView("email")}><Mail aria-hidden="true" />{t("dealRelated.email")}</button>
                  <button className="secondary-button deal-action-button" type="button" onClick={() => setRelatedView("calendar")}><CalendarDays aria-hidden="true" />{t("dealRelated.calendar")}</button>
                </div>
                {hasInactiveBusinessReference(modal.deal.service_id) && (
                  <p className="warning-box">
                    {t("d4.inactiveBusinessReference")}
                  </p>
                )}
                <LeadScoringSection
                  deal={modal.deal}
                  canRun={canChange(modal.deal)}
                  isClosed={["Won", "Lost"].includes(
                    references.stages.find(
                      (item) => item.id === modal.deal.stage_id,
                    )?.name,
                  )}
                />
                <DealPredictionSection
                  deal={modal.deal}
                  canRun={canChange(modal.deal)}
                  isClosed={["Won", "Lost"].includes(
                    references.stages.find(
                      (item) => item.id === modal.deal.stage_id,
                    )?.name,
                  )}
                />
                <NextBestActionSection
                  deal={modal.deal}
                  canRun={canChange(modal.deal)}
                  isClosed={["Won", "Lost"].includes(
                    references.stages.find(
                      (item) => item.id === modal.deal.stage_id,
                    )?.name,
                  )}
                />
                {canChange(modal.deal) && (
                  <DealAIHistorySection dealId={modal.deal.id} />
                )}
                {formError && (
                  <p className="form-error" role="alert">
                    {formError}
                  </p>
                )}
              </>
            ) : (
              <DealForm
                form={form}
                clients={references.clients}
                stages={references.stages}
                employees={references.employees}
                services={references.services}
                categories={references.categories}
                isAdmin={user.role === "ADMIN"}
                submitting={isSubmitting}
                error={formError}
                onChange={changeField}
                onSubmit={submit}
                submitLabel={t(isSubmitting ? "common.saving" : "common.save")}
                mode={modal.mode}
              />
            )}
          </section>
        </div>
      )}
      {modal?.mode === "detail" && <RelatedDealDialog view={relatedView} onClose={() => { setRelatedView(null); setShowCalendarCreate(false); }} request={publicRequest} deal={modal.deal} client={lookups.clients.get(modal.deal.client_id)} canRun={canChange(modal.deal)} refreshKey={calendarRefreshKey} showCalendarCreate={showCalendarCreate} setShowCalendarCreate={setShowCalendarCreate} onCalendarAccepted={() => { setShowCalendarCreate(false); setCalendarRefreshKey((value) => value + 1); }} />}
    </>
  );
}

export default DealsPage;
