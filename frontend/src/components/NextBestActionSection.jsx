import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import { getNextBestAction, launchNextBestAction } from "../services/nextBestAction.js";


function NextBestActionSection({ deal, canRun, isClosed }) {
  const { t, i18n } = useTranslation();
  const { accessToken } = useAuth();
  const [overview, setOverview] = useState(null);
  const [state, setState] = useState("loading");
  const load = useCallback(async () => {
    if (!canRun) { setOverview(null); setState("ready"); return; }
    try {
      setOverview(await getNextBestAction(accessToken, deal.id));
      setState("ready");
    } catch {
      setState("error");
    }
  }, [accessToken, canRun, deal.id]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!overview?.active && !overview?.waiting_for_initial_analyses) return;
    const timer = window.setInterval(load, 2500);
    return () => clearInterval(timer);
  }, [overview?.active, overview?.waiting_for_initial_analyses, load]);
  async function launch() {
    setState("launching");
    try {
      await launchNextBestAction(accessToken, deal.id, i18n.resolvedLanguage ?? "ru");
      await load();
    } catch {
      setState("error");
    }
  }
  const analysis = overview?.current;
  const result = analysis?.result_payload;
  return <section className="next-best-action">
    <div className="section-heading"><div><p className="eyebrow">AI</p><h3>{t("nextBestAction.title")}</h3></div>{canRun && !isClosed && <button className="primary-button" type="button" onClick={launch} disabled={state === "launching" || overview?.active}>{t(analysis ? "nextBestAction.recalculate" : "nextBestAction.run")}</button>}</div>
    <p className="readonly-note">{t("nextBestAction.advisory")}</p>
    {state === "loading" && <p>{t("nextBestAction.loading")}</p>}
    {state === "error" && <p className="form-error">{t("nextBestAction.error")}</p>}
    {overview?.waiting_for_initial_analyses && <p className="status-note">{t("nextBestAction.waiting")}</p>}
    {overview?.active && <p className="status-note">{t(`nextBestAction.status.${overview.active.status}`)}</p>}
    {overview?.latest_attempt?.status === "FAILED" && <p className="form-error">{t("nextBestAction.failed")}</p>}
    {isClosed && <p className="readonly-note">{t("nextBestAction.closed")}</p>}
    {!analysis && state === "ready" && !overview?.active && !overview?.waiting_for_initial_analyses && <p className="readonly-note">{t("nextBestAction.empty")}</p>}
    {result && <>
      <small>{analysis.is_outdated ? t("nextBestAction.outdated") : t("nextBestAction.fresh")}</small>
      <p className="ai-summary">{result.summary}</p>
      <div className="action-list">{result.actions.map((item) => <article className="action-card" key={item.rank}>
        <div><span className="action-rank">{item.rank}</span><strong>{item.action}</strong><span className={`priority-badge priority-badge--${item.priority}`}>{t(`nextBestAction.priorities.${item.priority}`)}</span></div>
        <p>{item.reason}</p><small>{t("nextBestAction.timing")}: {item.timing}</small>
      </article>)}</div>
      {result.security_warning && <div className="warning-box warning-box--security"><strong>{t("nextBestAction.security")}</strong><p>{result.security_warning}</p></div>}
      <p className="analysis-meta">{t("nextBestAction.language")}: {analysis.language} · {new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium", timeStyle: "short" }).format(new Date(analysis.finished_at || analysis.created_at))}</p>
    </>}
  </section>;
}


export default NextBestActionSection;
