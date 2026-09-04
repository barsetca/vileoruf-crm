import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import { createCategory, createService, getLeadScoringSettings, listCategories, listServices, updateCategory, updateLeadScoringSettings, updateService } from "../services/business.js";


const categoryBlank = { name_ru:"", name_en:"", name_es:"", target_hourly_rate:"", target_effort:"" };
const serviceBlank = { name_ru:"", name_en:"", name_es:"", category_id:"" };


function BusinessSettingsPage() {
  const { t, i18n } = useTranslation();
  const { accessToken } = useAuth();
  const [data, setData] = useState({ categories:[], services:[], settings:null });
  const [category, setCategory] = useState(categoryBlank);
  const [service, setService] = useState(serviceBlank);
  const [state, setState] = useState("loading");
  const lang = i18n.resolvedLanguage ?? "ru";
  const name = (item) => item[`name_${lang}`] || item.name_ru;
  const categoryMap = useMemo(() => new Map(data.categories.map((item) => [item.id, item])), [data.categories]);

  async function load() {
    setState("loading");
    try { const [categories, services, settings] = await Promise.all([listCategories(accessToken), listServices(accessToken), getLeadScoringSettings(accessToken)]); setData({ categories, services, settings }); setService((old) => ({ ...old, category_id: old.category_id || categories.find((item) => item.is_active)?.id || "" })); setState("ready"); }
    catch { setState("error"); }
  }
  useEffect(() => { load(); }, [accessToken]);
  async function addCategory(event) { event.preventDefault(); try { await createCategory(accessToken, category); setCategory(categoryBlank); await load(); } catch { setState("error"); } }
  async function addService(event) { event.preventDefault(); try { await createService(accessToken, service); setService({ ...serviceBlank, category_id:data.categories.find((item) => item.is_active)?.id || "" }); await load(); } catch { setState("error"); } }
  async function toggleCategory(item) { await updateCategory(accessToken, item.id, { is_active:!item.is_active }); await load(); }
  async function toggleService(item) { await updateService(accessToken, item.id, { is_active:!item.is_active }); await load(); }
  async function saveCategory(item) { await updateCategory(accessToken, item.id, { name_ru:item.name_ru, name_en:item.name_en, name_es:item.name_es, target_hourly_rate:item.target_hourly_rate, target_effort:item.target_effort }); await load(); }
  async function saveService(item) { await updateService(accessToken, item.id, { name_ru:item.name_ru, name_en:item.name_en, name_es:item.name_es, category_id:item.category_id }); await load(); }
  const editCategory = (id, field, value) => setData((old) => ({ ...old, categories:old.categories.map((item) => item.id === id ? {...item,[field]:value}:item) }));
  const editService = (id, field, value) => setData((old) => ({ ...old, services:old.services.map((item) => item.id === id ? {...item,[field]:value}:item) }));
  async function saveSettings(event) { event.preventDefault(); try { const { service_fit_weight, commercial_value_weight, lead_quality_weight, feasibility_weight, commercial_value_scale } = data.settings; await updateLeadScoringSettings(accessToken, { service_fit_weight, commercial_value_weight, lead_quality_weight, feasibility_weight, commercial_value_scale }); await load(); } catch { setState("error"); } }
  const editSettings = (key, value) => setData((old) => ({ ...old, settings:{ ...old.settings, [key]:value } }));

  return <><section className="page-header"><div><p className="eyebrow">{t("business.eyebrow")}</p><h1>{t("business.title")}</h1><p>{t("business.subtitle")}</p></div></section>
    {state === "loading" ? <div className="state-panel"><span className="loading-spinner" /><p>{t("business.loading")}</p></div> : state === "error" ? <div className="state-panel"><p className="form-error">{t("business.error")}</p><button className="secondary-button" onClick={load}>{t("common.retry")}</button></div> : <div className="settings-grid">
      <section className="content-surface settings-card"><h2>{t("business.categories")}</h2><form className="compact-form" onSubmit={addCategory}>{["name_ru","name_en","name_es","target_hourly_rate","target_effort"].map((field) => <label className="field" key={field}><span>{t(`business.fields.${field}`)}</span><input type={field.startsWith("target") ? "number":"text"} min={field.startsWith("target") ? "0.01":undefined} step={field.startsWith("target") ? "0.01":undefined} value={category[field]} onChange={(e) => setCategory({ ...category, [field]:e.target.value })} required /></label>)}<button className="primary-button">{t("business.addCategory")}</button></form><div className="settings-list">{data.categories.map((item) => <article key={item.id}><div><span className="inline-config inline-config--names">{["name_ru","name_en","name_es"].map((field) => <input key={field} aria-label={t(`business.fields.${field}`)} value={item[field]} onChange={(e) => editCategory(item.id,field,e.target.value)} required />)}</span><span className="inline-config"><input aria-label={t("business.fields.target_hourly_rate")} type="number" min="0.01" step="0.01" value={item.target_hourly_rate} onChange={(e) => editCategory(item.id,"target_hourly_rate",e.target.value)} /><input aria-label={t("business.fields.target_effort")} type="number" min="0.01" step="0.01" value={item.target_effort} onChange={(e) => editCategory(item.id,"target_effort",e.target.value)} /></span><small>{Number(item.target_effort)/8}d</small></div><span><button className="secondary-button" onClick={() => saveCategory(item)}>{t("common.save")}</button><button className="secondary-button" onClick={() => toggleCategory(item)}>{t(`business.${item.is_active ? "deactivate":"activate"}`)}</button></span></article>)}</div></section>
      <section className="content-surface settings-card"><h2>{t("business.services")}</h2><form className="compact-form" onSubmit={addService}>{["name_ru","name_en","name_es"].map((field) => <label className="field" key={field}><span>{t(`business.fields.${field}`)}</span><input value={service[field]} onChange={(e) => setService({ ...service, [field]:e.target.value })} required /></label>)}<label className="field"><span>{t("business.category")}</span><select value={service.category_id} onChange={(e) => setService({ ...service, category_id:e.target.value })} required>{data.categories.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{name(item)}</option>)}</select></label><button className="primary-button">{t("business.addService")}</button></form><div className="settings-list">{data.services.map((item) => <article key={item.id}><div><span className="inline-config inline-config--names">{["name_ru","name_en","name_es"].map((field) => <input key={field} aria-label={t(`business.fields.${field}`)} value={item[field]} onChange={(e) => editService(item.id,field,e.target.value)} required />)}</span><select value={item.category_id} onChange={(e) => editService(item.id,"category_id",e.target.value)}>{data.categories.filter((category) => category.is_active || category.id === item.category_id).map((category) => <option key={category.id} value={category.id}>{name(category)}</option>)}</select></div><span><button className="secondary-button" onClick={() => saveService(item)}>{t("common.save")}</button><button className="secondary-button" onClick={() => toggleService(item)}>{t(`business.${item.is_active ? "deactivate":"activate"}`)}</button></span></article>)}</div></section>
      <section className="content-surface settings-card settings-card--wide"><h2>{t("business.scoring")}</h2><form className="compact-form compact-form--row" onSubmit={saveSettings}>{["service_fit_weight","commercial_value_weight","lead_quality_weight","feasibility_weight"].map((field) => <label className="field" key={field}><span>{t(`business.fields.${field}`)}</span><input type="number" min="0" max="100" value={data.settings[field]} onChange={(e) => editSettings(field, Number(e.target.value))} /></label>)}<div className="field field--full"><span>{t("business.scale")}</span><div className="scale-fields">{data.settings.commercial_value_scale.map((point, index) => <span key={index}><input aria-label="ratio" type="number" step="0.01" value={point.ratio} onChange={(e) => editSettings("commercial_value_scale", data.settings.commercial_value_scale.map((p,i) => i===index ? {...p,ratio:e.target.value}:p))} /> → <input aria-label="score" type="number" min="0" max="100" value={point.score} onChange={(e) => editSettings("commercial_value_scale", data.settings.commercial_value_scale.map((p,i) => i===index ? {...p,score:Number(e.target.value)}:p))} /></span>)}</div></div><button className="primary-button">{t("common.save")}</button></form></section>
    </div>}</>;
}


export default BusinessSettingsPage;
