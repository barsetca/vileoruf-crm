import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import { listClients } from "../services/clients.js";
import { createDeal, getDeal, listDeals, transitionDeal, updateDeal } from "../services/deals.js";
import { listEmployeeReferences, listPipelineStages } from "../services/referenceData.js";


const PAGE_SIZE = 10;
const EMPTY_FORM = {
  name: "", description: "", client_id: "", stage_id: "", estimated_budget: "", deadline: "", probability: "", responsible_user_id: "",
};

function stageKey(name) {
  return {
    "New Lead": "newLead", Contact: "contact", Qualification: "qualification", Proposal: "proposal",
    Negotiation: "negotiation", Won: "won", Lost: "lost",
  }[name];
}

function dateLabel(value, locale) {
  return value ? new Intl.DateTimeFormat(locale, { year: "numeric", month: "short", day: "numeric" }).format(new Date(`${value}T00:00:00`)) : "—";
}

function DealForm({ form, clients, stages, employees, isAdmin, submitting, error, onChange, onSubmit, submitLabel, mode }) {
  const { t } = useTranslation();
  const activeEmployees = employees.filter((employee) => employee.is_active);
  return <form className="client-form" onSubmit={onSubmit}>
    <div className="client-form-grid">
      <label className="field field--full"><span>{t("deals.fields.name")} <em aria-hidden="true">*</em></span><input name="name" value={form.name} onChange={onChange} disabled={submitting} required /></label>
      {mode === "create" ? <label className="field"><span>{t("deals.fields.client")} <em aria-hidden="true">*</em></span><select name="client_id" value={form.client_id} onChange={onChange} disabled={submitting} required><option value="">{t("deals.selectClient")}</option>{clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}</select></label> : <label className="field"><span>{t("deals.fields.client")}</span><input value={form.client_name} disabled /></label>}
      {mode === "create" ? <label className="field"><span>{t("deals.fields.stage")} <em aria-hidden="true">*</em></span><select name="stage_id" value={form.stage_id} onChange={onChange} disabled={submitting} required><option value="">{t("deals.selectStage")}</option>{stages.map((stage) => <option key={stage.id} value={stage.id}>{t(`deals.stages.${stageKey(stage.name)}`, { defaultValue: stage.name })}</option>)}</select></label> : <label className="field"><span>{t("deals.fields.stage")}</span><input value={form.stage_name} disabled /></label>}
      <label className="field field--full"><span>{t("deals.fields.description")}</span><textarea name="description" value={form.description} onChange={onChange} rows="3" disabled={submitting} /></label>
      <label className="field"><span>{t("deals.fields.estimated_budget")}</span><input name="estimated_budget" type="number" min="0" step="0.01" value={form.estimated_budget} onChange={onChange} disabled={submitting} /></label>
      <label className="field"><span>{t("deals.fields.deadline")}</span><input name="deadline" type="date" value={form.deadline} onChange={onChange} disabled={submitting} /></label>
      <label className="field"><span>{t("deals.fields.probability")}</span><input name="probability" type="number" min="0" max="100" value={form.probability} onChange={onChange} disabled={submitting} /></label>
      {isAdmin && <label className="field"><span>{t("deals.fields.responsible")}</span><select name="responsible_user_id" value={form.responsible_user_id} onChange={onChange} disabled={submitting}><option value="">{t("deals.unassigned")}</option>{activeEmployees.map((employee) => <option key={employee.id} value={employee.id}>{employee.display_name} · {t(`employees.roles.${employee.role}`)}</option>)}</select></label>}
    </div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="primary-button" type="submit" disabled={submitting}>{submitLabel}</button>
  </form>;
}

