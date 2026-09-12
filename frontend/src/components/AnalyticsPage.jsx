import { useCallback, useEffect, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext.jsx";
import { getAnalyticsSummary } from "../services/analytics.js";

function Help({ text, label }) {
  const [open, setOpen] = useState(false); const id = useId();
  const onKeyDown = (event) => {
    if (event.key === "Escape") { setOpen(false); event.currentTarget.blur(); return; }
    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setOpen((value) => !value); }
  };
  return <span className="analytics-help"><button type="button" className="analytics-help__button" aria-label={label} aria-expanded={open} aria-controls={id} onClick={() => setOpen((value) => !value)} onBlur={() => setOpen(false)} onKeyDown={onKeyDown}>i</button>{open && <span id={id} role="tooltip" className="analytics-help__popover">{text}</span>}</span>;
}

function LineChart({ items, locale, emptyText }) {
  if (!items.length) return <div className="analytics-chart-empty">{emptyText}</div>;
  const width = 640, height = 210, pad = 30, max = Math.max(...items.map((item) => item.deal_count), 1);
  const points = items.map((item, index) => `${pad + (index * (width - pad * 2) / Math.max(items.length - 1, 1))},${height - pad - (item.deal_count / max) * (height - pad * 2)}`).join(" ");
  const label = (item) => new Intl.DateTimeFormat(locale, { month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(item.month_start));
  return <div className="analytics-chart" role="img" aria-label={items.map((item) => `${label(item)}: ${item.deal_count}`).join(", ")}><svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" aria-hidden="true"><line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} /><polyline points={points} /></svg><div className="analytics-chart__labels">{items.map((item) => <span key={item.month_start}>{label(item)}<strong>{item.deal_count}</strong></span>)}</div></div>;
}

export default function AnalyticsPage() {
  const { t, i18n } = useTranslation(); const { accessToken } = useAuth(); const [summary, setSummary] = useState(null); const [state, setState] = useState("loading");
  const load = useCallback(() => { const controller = new AbortController(); setState("loading"); getAnalyticsSummary(accessToken, controller.signal).then((value) => { setSummary(value); setState("ready"); }).catch((error) => { if (error.name !== "AbortError") setState("error"); }); return controller; }, [accessToken]);
  useEffect(() => { const controller = load(); return () => controller.abort(); }, [load]);
  const locale = i18n.resolvedLanguage ?? "ru";
  const integer = (value) => new Intl.NumberFormat(locale).format(value);
  const money = (value) => new Intl.NumberFormat(locale, { style: "currency", currency: "EUR" }).format(value);
  const percent = (value) => value === null ? "—" : new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 2 }).format(Number(value) / 100);
  const card = (key, value) => <article className="analytics-kpi" key={key}><div><h2>{t(`analytics.kpis.${key}.title`)} <Help label={t("analytics.helpLabel", { title: t(`analytics.kpis.${key}.title`) })} text={t(`analytics.kpis.${key}.help`)} /></h2><strong>{value}</strong></div></article>;
  return <><section className="page-header"><div><p className="eyebrow">CRM</p><h1>{t("analytics.title")}</h1><p>{t("analytics.subtitle")}</p></div></section><section className="content-surface analytics-surface" aria-live="polite">{state === "loading" && <div className="state-panel"><span className="loading-spinner" /><p>{t("analytics.loading")}</p></div>}{state === "error" && <div className="state-panel"><p className="form-error">{t("analytics.error")}</p><button className="secondary-button" type="button" onClick={load}>{t("common.retry")}</button></div>}{state === "ready" && <><div className="analytics-kpis">{card("clientsTotal", integer(summary.clients.total))}{card("customer", integer(summary.clients.customer))}{card("client", integer(summary.clients.client))}{card("dealsTotal", integer(summary.deals.total))}{card("active", integer(summary.deals.active))}{card("won", integer(summary.deals.won))}{card("lost", integer(summary.deals.lost))}{card("pipelineValue", money(summary.active_pipeline_estimated_value))}{card("wonValue", money(summary.won_deals_estimated_value))}{card("conversion", percent(summary.closed_deal_conversion_percent))}</div><section className="analytics-section"><h2>{t("analytics.breakdown.title")} <Help label={t("analytics.helpLabel", { title: t("analytics.breakdown.title") })} text={t("analytics.breakdown.help")} /></h2><div className="analytics-table-wrap"><table><thead><tr><th>{t("analytics.breakdown.stage")}</th><th>{t("analytics.breakdown.deals")}</th><th>{t("analytics.breakdown.value")}</th></tr></thead><tbody>{summary.pipeline_stages.map((stage) => <tr key={stage.stage_id}><td>{stage.stage_name}</td><td>{integer(stage.deal_count)}</td><td>{money(stage.estimated_value)}</td></tr>)}</tbody></table></div></section><div className="analytics-charts">{[["created", summary.created_deals_by_month], ["firstWon", summary.first_won_deals_by_month]].map(([key, items]) => <section className="analytics-section analytics-section--chart" key={key}><h2>{t(`analytics.charts.${key}.title`)} <Help label={t("analytics.helpLabel", { title: t(`analytics.charts.${key}.title`) })} text={t(`analytics.charts.${key}.help`)} /></h2><LineChart items={items} locale={locale} emptyText={t("analytics.charts.empty")} /></section>)}</div></>}</section></>;
}
