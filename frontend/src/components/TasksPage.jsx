import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import { listClients } from "../services/clients.js";
import { listDeals } from "../services/deals.js";
import { listEmployeeReferences } from "../services/referenceData.js";
import { TaskApiError, completeTask, createTask, listTasks, updateTask } from "../services/tasks.js";


const PAGE_SIZE = 10;
const REFERENCE_LIMIT = 100;
const EMPTY_FILTERS = { status: "", responsibleUserId: "", clientId: "", dealId: "" };

function localDateTime(value = new Date()) {
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function initialForm(task = null, user = null) {
  return {
    title: task?.title ?? "",
    description: task?.description ?? "",
    dueAt: task ? localDateTime(task.due_at) : localDateTime(),
    responsibleUserId: task?.responsible_user_id ?? user?.id ?? "",
    clientId: task?.client_id ?? "",
    dealId: task?.deal_id ?? "",
  };
}

async function loadAll(listPage, accessToken, signal) {
  const records = [];
  while (true) {
    const batch = await listPage(accessToken, { limit: REFERENCE_LIMIT, offset: records.length }, signal);
    records.push(...batch);
    if (batch.length < REFERENCE_LIMIT) return records;
  }
}

function formatDateTime(value, locale) {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function TaskForm({ form, employees, clients, deals, isAdmin, user, submitting, error, onChange, onSubmit, submitLabel }) {
  const { t } = useTranslation();
  const activeEmployees = employees.filter((employee) => employee.is_active);
  const selectableDeals = form.clientId ? deals.filter((deal) => deal.client_id === form.clientId) : deals;
  const currentEmployee = employees.find((employee) => employee.id === user.id);
  return <form className="client-form" onSubmit={onSubmit}>
    <div className="client-form-grid">
      <label className="field field--full"><span>{t("tasks.fields.title")} <em aria-hidden="true">*</em></span><input name="title" value={form.title} onChange={onChange} disabled={submitting} required /></label>
      <label className="field field--full"><span>{t("tasks.fields.description")}</span><textarea name="description" value={form.description} onChange={onChange} rows="3" disabled={submitting} /></label>
      <label className="field"><span>{t("tasks.fields.dueAt")} <em aria-hidden="true">*</em></span><input name="dueAt" type="datetime-local" value={form.dueAt} onChange={onChange} disabled={submitting} required /></label>
      {isAdmin ? <label className="field"><span>{t("tasks.fields.responsible")} <em aria-hidden="true">*</em></span><select name="responsibleUserId" value={form.responsibleUserId} onChange={onChange} disabled={submitting} required><option value="">{t("tasks.filters.allEmployees")}</option>{activeEmployees.map((employee) => <option key={employee.id} value={employee.id}>{employee.display_name} · {t(`employees.roles.${employee.role}`)}</option>)}</select></label> : <label className="field"><span>{t("tasks.fields.responsible")}</span><input value={currentEmployee?.display_name ?? user.display_name} disabled /></label>}
      <label className="field"><span>{t("tasks.fields.client")}</span><select name="clientId" value={form.clientId} onChange={onChange} disabled={submitting}><option value="">{t("tasks.associations.none")}</option>{clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}</select></label>
      <label className="field"><span>{t("tasks.fields.deal")}</span><select name="dealId" value={form.dealId} onChange={onChange} disabled={submitting}><option value="">{t("tasks.associations.none")}</option>{selectableDeals.map((deal) => <option key={deal.id} value={deal.id}>{deal.name}</option>)}</select></label>
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="primary-button" type="submit" disabled={submitting}>{submitLabel}</button>
  </form>;
}

function TasksPage() {
  const { t, i18n } = useTranslation();
  const { accessToken, user } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [references, setReferences] = useState({ clients: [], deals: [], employees: [] });
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState("loading");
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState(initialForm(null, user));
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const locale = i18n.resolvedLanguage ?? "ru";

  const load = useCallback((nextOffset = 0, nextFilters = appliedFilters) => {
    const controller = new AbortController();
    setState("loading");
    Promise.all([
      listTasks(accessToken, { limit: PAGE_SIZE, offset: nextOffset, ...nextFilters }, controller.signal),
      loadAll(listClients, accessToken, controller.signal),
      loadAll(listDeals, accessToken, controller.signal),
      listEmployeeReferences(accessToken, controller.signal),
    ]).then(([nextTasks, clients, deals, employees]) => {
      setTasks(nextTasks); setReferences({ clients, deals, employees }); setOffset(nextOffset); setState("ready");
    }).catch((error) => { if (error.name !== "AbortError") setState("error"); });
    return controller;
  }, [accessToken, appliedFilters]);

  useEffect(() => {
    const controller = load(0, EMPTY_FILTERS);
    return () => controller.abort();
  }, [accessToken]);

  const lookups = useMemo(() => ({
    clients: new Map(references.clients.map((item) => [item.id, item])),
    deals: new Map(references.deals.map((item) => [item.id, item])),
    employees: new Map(references.employees.map((item) => [item.id, item])),
  }), [references]);
  const canModify = (task) => user.role === "ADMIN" || task.responsible_user_id === user.id;
  const labelClient = (id) => id ? lookups.clients.get(id)?.name ?? t("tasks.unknownReference") : t("tasks.associations.none");
  const labelDeal = (id) => id ? lookups.deals.get(id)?.name ?? t("tasks.unknownReference") : t("tasks.associations.none");
  const labelEmployee = (id) => lookups.employees.get(id)?.display_name ?? t("tasks.unknownReference");
  const isOverdue = (task) => task.status === "OPEN" && new Date(task.due_at) < new Date();

  function openCreate() { setForm(initialForm(null, user)); setFormError(""); setModal({ mode: "create" }); }
  function openDetail(task) { setFormError(""); setModal({ mode: "detail", task }); }
  function openEdit(task) { setForm(initialForm(task, user)); setFormError(""); setModal({ mode: "edit", task }); }
  function changeForm(event) {
    const { name, value } = event.target;
    setForm((previous) => {
      const next = { ...previous, [name]: value };
      if (name === "clientId" && next.dealId && references.deals.find((deal) => deal.id === next.dealId)?.client_id !== value) next.dealId = "";
      return next;
    });
  }
  function changeFilter(event) { setFilters((previous) => ({ ...previous, [event.target.name]: event.target.value })); }
  function applyFilters(event) { event.preventDefault(); const next = { ...filters }; setAppliedFilters(next); load(0, next); }
  function resetFilters() { setFilters(EMPTY_FILTERS); setAppliedFilters(EMPTY_FILTERS); load(0, EMPTY_FILTERS); }
  function payloadFor(mode) {
    const payload = {
      title: form.title.trim(), description: form.description.trim() || null,
      due_at: new Date(form.dueAt).toISOString(), client_id: form.clientId || null, deal_id: form.dealId || null,
    };
    if (mode === "create" || user.role === "ADMIN") payload.responsible_user_id = user.role === "ADMIN" ? form.responsibleUserId : user.id;
    return payload;
  }
  function errorMessage(error, action) {
    if (error instanceof TaskApiError && error.status === 403) return t("tasks.errors.forbidden");
    if (error instanceof TaskApiError && error.status === 404) return t("tasks.errors.notFound");
    if (error instanceof TaskApiError && error.status === 422) return t("tasks.errors.validation");
    return t(`tasks.errors.${action}`);
  }
  async function submit(event) {
    event.preventDefault();
    if (!form.title.trim()) { setFormError(t("tasks.validation.titleRequired")); return; }
    setIsSubmitting(true); setFormError("");
    try {
      if (modal.mode === "create") await createTask(accessToken, payloadFor("create"));
      else await updateTask(accessToken, modal.task.id, payloadFor("edit"));
      setModal(null); load(modal.mode === "create" ? 0 : offset);
    } catch (error) { setFormError(errorMessage(error, "save")); }
    finally { setIsSubmitting(false); }
  }
  async function complete(task) {
    setIsSubmitting(true); setFormError("");
    try {
      const completed = await completeTask(accessToken, task.id);
      if (modal?.mode === "detail" && modal.task.id === completed.id) setModal({ mode: "detail", task: completed });
      load(offset);
    } catch (error) { setFormError(errorMessage(error, "complete")); }
    finally { setIsSubmitting(false); }
  }

  return <>
    <section className="page-header"><div><p className="eyebrow">{t("crm.navigation.tasks")}</p><h1>{t("tasks.title")}</h1><p>{t("tasks.subtitle")}</p></div><button className="primary-button page-action" type="button" onClick={openCreate} disabled={state !== "ready"}>+ {t("tasks.create")}</button></section>
    <form className="task-filters content-surface" onSubmit={applyFilters}>
      <label className="field"><span>{t("tasks.fields.status")}</span><select name="status" value={filters.status} onChange={changeFilter}><option value="">{t("tasks.filters.allStatuses")}</option><option value="OPEN">{t("tasks.status.OPEN")}</option><option value="COMPLETED">{t("tasks.status.COMPLETED")}</option></select></label>
      <label className="field"><span>{t("tasks.fields.responsible")}</span><select name="responsibleUserId" value={filters.responsibleUserId} onChange={changeFilter}><option value="">{t("tasks.filters.allEmployees")}</option>{references.employees.map((employee) => <option key={employee.id} value={employee.id}>{employee.display_name}</option>)}</select></label>
      <label className="field"><span>{t("tasks.fields.client")}</span><select name="clientId" value={filters.clientId} onChange={changeFilter}><option value="">{t("tasks.filters.allClients")}</option>{references.clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}</select></label>
      <label className="field"><span>{t("tasks.fields.deal")}</span><select name="dealId" value={filters.dealId} onChange={changeFilter}><option value="">{t("tasks.filters.allDeals")}</option>{references.deals.map((deal) => <option key={deal.id} value={deal.id}>{deal.name}</option>)}</select></label>
      <div className="task-filter-actions"><button className="secondary-button" type="submit">{t("tasks.filters.apply")}</button><button className="text-button" type="button" onClick={resetFilters}>{t("tasks.filters.reset")}</button></div>
    </form>
    {formError && !modal && <p className="form-error" role="alert">{formError}</p>}
    <section className="content-surface clients-surface" aria-live="polite">
      {state === "loading" && <div className="state-panel"><span className="loading-spinner" aria-hidden="true" /><p>{t("tasks.loading")}</p></div>}
      {state === "error" && <div className="state-panel"><p className="form-error">{t("tasks.errors.load")}</p><button className="secondary-button" type="button" onClick={() => load(offset)}>{t("common.retry")}</button></div>}
      {state === "ready" && tasks.length === 0 && <div className="state-panel"><h2>{t("tasks.empty.title")}</h2><p>{t("tasks.empty.description")}</p><button className="primary-button" type="button" onClick={openCreate}>{t("tasks.empty.action")}</button></div>}
      {state === "ready" && tasks.length > 0 && <><div className="clients-table-wrap"><table className="clients-table tasks-table"><thead><tr><th>{t("tasks.fields.title")}</th><th>{t("tasks.fields.dueAt")}</th><th>{t("tasks.fields.status")}</th><th>{t("tasks.fields.responsible")}</th><th>{t("tasks.fields.client")}</th><th>{t("tasks.fields.deal")}</th></tr></thead><tbody>{tasks.map((task) => <tr key={task.id} tabIndex="0" onClick={() => openDetail(task)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") openDetail(task); }}><td><strong>{task.title}</strong>{isOverdue(task) && <span className="task-overdue">{t("tasks.status.OVERDUE")}</span>}</td><td>{formatDateTime(task.due_at, locale)}</td><td><span className={`task-status task-status--${task.status.toLowerCase()}`}>{t(`tasks.status.${task.status}`)}</span></td><td>{labelEmployee(task.responsible_user_id)}</td><td>{labelClient(task.client_id)}</td><td>{labelDeal(task.deal_id)}</td></tr>)}</tbody></table></div><nav className="pagination" aria-label={t("tasks.pagination.label")}><button className="secondary-button" type="button" disabled={offset === 0} onClick={() => load(Math.max(0, offset - PAGE_SIZE))}>{t("tasks.pagination.previous")}</button><span>{t("tasks.pagination.page", { page: Math.floor(offset / PAGE_SIZE) + 1 })}</span><button className="secondary-button" type="button" disabled={tasks.length < PAGE_SIZE} onClick={() => load(offset + PAGE_SIZE)}>{t("tasks.pagination.next")}</button></nav></>}
    </section>
    {modal && <div className="modal-backdrop" role="presentation"><section className="client-modal" role="dialog" aria-modal="true" aria-labelledby="task-modal-title"><div className="modal-header"><div><p className="eyebrow">{modal.mode === "create" ? t("tasks.create") : modal.mode === "edit" ? t("tasks.edit") : t("tasks.details")}</p><h2 id="task-modal-title">{modal.task?.title ?? t("tasks.create")}</h2></div><button className="icon-button" type="button" onClick={() => setModal(null)} aria-label={t("common.close")}>×</button></div>{modal.mode === "detail" ? <><dl className="deal-details task-details"><div><dt>{t("tasks.fields.responsible")}</dt><dd>{labelEmployee(modal.task.responsible_user_id)}</dd></div><div><dt>{t("tasks.fields.dueAt")}</dt><dd>{formatDateTime(modal.task.due_at, locale)} {isOverdue(modal.task) && <span className="task-overdue">{t("tasks.status.OVERDUE")}</span>}</dd></div><div><dt>{t("tasks.fields.status")}</dt><dd><span className={`task-status task-status--${modal.task.status.toLowerCase()}`}>{t(`tasks.status.${modal.task.status}`)}</span></dd></div><div><dt>{t("tasks.fields.client")}</dt><dd>{labelClient(modal.task.client_id)}</dd></div><div><dt>{t("tasks.fields.deal")}</dt><dd>{labelDeal(modal.task.deal_id)}</dd></div><div className="field--full"><dt>{t("tasks.fields.description")}</dt><dd>{modal.task.description || "—"}</dd></div></dl>{formError && <p className="form-error" role="alert">{formError}</p>}{canModify(modal.task) ? <div className="deal-actions"><button className="secondary-button" type="button" onClick={() => openEdit(modal.task)}>{t("tasks.edit")}</button>{modal.task.status === "OPEN" && <button className="primary-button" type="button" disabled={isSubmitting} onClick={() => complete(modal.task)}>{t("tasks.complete")}</button>}</div> : <p className="readonly-note">{t("tasks.permissions.readonly")}</p>}</> : <TaskForm form={form} employees={references.employees} clients={references.clients} deals={references.deals} isAdmin={user.role === "ADMIN"} user={user} submitting={isSubmitting} error={formError} onChange={changeForm} onSubmit={submit} submitLabel={t(isSubmitting ? "common.saving" : modal.mode === "create" ? "tasks.create" : "common.save")} />}</section></div>}
  </>;
}


export default TasksPage;
