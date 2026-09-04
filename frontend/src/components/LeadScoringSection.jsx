import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import { getLeadScoring, launchLeadScoring } from "../services/leadScoring.js";


function LeadScoringSection({ deal, canRun, isClosed }) {
  const { t, i18n } = useTranslation();
  const { accessToken } = useAuth();
  const [overview, setOverview] = useState(null);
  const [state, setState] = useState("loading");
  const load = useCallback(async () => { if (!canRun) { setOverview(null); setState("ready"); return; } try { setOverview(await getLeadScoring(accessToken, deal.id)); setState("ready"); } catch { setState("error"); } }, [accessToken, canRun, deal.id]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!overview?.active) return; const timer = window.setInterval(load, 2500); return () => clearInterval(timer); }, [overview?.active, load]);
  async function launch() { setState("launching"); try { await launchLeadScoring(accessToken, deal.id, i18n.resolvedLanguage ?? "ru"); await load(); } catch { setState("error"); } }
  const analysis = overview?.current;
  const result = analysis?.result_payload;
  const factors = result ? [["serviceFit", result.service_fit], ["commercialValue", result.commercial_value], ["leadQuality", result.lead_quality], ["feasibility", result.feasibility]] : [];
  return <section className="lead-scoring"><div className="section-heading"><div><p className="eyebrow">AI</p><h3>{t("leadScoring.title")}</h3></div>{canRun && !isClosed && <button className="primary-button" type="button" onClick={launch} disabled={state === "launching" || overview?.active}>{t(analysis ? "leadScoring.recalculate":"leadScoring.run")}</button>}</div>
    {state === "loading" && <p>{t("leadScoring.loading")}</p>}{state === "error" && <p className="form-error">{t("leadScoring.error")}</p>}{overview?.active && <p className="status-note">{t(`leadScoring.status.${overview.active.status}`)}</p>}{overview?.latest_attempt?.status === "FAILED" && <p className="form-error">{t("leadScoring.failed")}</p>}{isClosed && <p className="readonly-note">{t("leadScoring.closed")}</p>}
    {!analysis && state === "ready" && !overview?.active && <p className="readonly-note">{t("leadScoring.empty")}</p>}
    {result && <><div className="score-hero"><strong>{result.overall_score}</strong><span>/100</span><small>{analysis.is_outdated ? t("leadScoring.outdated") : t("leadScoring.fresh")}</small></div><div className="factor-grid">{factors.map(([key, factor]) => <article key={key} className={key === "commercialValue" && factor.status === "NO_BUDGET" ? "factor-card factor-card--missing":"factor-card"}><div><strong>{t(`leadScoring.factors.${key}`)}</strong><span>{factor.score}/100</span></div><p>{factor.explanation}</p></article>)}</div><p className="ai-summary">{result.summary}</p>{result.missing_data.length > 0 && <div className="warning-box"><strong>{t("leadScoring.missing")}</strong><ul>{result.missing_data.map((item) => <li key={item}>{t(`leadScoring.missingItems.${item}`, { defaultValue:item })}</li>)}</ul></div>}{result.security_warning && <div className="warning-box warning-box--security"><strong>{t("leadScoring.security")}</strong><p>{result.security_warning}</p></div>}{result.category_suggestion && <div className="warning-box"><strong>{t("leadScoring.suggestion")}: {result.category_suggestion.category_name}</strong><p>{result.category_suggestion.reason}</p></div>}<p className="analysis-meta">{t("leadScoring.language")}: {analysis.language} · {new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle:"medium", timeStyle:"short" }).format(new Date(analysis.finished_at || analysis.created_at))}</p></>}
  </section>;
}


export default LeadScoringSection;
