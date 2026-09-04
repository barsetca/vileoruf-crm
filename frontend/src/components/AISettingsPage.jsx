import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import { getAISettings, updateAISettings } from "../services/aiSettings.js";

function AISettingsPage() {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [settings, setSettings] = useState(null);
  const [state, setState] = useState("loading");
  async function load() { setState("loading"); try { setSettings(await getAISettings(accessToken)); setState("ready"); } catch { setState("error"); } }
  useEffect(() => { load(); }, [accessToken]);
  async function save(event) {
    event.preventDefault(); setState("saving");
    try {
      setSettings(await updateAISettings(accessToken, {
        ai_enabled: settings.ai_enabled,
        automatic_new_deal_analysis: settings.automatic_new_deal_analysis,
        analysis_model_override: settings.analysis_model_override || null,
        email_model_override: settings.email_model_override || null,
        deal_prediction_validity_days: Number(settings.deal_prediction_validity_days),
        next_best_action_validity_days: Number(settings.next_best_action_validity_days),
      })); setState("saved");
    } catch { setState("error"); }
  }
  const edit = (field, value) => setSettings((current) => ({ ...current, [field]: value }));
  return <><section className="page-header"><div><p className="eyebrow">AI</p><h1>{t("aiSettings.title")}</h1><p>{t("aiSettings.subtitle")}</p></div></section>
    {state === "loading" ? <div className="state-panel"><span className="loading-spinner" /><p>{t("aiSettings.loading")}</p></div> : !settings ? <div className="state-panel"><p className="form-error">{t("aiSettings.error")}</p><button className="secondary-button" onClick={load}>{t("common.retry")}</button></div> : <form className="content-surface settings-card ai-settings-form" onSubmit={save}>
      <label className="settings-toggle"><input type="checkbox" checked={settings.ai_enabled} onChange={(event) => edit("ai_enabled", event.target.checked)} /><span><strong>{t("aiSettings.enabled")}</strong><small>{t("aiSettings.enabledHelp")}</small></span></label>
      <label className="settings-toggle"><input type="checkbox" checked={settings.automatic_new_deal_analysis} onChange={(event) => edit("automatic_new_deal_analysis", event.target.checked)} /><span><strong>{t("aiSettings.automatic")}</strong><small>{t("aiSettings.automaticHelp")}</small></span></label>
      <div className="client-form-grid"><label className="field"><span>{t("aiSettings.analysisModel")}</span><select value={settings.analysis_model_override ?? ""} onChange={(event) => edit("analysis_model_override", event.target.value || null)}><option value="">{t("aiSettings.defaultModel", { model: settings.default_analysis_model })}</option>{settings.allowed_models.map((model) => <option key={model} value={model}>{model}</option>)}</select><small>{t("aiSettings.analysisHelp")} · {t("aiSettings.effective", { model: settings.effective_analysis_model })}</small></label>
      <label className="field"><span>{t("aiSettings.emailModel")}</span><select value={settings.email_model_override ?? ""} onChange={(event) => edit("email_model_override", event.target.value || null)}><option value="">{t("aiSettings.defaultModel", { model: settings.default_email_model })}</option>{settings.allowed_models.map((model) => <option key={model} value={model}>{model}</option>)}</select><small>{t("aiSettings.emailHelp")} · {t("aiSettings.effective", { model: settings.effective_email_model })}</small></label>
      <label className="field"><span>{t("aiSettings.dpValidity")}</span><input type="number" min="1" max="365" value={settings.deal_prediction_validity_days} onChange={(event) => edit("deal_prediction_validity_days", event.target.value)} /><small>{t("aiSettings.validityHelp")}</small><button className="text-button" type="button" onClick={() => edit("deal_prediction_validity_days", settings.default_deal_prediction_validity_days)}>{t("common.resetDefault", { value:settings.default_deal_prediction_validity_days })}</button></label>
      <label className="field"><span>{t("aiSettings.nbaValidity")}</span><input type="number" min="1" max="365" value={settings.next_best_action_validity_days} onChange={(event) => edit("next_best_action_validity_days", event.target.value)} /><small>{t("aiSettings.validityHelp")}</small><button className="text-button" type="button" onClick={() => edit("next_best_action_validity_days", settings.default_next_best_action_validity_days)}>{t("common.resetDefault", { value:settings.default_next_best_action_validity_days })}</button></label></div>
      {state === "error" && <p className="form-error">{t("aiSettings.error")}</p>}{state === "saved" && <p className="status-note">{t("aiSettings.saved")}</p>}<button className="primary-button" disabled={state === "saving"}>{t(state === "saving" ? "common.saving" : "common.save")}</button>
    </form>}
  </>;
}

export default AISettingsPage;
