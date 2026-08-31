import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import { createUser, listUsers, updateUser } from "../services/users.js";


function EmployeeManagement() {
  const { t } = useTranslation();
  const { accessToken, user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [state, setState] = useState("loading");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({ display_name: "", email: "", password: "", role: "MANAGER" });

  const load = () => { setState("loading"); listUsers(accessToken).then(data => { setUsers(data); setState("ready"); }).catch(() => setState("error")); };
  useEffect(load, [accessToken]);

  async function submit(event) {
    event.preventDefault(); setMessage("");
    try { await createUser(accessToken, form); setForm({ display_name: "", email: "", password: "", role: "MANAGER" }); setMessage(t("employees.created")); load(); }
    catch (error) { setMessage(t(error.status === 409 ? "employees.errors.duplicate" : "employees.errors.generic")); }
  }

  async function patch(employee, changes) {
    setMessage("");
    try { await updateUser(accessToken, employee.id, changes); setMessage(t("employees.updated")); load(); }
    catch (error) { setMessage(t(error.status === 409 ? "employees.errors.adminSafety" : "employees.errors.generic")); }
  }

  if (state === "loading") return <section className="employees-panel"><h2>{t("employees.title")}</h2><p>{t("employees.loading")}</p></section>;
  if (state === "error") return <section className="employees-panel"><h2>{t("employees.title")}</h2><p className="form-error">{t("employees.errors.generic")}</p></section>;

  return <section className="employees-panel" aria-labelledby="employees-title">
    <h2 id="employees-title">{t("employees.title")}</h2>
    <form className="employee-form" onSubmit={submit}>
      <input aria-label={t("employees.name")} placeholder={t("employees.name")} value={form.display_name} onChange={e=>setForm({...form,display_name:e.target.value})} required />
      <input aria-label={t("employees.email")} placeholder={t("employees.email")} type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})} required />
      <input aria-label={t("employees.password")} placeholder={t("employees.password")} type="password" autoComplete="new-password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} required />
      <select aria-label={t("employees.role")} value={form.role} onChange={e=>setForm({...form,role:e.target.value})}><option value="MANAGER">{t("employees.roles.MANAGER")}</option><option value="ADMIN">{t("employees.roles.ADMIN")}</option></select>
      <button className="primary-button" type="submit">{t("employees.create")}</button>
    </form>
    {message && <p className="action-message" role="status">{message}</p>}
    <div className="employee-list">
      {users.length === 0 && <p>{t("employees.empty")}</p>}
      {users.map(employee => <article className="employee-row" key={employee.id} data-user-email={employee.email}>
        <div><strong>{employee.display_name}</strong><span>{employee.email}</span></div>
        <select aria-label={t("employees.role")} value={employee.role} disabled={employee.id===currentUser.id} onChange={e=>patch(employee,{role:e.target.value})}><option value="MANAGER">{t("employees.roles.MANAGER")}</option><option value="ADMIN">{t("employees.roles.ADMIN")}</option></select>
        <span className={`employee-status employee-status--${employee.is_active?"active":"inactive"}`}>{t(employee.is_active?"employees.active":"employees.inactive")}</span>
        <button className="secondary-button" type="button" disabled={employee.id===currentUser.id} onClick={()=>patch(employee,{is_active:!employee.is_active})}>{t(employee.is_active?"employees.deactivate":"employees.activate")}</button>
        <button className="secondary-button" type="button" onClick={()=>{const name=window.prompt(t("employees.name"),employee.display_name);if(name!==null)patch(employee,{display_name:name});}}>{t("employees.edit")}</button>
      </article>)}
    </div>
  </section>;
}

export default EmployeeManagement;
