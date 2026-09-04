import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import { getAIHistory } from "../services/aiHistory.js";
import { listDeals } from "../services/deals.js";
import AIHistoryList from "./AIHistoryList.jsx";

const PAGE_SIZE = 20;
const initialFilters = { function_type:"", status:"", deal_id:"", freshness:"", current_only:false };

function AIHistoryPage() {
  const { t } = useTranslation(); const { accessToken } = useAuth();
  const [filters, setFilters] = useState(initialFilters); const [offset, setOffset] = useState(0); const [page, setPage] = useState(null); const [deals, setDeals] = useState([]); const [state, setState] = useState("loading");
  const load = useCallback(async (nextOffset = offset) => { setState("loading"); try { const query = { function_type:filters.function_type, status:filters.status, deal_id:filters.deal_id, current_only:filters.current_only, limit:PAGE_SIZE, offset:nextOffset }; if (filters.freshness !== "") query.is_outdated = filters.freshness === "outdated"; const [result, references] = await Promise.all([getAIHistory(accessToken, query), listDeals(accessToken, { limit:100, offset:0 })]); setPage(result); setDeals(references); setOffset(nextOffset); setState("ready"); } catch { setState("error"); } }, [accessToken, filters, offset]);
  useEffect(() => { load(0); }, [accessToken]);
  const edit = (field, value) => setFilters((current) => ({ ...current, [field]:value }));
  return <><section className="page-header"><div><p className="eyebrow">AI</p><h1>{t("aiHistory.title")}</h1><p>{t("aiHistory.subtitle")}</p></div></section><section className="content-surface"><div className="history-filters"><label className="field"><span>{t("aiHistory.function")}</span><select value={filters.function_type} onChange={(event) => edit("function_type", event.target.value)}><option value="">{t("aiHistory.all")}</option>{["LEAD_SCORING","DEAL_PREDICTION","NEXT_BEST_ACTION","EMAIL_DRAFT"].map((type) => <option key={type} value={type}>{t(`aiHistory.functions.${type}`)}</option>)}</select></label><label className="field"><span>{t("aiHistory.technicalStatus")}</span><select value={filters.status} onChange={(event) => edit("status", event.target.value)}><option value="">{t("aiHistory.all")}</option>{["QUEUED","RUNNING","SUCCESS","FAILED"].map((status) => <option key={status} value={status}>{t(`aiHistory.status.${status}`)}</option>)}</select></label><label className="field"><span>{t("aiHistory.deal")}</span><select value={filters.deal_id} onChange={(event) => edit("deal_id", event.target.value)}><option value="">{t("aiHistory.all")}</option>{deals.map((deal) => <option key={deal.id} value={deal.id}>{deal.name}</option>)}</select></label><label className="field"><span>{t("aiHistory.freshness")}</span><select value={filters.freshness} onChange={(event) => edit("freshness", event.target.value)}><option value="">{t("aiHistory.all")}</option><option value="fresh">{t("aiHistory.fresh")}</option><option value="outdated">{t("aiHistory.outdated")}</option></select></label><label className="settings-toggle"><input type="checkbox" checked={filters.current_only} onChange={(event) => edit("current_only", event.target.checked)} /><span>{t("aiHistory.currentOnly")}</span></label><button className="primary-button" type="button" onClick={() => load(0)}>{t("aiHistory.apply")}</button></div>{state === "loading" ? <div className="state-panel"><span className="loading-spinner" /></div> : state === "error" ? <p className="form-error">{t("aiHistory.error")}</p> : <><AIHistoryList items={page.items} /><nav className="pagination"><button className="secondary-button" disabled={!offset} onClick={() => load(Math.max(0, offset-PAGE_SIZE))}>{t("deals.pagination.previous")}</button><span>{offset+1}–{Math.min(offset+PAGE_SIZE,page.total)} / {page.total}</span><button className="secondary-button" disabled={offset+PAGE_SIZE >= page.total} onClick={() => load(offset+PAGE_SIZE)}>{t("deals.pagination.next")}</button></nav></>}</section></>;
}

export default AIHistoryPage;
