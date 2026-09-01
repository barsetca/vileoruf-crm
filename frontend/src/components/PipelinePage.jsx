import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import { listClients } from "../services/clients.js";
import { listDeals, transitionDeal } from "../services/deals.js";
import { pipelineStageLabel } from "../services/pipelinePresentation.js";
import { listEmployeeReferences, listPipelineStages } from "../services/referenceData.js";


const FETCH_LIMIT = 100;
const MAX_PAGES = 1000;

async function loadAll(listPage, accessToken, signal) {
  const records = [];
  for (let page = 0; page < MAX_PAGES; page += 1) {
    const batch = await listPage(accessToken, { limit: FETCH_LIMIT, offset: records.length }, signal);
    records.push(...batch);
    if (batch.length < FETCH_LIMIT) return records;
  }
  throw new Error("Pagination safety limit exceeded");
}

function formatDeadline(value, locale) {
  return value ? new Intl.DateTimeFormat(locale, { year: "numeric", month: "short", day: "numeric" }).format(new Date(`${value}T00:00:00`)) : null;
}

function PipelinePage({ onOpenDeal }) {
  const { t, i18n } = useTranslation();
  const { accessToken, user } = useAuth();
  const [state, setState] = useState("loading");
  const [data, setData] = useState({ deals: [], clients: [], stages: [], employees: [] });
  const [draggedDeal, setDraggedDeal] = useState(null);
  const [moveDeal, setMoveDeal] = useState(null);
  const [error, setError] = useState("");
  const [isMoving, setIsMoving] = useState(false);
  const locale = i18n.resolvedLanguage ?? "ru";

  const load = useCallback(() => {
    const controller = new AbortController();
    setState("loading"); setError("");
    Promise.all([
      loadAll(listDeals, accessToken, controller.signal),
      loadAll(listClients, accessToken, controller.signal),
      listPipelineStages(accessToken, controller.signal),
      listEmployeeReferences(accessToken, controller.signal),
    ]).then(([deals, clients, stages, employees]) => {
      setData({ deals, clients, stages, employees }); setState("ready");
    }).catch((loadError) => {
      if (loadError.name !== "AbortError") setState("error");
    });
    return controller;
  }, [accessToken]);

  useEffect(() => {
    const controller = load();
    return () => controller.abort();
  }, [load]);

  const lookup = useMemo(() => ({
    clients: new Map(data.clients.map((client) => [client.id, client])),
    employees: new Map(data.employees.map((employee) => [employee.id, employee])),
  }), [data.clients, data.employees]);
  const canMove = (deal) => user.role === "ADMIN" || deal.responsible_user_id === user.id;
  const clientLabel = (deal) => lookup.clients.get(deal.client_id)?.name ?? t("deals.unknownReference");
  const employeeLabel = (deal) => deal.responsible_user_id ? lookup.employees.get(deal.responsible_user_id)?.display_name ?? t("deals.unknownReference") : t("deals.unassigned");

  async function move(deal, targetStageId) {
    if (!canMove(deal) || isMoving) return;
    if (deal.stage_id === targetStageId) {
      setMoveDeal(null);
      return;
    }
    setIsMoving(true); setError("");
    try {
      const updated = await transitionDeal(accessToken, deal.id, targetStageId);
      setData((previous) => ({ ...previous, deals: previous.deals.map((item) => item.id === updated.id ? updated : item) }));
      setMoveDeal(null);
    } catch {
      setError(t("pipeline.errors.transition"));
      setMoveDeal(null);
      load();
    } finally {
      setIsMoving(false); setDraggedDeal(null);
    }
  }

  function dragStart(event, deal) {
    if (!canMove(deal)) return;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", deal.id);
    setDraggedDeal(deal);
  }

  function drop(event, stageId) {
    event.preventDefault();
    const deal = draggedDeal;
    if (deal && deal.stage_id !== stageId) move(deal, stageId);
    setDraggedDeal(null);
  }

  return <>
    <section className="page-header"><div><p className="eyebrow">{t("crm.navigation.pipeline")}</p><h1>{t("pipeline.title")}</h1><p>{t("pipeline.subtitle")}</p></div></section>
    {error && <p className="form-error" role="alert">{error}</p>}
    {state === "loading" && <section className="content-surface"><div className="state-panel"><span className="loading-spinner" aria-hidden="true" /><p>{t("pipeline.loading")}</p></div></section>}
    {state === "error" && <section className="content-surface"><div className="state-panel"><p className="form-error">{t("pipeline.errors.load")}</p><button className="secondary-button" type="button" onClick={load}>{t("common.retry")}</button></div></section>}
    {state === "ready" && data.deals.length === 0 && <section className="content-surface"><div className="state-panel"><h2>{t("pipeline.empty.title")}</h2><p>{t("pipeline.empty.description")}</p></div></section>}
    {state === "ready" && data.deals.length > 0 && <section className="kanban-scroll" aria-label={t("pipeline.boardLabel")}><div className="kanban-board">{data.stages.map((stage) => {
      const deals = data.deals.filter((deal) => deal.stage_id === stage.id);
      return <section className={`kanban-column ${draggedDeal && draggedDeal.stage_id !== stage.id && canMove(draggedDeal) ? "is-drop-target" : ""}`} key={stage.id} onDragOver={(event) => { if (draggedDeal && canMove(draggedDeal)) event.preventDefault(); }} onDrop={(event) => drop(event, stage.id)}><header className="kanban-column-header"><h2>{pipelineStageLabel(t, stage)}</h2><span>{t("pipeline.dealCount", { count: deals.length })}</span></header><div className="kanban-cards">{deals.map((deal) => <article className={`kanban-card ${canMove(deal) ? "" : "is-readonly"}`} key={deal.id} draggable={canMove(deal)} onDragStart={(event) => dragStart(event, deal)} onDragEnd={() => setDraggedDeal(null)} onClick={() => onOpenDeal(deal.id)} title={canMove(deal) ? t("pipeline.cardMoveHint") : t("pipeline.readonlyHint")}><h3>{deal.name}</h3><p>{clientLabel(deal)}</p><dl><div><dt>{t("deals.fields.responsible")}</dt><dd>{employeeLabel(deal)}</dd></div>{deal.estimated_budget != null && <div><dt>{t("deals.fields.estimated_budget")}</dt><dd>{deal.estimated_budget}</dd></div>}{deal.probability != null && <div><dt>{t("deals.fields.probability")}</dt><dd>{deal.probability}%</dd></div>}{deal.deadline && <div><dt>{t("deals.fields.deadline")}</dt><dd>{formatDeadline(deal.deadline, locale)}</dd></div>}</dl>{canMove(deal) ? <button className="text-button kanban-move-button" type="button" onClick={(event) => { event.stopPropagation(); setMoveDeal(deal); }}>{t("pipeline.move")}</button> : <small>{t("pipeline.readonly")}</small>}</article>)}</div></section>;
    })}</div></section>}
    {moveDeal && <div className="modal-backdrop" role="presentation"><section className="client-modal move-modal" role="dialog" aria-modal="true" aria-labelledby="move-deal-title"><div className="modal-header"><div><p className="eyebrow">{t("pipeline.move")}</p><h2 id="move-deal-title">{moveDeal.name}</h2></div><button className="icon-button" type="button" onClick={() => setMoveDeal(null)} aria-label={t("common.close")}>×</button></div><form className="client-form" onSubmit={(event) => { event.preventDefault(); move(moveDeal, event.target.stage_id.value); }}><label className="field"><span>{t("pipeline.targetStage")}</span><select name="stage_id" defaultValue={moveDeal.stage_id} disabled={isMoving}>{data.stages.map((stage) => <option key={stage.id} value={stage.id}>{pipelineStageLabel(t, stage)}</option>)}</select></label><button className="primary-button" type="submit" disabled={isMoving}>{t("pipeline.move")}</button></form></section></div>}
  </>;
}


export default PipelinePage;
