import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import { listCommunications } from "../services/communications.js";
import { listEmployeeReferences } from "../services/referenceData.js";
import { listTasks } from "../services/tasks.js";


const PREVIEW_LIMIT = 5;

function formatDateTime(value, locale) {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function communicationPreview(content) {
  return content.length > 140 ? `${content.slice(0, 140)}…` : content;
}

function DashboardPage({ onNavigate }) {
  const { t, i18n } = useTranslation();
  const { accessToken, user } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [communications, setCommunications] = useState([]);
  const [tasksState, setTasksState] = useState("loading");
  const [communicationsState, setCommunicationsState] = useState("loading");
  const locale = i18n.resolvedLanguage ?? "ru";

  const loadTasks = useCallback(() => {
    const controller = new AbortController();
    setTasksState("loading");
    Promise.all([
      listTasks(accessToken, { limit: PREVIEW_LIMIT, offset: 0, status: "OPEN" }, controller.signal),
      listEmployeeReferences(accessToken, controller.signal),
    ]).then(([nextTasks, nextEmployees]) => {
      setTasks(nextTasks); setEmployees(nextEmployees); setTasksState("ready");
    }).catch((error) => { if (error.name !== "AbortError") setTasksState("error"); });
    return controller;
  }, [accessToken]);

  const loadCommunications = useCallback(() => {
    const controller = new AbortController();
    setCommunicationsState("loading");
    listCommunications(accessToken, { limit: PREVIEW_LIMIT, offset: 0 }, controller.signal)
      .then((nextCommunications) => { setCommunications(nextCommunications); setCommunicationsState("ready"); })
      .catch((error) => { if (error.name !== "AbortError") setCommunicationsState("error"); });
    return controller;
  }, [accessToken]);

  useEffect(() => {
    const controller = loadTasks();
    return () => controller.abort();
  }, [loadTasks]);

  useEffect(() => {
    const controller = loadCommunications();
    return () => controller.abort();
  }, [loadCommunications]);

  const employeeLabels = useMemo(() => new Map(employees.map((employee) => [employee.id, employee.display_name])), [employees]);
  const isOverdue = (task) => task.status === "OPEN" && new Date(task.due_at) < new Date();

  return <>
    <section className="page-header dashboard-header"><div><p className="eyebrow">{t("dashboard.eyebrow")}</p><h1>{t("dashboard.greeting", { name: user.display_name })}</h1><p>{t("dashboard.subtitle")}</p></div></section>
    <section className="dashboard-grid">
      <section className="content-surface dashboard-section" aria-live="polite"><header className="dashboard-section-header"><div><h2>{t("dashboard.tasks.title")}</h2><p>{t("dashboard.tasks.subtitle")}</p></div><button className="text-button" type="button" onClick={() => onNavigate("/crm/tasks")}>{t("dashboard.tasks.viewAll")}</button></header>
        {tasksState === "loading" && <div className="dashboard-state"><span className="loading-spinner" aria-hidden="true" /><p>{t("dashboard.tasks.loading")}</p></div>}
        {tasksState === "error" && <div className="dashboard-state"><p className="form-error">{t("dashboard.tasks.error")}</p><button className="secondary-button" type="button" onClick={loadTasks}>{t("common.retry")}</button></div>}
        {tasksState === "ready" && tasks.length === 0 && <div className="dashboard-state"><p>{t("dashboard.tasks.empty")}</p></div>}
        {tasksState === "ready" && tasks.length > 0 && <ol className="dashboard-list">{tasks.map((task) => <li key={task.id}><div><strong>{task.title}</strong><p>{employeeLabels.get(task.responsible_user_id) ?? t("dashboard.unknownEmployee")}</p></div><div className="dashboard-item-time"><time dateTime={task.due_at}>{formatDateTime(task.due_at, locale)}</time>{isOverdue(task) && <span className="task-overdue">{t("tasks.status.OVERDUE")}</span>}</div></li>)}</ol>}
      </section>
      <section className="content-surface dashboard-section" aria-live="polite"><header className="dashboard-section-header"><div><h2>{t("dashboard.communications.title")}</h2><p>{t("dashboard.communications.subtitle")}</p></div></header>
        {communicationsState === "loading" && <div className="dashboard-state"><span className="loading-spinner" aria-hidden="true" /><p>{t("dashboard.communications.loading")}</p></div>}
        {communicationsState === "error" && <div className="dashboard-state"><p className="form-error">{t("dashboard.communications.error")}</p><button className="secondary-button" type="button" onClick={loadCommunications}>{t("common.retry")}</button></div>}
        {communicationsState === "ready" && communications.length === 0 && <div className="dashboard-state"><p>{t("dashboard.communications.empty")}</p></div>}
        {communicationsState === "ready" && communications.length > 0 && <ol className="dashboard-list">{communications.map((communication) => <li key={communication.id}><div><p className="dashboard-communication-meta">{t(`communications.channels.${communication.channel}`)} · {t(`communications.directions.${communication.direction}`)}</p><strong>{communicationPreview(communication.content)}</strong></div><time dateTime={communication.occurred_at}>{formatDateTime(communication.occurred_at, locale)}</time></li>)}</ol>}
      </section>
    </section>
    <section className="content-surface dashboard-quick"><h2>{t("dashboard.quick.title")}</h2><div>{[["/crm/clients", "clients", "◫"], ["/crm/deals", "deals", "◇"], ["/crm/pipeline", "pipeline", "▤"], ["/crm/tasks", "tasks", "✓"]].map(([path, label, icon]) => <button key={path} className="secondary-button dashboard-quick-link" type="button" onClick={() => onNavigate(path)}><span aria-hidden="true">{icon}</span>{t(`crm.navigation.${label}`)}</button>)}</div></section>
  </>;
}


export default DashboardPage;
