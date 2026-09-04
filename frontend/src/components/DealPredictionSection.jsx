import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext.jsx";
import { getDealPrediction, launchDealPrediction } from "../services/dealPrediction.js";

function DealPredictionSection({ deal, canRun, isClosed }) {
  const { t, i18n } = useTranslation(); const { accessToken } = useAuth();
  const [overview, setOverview] = useState(null); const [state, setState] = useState("loading");
  const load = useCallback(async () => { if (!canRun) { setOverview(null); setState("ready"); return; } try { setOverview(await getDealPrediction(accessToken, deal.id)); setState("ready"); } catch { setState("error"); } }, [accessToken, canRun, deal.id]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!overview?.active) return; const timer=window.setInterval(load,2500); return () => clearInterval(timer); }, [overview?.active,load]);
  async function launch() { setState("launching"); try { await launchDealPrediction(accessToken, deal.id, i18n.resolvedLanguage ?? "ru"); await load(); } catch { setState("error"); } }
  const analysis=overview?.current; const result=analysis?.result_payload;
  return <section className="deal-prediction"><div className="section-heading"><div><p className="eyebrow">AI</p><h3>{t("dealPrediction.title")}</h3></div>{canRun && !isClosed && <button className="primary-button" type="button" onClick={launch} disabled={state==="launching"||overview?.active}>{t(analysis ? "dealPrediction.recalculate":"dealPrediction.run")}</button>}</div>
    <p className="readonly-note">{t("dealPrediction.confidenceHelp")}</p>{state==="loading"&&<p>{t("dealPrediction.loading")}</p>}{state==="error"&&<p className="form-error">{t("dealPrediction.error")}</p>}{overview?.active&&<p className="status-note">{t(`dealPrediction.status.${overview.active.status}`)}</p>}{overview?.latest_attempt?.status==="FAILED"&&<p className="form-error">{t("dealPrediction.failed")}</p>}{isClosed&&<p className="readonly-note">{t("dealPrediction.closed")}</p>}
    {!analysis&&state==="ready"&&!overview?.active&&<p className="readonly-note">{t("dealPrediction.empty")}</p>}{result&&<><div className="prediction-metrics"><article><span>{t("dealPrediction.probability")}</span><strong>{result.probability_won}%</strong></article><article><span>{t("dealPrediction.confidence")}</span><strong className={`confidence-badge confidence-badge--${result.confidence}`}>{t(`dealPrediction.confidenceValues.${result.confidence}`)}</strong></article></div><small>{analysis.is_outdated?t("dealPrediction.outdated"):t("dealPrediction.fresh")}</small><p className="ai-summary">{result.summary}</p>{[["positive",result.positive_signals],["risks",result.risks],["missing",result.missing_context]].map(([key,items]) => items.length>0&&<div className="warning-box" key={key}><strong>{t(`dealPrediction.${key}`)}</strong><ul>{items.map((x,i)=><li key={i}>{x}</li>)}</ul></div>)}{result.security_warning&&<div className="warning-box warning-box--security"><strong>{t("dealPrediction.security")}</strong><p>{result.security_warning}</p></div>}<p className="analysis-meta">{t("dealPrediction.language")}: {analysis.language} · {new Intl.DateTimeFormat(i18n.resolvedLanguage,{dateStyle:"medium",timeStyle:"short"}).format(new Date(analysis.finished_at||analysis.created_at))}</p></>}
  </section>;
}
export default DealPredictionSection;
