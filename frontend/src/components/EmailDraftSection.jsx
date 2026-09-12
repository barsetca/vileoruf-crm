import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Bot, Copy, FilePlus, Pencil, Send, Trash2 } from "lucide-react";

import { useAuth } from "../auth/AuthContext.jsx";
import { getNextBestAction } from "../services/nextBestAction.js";
import { createEmailDraft, deleteEmailDraft, generateEmailDraft, getEmailGeneration, listEmailDrafts, sendEmailDraft, updateEmailDraft } from "../services/emailDrafts.js";

const blank = { subject: "", body: "", purpose: "", language: "", source_ai_analysis_id: null };

function EmailDraftSection({ deal, client, canRun }) {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [generation, setGeneration] = useState(null);
  const [drafts, setDrafts] = useState([]);
  const [nba, setNba] = useState(null);
  const [purpose, setPurpose] = useState("");
  const [instructions, setInstructions] = useState("");
  const [selectedAction, setSelectedAction] = useState("");
  const [editing, setEditing] = useState(null);
  const [state, setState] = useState("loading");
  const [error, setError] = useState("");
  const [sendingId, setSendingId] = useState(null);

  const load = useCallback(async () => {
    if (!canRun) { setGeneration(null); setDrafts([]); setNba(null); setState("ready"); return; }
    setState("loading");
    try {
      const [nextGeneration, nextDrafts, nextNba] = await Promise.all([getEmailGeneration(accessToken, deal.id), listEmailDrafts(accessToken, deal.id), getNextBestAction(accessToken, deal.id)]);
      setGeneration(nextGeneration); setDrafts(nextDrafts); setNba(nextNba); setState("ready");
    } catch { setState("error"); }
  }, [accessToken, canRun, deal.id]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!generation?.active) return; const timer = window.setInterval(load, 2500); return () => window.clearInterval(timer); }, [generation?.active, load]);
  const current = generation?.current;
  const result = current?.result_payload;
  const nbaAnalysis = nba?.current ?? nba?.history?.find((item) => item.status === "SUCCESS") ?? null;
  const actions = nbaAnalysis?.result_payload?.actions ?? [];

  async function generate() {
    if (!purpose.trim()) { setError(t("emailDraft.purposeRequired")); return; }
    setState("generating"); setError("");
    try {
      const [analysisId, rank] = selectedAction.split(":");
      await generateEmailDraft(accessToken, deal.id, { purpose: purpose.trim(), additional_instructions: instructions.trim() || null, nba_analysis_id: analysisId || null, nba_action_rank: rank ? Number(rank) : null });
      await load();
    } catch (nextError) { setError(nextError.message); setState("ready"); }
  }
  function generatedForSave() {
    return { subject: result.subject, body: result.body, purpose, language: current.language, source_ai_analysis_id: current.id };
  }
  function openGenerated() { if (result) setEditing({ ...generatedForSave(), id: null }); }
  function openManual() { setEditing({ ...blank }); }
  function openExisting(draft) { setEditing({ ...draft }); }
  async function save() {
    if (!editing.subject.trim() || !editing.body.trim() || !editing.purpose.trim()) { setError(t("emailDraft.required")); return; }
    setError("");
    try {
      const payload = { subject: editing.subject.trim(), body: editing.body.trim(), purpose: editing.purpose.trim(), language: editing.language || null };
      if (editing.id) await updateEmailDraft(accessToken, deal.id, editing.id, payload);
      else await createEmailDraft(accessToken, deal.id, { ...payload, source_ai_analysis_id: editing.source_ai_analysis_id });
      setEditing(null); await load();
    } catch (nextError) { setError(nextError.message); }
  }
  async function remove(draft) {
    if (!window.confirm(t("emailDraft.confirmDelete"))) return;
    try { await deleteEmailDraft(accessToken, deal.id, draft.id); await load(); } catch (nextError) { setError(nextError.message); }
  }
  async function copy(value) { try { await navigator.clipboard.writeText(value); } catch { setError(t("emailDraft.copyError")); } }
  async function send(draft) {
    if (!client?.email) { setError(t("emailDraft.recipientMissing")); return; }
    if (!window.confirm(t("emailDraft.confirmSend", { recipient: client.email, subject: draft.subject }))) return;
    setSendingId(draft.id); setError("");
    try { await sendEmailDraft(accessToken, deal.id, draft.id); await load(); }
    catch (nextError) { setError(nextError.message || t("emailDraft.sendFailed")); }
    finally { setSendingId(null); }
  }

  return <section className="next-best-action email-draft-section">
    <div className="section-heading"><div><p className="eyebrow">AI</p><h3>{t("emailDraft.title")}</h3></div></div>
    <p className="readonly-note">{t("emailDraft.noAutoSend")}</p>
    {!canRun && <p className="readonly-note">{t("deals.readonly")}</p>}
    {canRun && <div className="email-draft-creation">
      <section className="email-draft-creation__ai">
        <div className="email-draft-creation__heading"><Bot aria-hidden="true" /><h4>{t("emailDraft.aiGeneration")}</h4></div>
        <div className="client-form-grid"><label className="field"><span>{t("emailDraft.purpose")} <em>*</em></span><input value={purpose} onChange={(event) => setPurpose(event.target.value)} maxLength="255" /></label><label className="field"><span>{t("emailDraft.instructions")}</span><input value={instructions} onChange={(event) => setInstructions(event.target.value)} maxLength="2000" /></label><label className="field field--full"><span>{t("emailDraft.nba")}</span><select value={selectedAction} onChange={(event) => setSelectedAction(event.target.value)}><option value="">{t("emailDraft.noNba")}</option>{actions.map((action) => <option key={action.rank} value={`${nbaAnalysis.id}:${action.rank}`}>{action.rank}. {action.action}{nbaAnalysis.is_outdated ? ` · ${t("emailDraft.nbaOutdated")}` : ""}</option>)}</select></label></div>
        <button className="primary-button deal-action-button" type="button" onClick={generate} disabled={state === "generating" || generation?.active}><Bot aria-hidden="true" />{t("emailDraft.generate")}</button>
      </section>
      <div className="email-draft-creation__manual"><button className="secondary-button deal-action-button" type="button" onClick={openManual}><FilePlus aria-hidden="true" />{t("emailDraft.newManual")}</button></div>
    </div>}
    {state === "loading" && <p>{t("emailDraft.loading")}</p>}
    {state === "error" && <div className="state-panel"><p className="form-error">{t("emailDraft.loadError")}</p><button className="secondary-button" type="button" onClick={load}>{t("common.retry")}</button></div>}
    {generation?.active && <p className="status-note">{t(`emailDraft.status.${generation.active.status}`)}</p>}
    {generation?.latest_attempt?.status === "FAILED" && <p className="form-error">{t("emailDraft.failed")}</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    {result && <article className="action-card email-proposal"><div><strong>{t("emailDraft.generated")}</strong><small>{current.language}</small></div>{current.is_outdated && <p className="warning-box">{t("emailDraft.contextChanged")}</p>}<label className="field"><span>{t("emailDraft.subject")}</span><input value={result.subject} readOnly /></label><label className="field"><span>{t("emailDraft.body")}</span><textarea value={result.body} readOnly rows="5" /></label><div className="email-draft-inline-actions"><button className="secondary-button deal-action-button" type="button" onClick={() => copy(`${result.subject}\n\n${result.body}`)}><Copy aria-hidden="true" />{t("emailDraft.copyAll")}</button>{canRun && <button className="primary-button" type="button" onClick={openGenerated}>{t("emailDraft.saveAs")}</button>}</div>{result.security_warning && <div className="warning-box warning-box--security"><strong>{t("emailDraft.security")}</strong><p>{result.security_warning}</p></div>}</article>}
    {state === "ready" && drafts.length === 0 && <p className="readonly-note">{t("emailDraft.empty")}</p>}
    <div className="action-list">{drafts.map((draft) => <article className="action-card" key={draft.id}><div><strong>{draft.subject}</strong><small>{draft.state === "SENT" ? t("emailDraft.sent") : draft.language}</small></div>{draft.outbound_status === "PENDING" && <p className="status-note">{t("emailDraft.sending")}</p>}{draft.outbound_status === "FAILED" && <p className="form-error">{t("emailDraft.sendFailed")}</p>}{draft.outbound_status === "UNKNOWN" && <p className="warning-box">{t("emailDraft.unknownOutcome")}</p>}<p>{draft.body}</p><small>{t("emailDraft.purpose")}: {draft.purpose}</small><div className="email-draft-actions"><button className="secondary-button deal-action-button" type="button" onClick={() => copy(`${draft.subject}\n\n${draft.body}`)}><Copy aria-hidden="true" />{t("emailDraft.copyAll")}</button>{canRun && draft.state !== "SENT" && !draft.outbound_status && <><button className="primary-button deal-action-button" type="button" disabled={sendingId === draft.id} onClick={() => send(draft)}><Send aria-hidden="true" />{sendingId === draft.id ? t("emailDraft.sending") : t("emailDraft.send")}</button><button className="secondary-button deal-action-button" type="button" onClick={() => openExisting(draft)}><Pencil aria-hidden="true" />{t("emailDraft.editAction")}</button><button className="secondary-button deal-action-button" type="button" onClick={() => remove(draft)}><Trash2 aria-hidden="true" />{t("emailDraft.delete")}</button></>}</div></article>)}</div>
    {editing && <div className="email-draft-editor"><h4>{editing.id ? t("emailDraft.editDraft") : t("emailDraft.newDraft")}</h4><label className="field"><span>{t("emailDraft.subject")}</span><input value={editing.subject} onChange={(event) => setEditing({ ...editing, subject: event.target.value })} /></label><label className="field"><span>{t("emailDraft.body")}</span><textarea rows="7" value={editing.body} onChange={(event) => setEditing({ ...editing, body: event.target.value })} /></label><label className="field"><span>{t("emailDraft.purpose")}</span><input value={editing.purpose} onChange={(event) => setEditing({ ...editing, purpose: event.target.value })} /></label><label className="field"><span>{t("emailDraft.language")}</span><select value={editing.language} onChange={(event) => setEditing({ ...editing, language: event.target.value })}><option value="">—</option><option value="RU">RU</option><option value="EN">EN</option><option value="ES">ES</option></select></label><div className="deal-actions"><button className="primary-button" type="button" onClick={save}>{t("common.save")}</button><button className="secondary-button" type="button" onClick={() => setEditing(null)}>{t("common.close")}</button></div></div>}
  </section>;
}

export default EmailDraftSection;
