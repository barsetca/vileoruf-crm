import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext.jsx";
import { getAIHistory } from "../services/aiHistory.js";
import AIHistoryList from "./AIHistoryList.jsx";

function DealAIHistorySection({ dealId }) {
  const { t } = useTranslation(); const { accessToken } = useAuth(); const [page, setPage] = useState(null); const [error, setError] = useState(false);
  useEffect(() => { const controller = new AbortController(); getAIHistory(accessToken, { dealPath:dealId, limit:20, offset:0 }, controller.signal).then(setPage).catch((reason) => { if (reason.name !== "AbortError") setError(true); }); return () => controller.abort(); }, [accessToken, dealId]);
  return <details className="next-best-action"><summary><strong>{t("aiHistory.dealTitle")}</strong></summary>{error ? <p className="form-error">{t("aiHistory.error")}</p> : !page ? <p>{t("aiHistory.loading")}</p> : <AIHistoryList items={page.items} />}</details>;
}
export default DealAIHistorySection;
