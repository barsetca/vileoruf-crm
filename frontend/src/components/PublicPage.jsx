import { useState } from "react";
import { useTranslation } from "react-i18next";

import logoUrl from "../assets/vileoruf-logo.png";
import { createPublicRequest } from "../services/publicRequests.js";
import LanguageSwitcher from "./LanguageSwitcher.jsx";


const EMPTY_FORM = { name: "", contact_person: "", email: "", phone: "", telegram: "", whatsapp: "", company: "", deal_name: "", description: "", estimated_budget: "", deadline: "" };

function PublicPage({ onLogin }) {
  const { t } = useTranslation();
  const [form, setForm] = useState(EMPTY_FORM);
  const [state, setState] = useState("ready");

  async function submit(event) {
    event.preventDefault(); setState("loading");
    try {
      await createPublicRequest(Object.fromEntries(Object.entries(form).map(([key, value]) => [key, ["name", "deal_name"].includes(key) ? value.trim() : value.trim() || null])));
      setForm(EMPTY_FORM); setState("success");
    } catch { setState("error"); }
  }
  return <main className="public-shell"><header className="public-header"><div className="public-brand"><img className="brand-logo brand-logo--login" src={logoUrl} alt="" /><strong>VILEORUF</strong></div><div><LanguageSwitcher compact /><button className="text-button" type="button" onClick={onLogin}>{t("public.login")}</button></div></header><section className="public-card"><p className="eyebrow">{t("public.eyebrow")}</p><h1>{t("public.title")}</h1><p className="auth-intro">{t("public.subtitle")}</p>{state === "success" ? <div className="state-panel public-success"><h2>{t("public.success.title")}</h2><p>{t("public.success.description")}</p><button className="secondary-button" type="button" onClick={() => setState("ready")}>{t("public.success.again")}</button></div> : <form className="client-form" onSubmit={submit}><div className="client-form-grid">{[["name", "text", true], ["contact_person", "text"], ["email", "email"], ["phone", "text"], ["telegram", "text"], ["whatsapp", "text"], ["company", "text"], ["deal_name", "text", true], ["estimated_budget", "number"], ["deadline", "date"]].map(([field, type, required]) => <label className="field" key={field}><span>{t(`public.fields.${field}`)}{required && <em> *</em>}</span><input name={field} type={type} min={field === "estimated_budget" ? "0" : undefined} step={field === "estimated_budget" ? "0.01" : undefined} value={form[field]} onChange={(event) => setForm({ ...form, [field]: event.target.value })} disabled={state === "loading"} required={required} /></label>)}<label className="field field--full"><span>{t("public.fields.description")}</span><textarea name="description" rows="4" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} disabled={state === "loading"} /></label></div>{state === "error" && <p className="form-error" role="alert">{t("public.error")}</p>}<button className="primary-button" type="submit" disabled={state === "loading"}>{t(state === "loading" ? "public.sending" : "public.send")}</button></form>}</section></main>;
}

export default PublicPage;