function DealsPage({ initialDealId }) {
  const { t, i18n } = useTranslation();
  const { accessToken, user } = useAuth();
  const [deals, setDeals] = useState([]);
  const [references, setReferences] = useState({ clients: [], stages: [], employees: [] });
  const [offset, setOffset] = useState(0);
  const [state, setState] = useState("loading");
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const load = useCallback((nextOffset = offset) => {
    const controller = new AbortController();
    setState("loading");
    Promise.all([
      listDeals(accessToken, { limit: PAGE_SIZE, offset: nextOffset }, controller.signal),
      listClients(accessToken, { limit: 100, offset: 0 }, controller.signal),
      listPipelineStages(accessToken, controller.signal),
      listEmployeeReferences(accessToken, controller.signal),
    ]).then(([nextDeals, clients, stages, employees]) => {
      setDeals(nextDeals); setReferences({ clients, stages, employees }); setOffset(nextOffset); setState("ready");
    }).catch((error) => { if (error.name !== "AbortError") setState("error"); });
    return controller;
  }, [accessToken, offset]);

  useEffect(() => {
    const controller = load(0);
    return () => controller.abort();
  }, [accessToken]);

  useEffect(() => {
    if (initialDealId) openDetail(initialDealId);
  }, [initialDealId]);

  const lookups = useMemo(() => ({
    clients: new Map(references.clients.map((item) => [item.id, item])),
    stages: new Map(references.stages.map((item) => [item.id, item])),
    employees: new Map(references.employees.map((item) => [item.id, item])),
  }), [references]);
  const stageLabel = (stageId) => {
    const stage = lookups.stages.get(stageId);
    return stage ? t(`deals.stages.${stageKey(stage.name)}`, { defaultValue: stage.name }) : t("deals.unknownReference");
  };
  const clientLabel = (clientId) => lookups.clients.get(clientId)?.name ?? t("deals.unknownReference");
  const employeeLabel = (employeeId) => employeeId ? lookups.employees.get(employeeId)?.display_name ?? t("deals.unknownReference") : t("deals.unassigned");
  const canChange = (deal) => user.role === "ADMIN" || deal.responsible_user_id === user.id;
  const locale = i18n.resolvedLanguage ?? "ru";

  function openCreate() {
    setForm({ ...EMPTY_FORM, client_id: references.clients[0]?.id ?? "", stage_id: references.stages[0]?.id ?? "" });
    setFormError(""); setModal({ mode: "create" });
  }
  async function openDetail(dealId) {
    setModal({ mode: "loading" }); setFormError("");
    try { setModal({ mode: "detail", deal: await getDeal(accessToken, dealId) }); }
    catch { setModal(null); setState("error"); }
  }
  function openEdit(deal) {
    setForm({ name: deal.name, description: deal.description ?? "", client_name: clientLabel(deal.client_id), stage_name: stageLabel(deal.stage_id), estimated_budget: deal.estimated_budget ?? "", deadline: deal.deadline ?? "", probability: deal.probability ?? "", responsible_user_id: deal.responsible_user_id ?? "" });
    setFormError(""); setModal({ mode: "edit", deal });
  }
  function changeField(event) { setForm((previous) => ({ ...previous, [event.target.name]: event.target.value })); }
  function payloadFor(mode) {
    const payload = {
      name: form.name.trim(), description: form.description.trim() || null,
      estimated_budget: form.estimated_budget === "" ? null : form.estimated_budget,
      deadline: form.deadline || null, probability: form.probability === "" ? null : Number(form.probability),
    };
    if (mode === "create") {
      payload.client_id = form.client_id; payload.stage_id = form.stage_id;
      if (user.role === "ADMIN") payload.responsible_user_id = form.responsible_user_id || null;
    } else if (user.role === "ADMIN") payload.responsible_user_id = form.responsible_user_id || null;
    return payload;
  }
  async function submit(event) {
    event.preventDefault();
    if (!form.name.trim()) { setFormError(t("deals.validation.nameRequired")); return; }
    setIsSubmitting(true); setFormError("");
    try {
      if (modal.mode === "create") await createDeal(accessToken, payloadFor("create"));
      else await updateDeal(accessToken, modal.deal.id, payloadFor("edit"));
      setModal(null); load(modal.mode === "create" ? 0 : offset);
    } catch { setFormError(t("deals.errors.save")); }
    finally { setIsSubmitting(false); }
  }
  async function submitTransition(event) {
    event.preventDefault();
    const stageId = event.target.stage_id.value;
    if (!stageId || stageId === modal.deal.stage_id) return;
    setIsSubmitting(true); setFormError("");
    try {
      const deal = await transitionDeal(accessToken, modal.deal.id, stageId);
      setModal({ mode: "detail", deal }); load(offset);
    } catch { setFormError(t("deals.errors.transition")); }
    finally { setIsSubmitting(false); }
  }

  return <>
    <section className="page-header"><div><p className="eyebrow">{t("crm.navigation.deals")}</p><h1>{t("deals.title")}</h1><p>{t("deals.subtitle")}</p></div><button className="primary-button page-action" type="button" onClick={openCreate} disabled={state !== "ready"}>+ {t("deals.create")}</button></section>
    <section className="content-surface clients-surface" aria-live="polite">
      {state === "loading" && <div className="state-panel"><span className="loading-spinner" aria-hidden="true" /><p>{t("deals.loading")}</p></div>}
      {state === "error" && <div className="state-panel"><p className="form-error">{t("deals.errors.load")}</p><button className="secondary-button" type="button" onClick={() => load(offset)}>{t("common.retry")}</button></div>}
      {state === "ready" && deals.length === 0 && <div className="state-panel"><h2>{t("deals.empty.title")}</h2><p>{t("deals.empty.description")}</p><button className="primary-button" type="button" onClick={openCreate}>{t("deals.empty.action")}</button></div>}
      {state === "ready" && deals.length > 0 && <><div className="clients-table-wrap"><table className="clients-table deals-table"><thead><tr><th>{t("deals.fields.name")}</th><th>{t("deals.fields.client")}</th><th>{t("deals.fields.stage")}</th><th>{t("deals.fields.responsible")}</th><th>{t("deals.fields.estimated_budget")}</th><th>{t("deals.fields.deadline")}</th><th>{t("deals.fields.probability")}</th></tr></thead><tbody>{deals.map((deal) => <tr key={deal.id} tabIndex="0" onClick={() => openDetail(deal.id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") openDetail(deal.id); }}><td><strong>{deal.name}</strong></td><td>{clientLabel(deal.client_id)}</td><td><span className="stage-badge">{stageLabel(deal.stage_id)}</span></td><td>{employeeLabel(deal.responsible_user_id)}</td><td>{deal.estimated_budget ?? "—"}</td><td>{dateLabel(deal.deadline, locale)}</td><td>{deal.probability == null ? "—" : `${deal.probability}%`}</td></tr>)}</tbody></table></div><nav className="pagination" aria-label={t("deals.pagination.label")}><button className="secondary-button" type="button" disabled={offset === 0} onClick={() => load(Math.max(0, offset - PAGE_SIZE))}>{t("deals.pagination.previous")}</button><span>{t("deals.pagination.page", { page: Math.floor(offset / PAGE_SIZE) + 1 })}</span><button className="secondary-button" type="button" disabled={deals.length < PAGE_SIZE} onClick={() => load(offset + PAGE_SIZE)}>{t("deals.pagination.next")}</button></nav></>}
    </section>
    {modal && <div className="modal-backdrop" role="presentation"><section className="client-modal" role="dialog" aria-modal="true" aria-labelledby="deal-modal-title"><div className="modal-header"><div><p className="eyebrow">{modal.mode === "create" ? t("deals.create") : modal.mode === "edit" ? t("deals.edit") : t("deals.details")}</p><h2 id="deal-modal-title">{modal.deal?.name ?? t("deals.create")}</h2></div><button className="icon-button" type="button" onClick={() => setModal(null)} aria-label={t("common.close")}>×</button></div>{modal.mode === "loading" ? <div className="state-panel"><span className="loading-spinner" /><p>{t("deals.loading")}</p></div> : modal.mode === "detail" ? <><dl className="deal-details"><div><dt>{t("deals.fields.client")}</dt><dd>{clientLabel(modal.deal.client_id)}</dd></div><div><dt>{t("deals.fields.stage")}</dt><dd>{stageLabel(modal.deal.stage_id)}</dd></div><div><dt>{t("deals.fields.responsible")}</dt><dd>{employeeLabel(modal.deal.responsible_user_id)}</dd></div><div><dt>{t("deals.fields.estimated_budget")}</dt><dd>{modal.deal.estimated_budget ?? "—"}</dd></div><div><dt>{t("deals.fields.deadline")}</dt><dd>{dateLabel(modal.deal.deadline, locale)}</dd></div><div><dt>{t("deals.fields.probability")}</dt><dd>{modal.deal.probability == null ? "—" : `${modal.deal.probability}%`}</dd></div><div className="field--full"><dt>{t("deals.fields.description")}</dt><dd>{modal.deal.description || "—"}</dd></div></dl>{canChange(modal.deal) ? <div className="deal-actions"><button className="secondary-button" type="button" onClick={() => openEdit(modal.deal)}>{t("deals.edit")}</button><form className="transition-form" onSubmit={submitTransition}><label><span>{t("deals.transition")}</span><select name="stage_id" defaultValue={modal.deal.stage_id} disabled={isSubmitting}>{references.stages.map((stage) => <option key={stage.id} value={stage.id}>{t(`deals.stages.${stageKey(stage.name)}`, { defaultValue: stage.name })}</option>)}</select></label><button className="primary-button" type="submit" disabled={isSubmitting}>{t("deals.move")}</button></form></div> : <p className="readonly-note">{t("deals.readonly")}</p>}{formError && <p className="form-error" role="alert">{formError}</p>}</> : <DealForm form={form} clients={references.clients} stages={references.stages} employees={references.employees} isAdmin={user.role === "ADMIN"} submitting={isSubmitting} error={formError} onChange={changeField} onSubmit={submit} submitLabel={t(isSubmitting ? "common.saving" : "common.save")} mode={modal.mode} />}</section></div>}
  </>;
}


export default DealsPage;
