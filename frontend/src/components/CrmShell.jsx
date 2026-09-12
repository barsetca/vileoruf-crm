import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import logoUrl from "../assets/vileoruf-logo.png";
import LanguageSwitcher from "./LanguageSwitcher.jsx";


function CrmShell({ children, pathname, onNavigate }) {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  useEffect(() => { setMobileNavOpen(false); }, [pathname]);
  async function handleLogout() {
    await logout();
    window.history.replaceState({}, "", "/");
    window.dispatchEvent(new PopStateEvent("popstate"));
  }

  return (
    <div className="crm-shell">
      <aside className="crm-sidebar" aria-label={t("crm.navigation.label")}>
        <button className="crm-brand" type="button" onClick={() => onNavigate("/crm")}>
          <img className="brand-logo" src={logoUrl} alt="" />
          <span>VILEORUF</span>
        </button>
        <button className="crm-menu-button secondary-button" type="button" aria-expanded={mobileNavOpen} aria-controls="crm-navigation" onClick={() => setMobileNavOpen((value) => !value)}>
          <span aria-hidden="true">{mobileNavOpen ? "×" : "☰"}</span>
          {t(`crm.navigation.${mobileNavOpen ? "closeMenu" : "openMenu"}`)}
        </button>
        <nav id="crm-navigation" className={`crm-nav ${mobileNavOpen ? "is-open" : ""}`}>
          <button className={`crm-nav-item ${pathname === "/crm" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm")}><span aria-hidden="true">⌂</span>{t("crm.navigation.dashboard")}</button>
          <button className={`crm-nav-item ${pathname === "/crm/clients" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm/clients")}>
            <span aria-hidden="true">◫</span>{t("crm.navigation.clients")}
          </button>
          <button className={`crm-nav-item ${pathname === "/crm/deals" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm/deals")}><span aria-hidden="true">◇</span>{t("crm.navigation.deals")}</button>
          <button className={`crm-nav-item ${pathname === "/crm/pipeline" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm/pipeline")}><span aria-hidden="true">▤</span>{t("crm.navigation.pipeline")}</button>
          <button className={`crm-nav-item ${pathname === "/crm/tasks" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm/tasks")}><span aria-hidden="true">✓</span>{t("crm.navigation.tasks")}</button>
          <button className={`crm-nav-item ${pathname === "/crm/ai-history" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm/ai-history")}><span aria-hidden="true">◎</span>{t("crm.navigation.aiHistory")}</button>
          <button className={`crm-nav-item ${pathname === "/crm/inbox" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm/inbox")}><span aria-hidden="true">✉</span>{t("crm.navigation.inbox")}</button>
          <button className={`crm-nav-item ${pathname === "/crm/analytics" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm/analytics")}><span aria-hidden="true">◔</span>{t("crm.navigation.analytics")}</button>
          {user.role === "ADMIN" && <button className={`crm-nav-item ${pathname === "/crm/settings/business" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm/settings/business")}><span aria-hidden="true">⚙</span>{t("d4.businessSettings")}</button>}
          {user.role === "ADMIN" && <button className={`crm-nav-item ${pathname === "/crm/settings/ai" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm/settings/ai")}><span aria-hidden="true">⚙</span>{t("aiSettings.title")}</button>}
          {user.role === "ADMIN" && <button className={`crm-nav-item ${pathname === "/crm/settings/integrations" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm/settings/integrations")}><span aria-hidden="true">⚙</span>{t("integrations.title")}</button>}
          {user.role === "ADMIN" && <button className={`crm-nav-item ${pathname === "/crm/employees" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm/employees")}><span aria-hidden="true">♙</span>{t("employees.title")}</button>}
        </nav>
        <div className="crm-sidebar-footer">
          <p>{t("crm.sidebar.workspace")}</p>
          <strong>{t("product.name")}</strong>
        </div>
      </aside>
      <div className="crm-main">
        <header className="crm-header">
          <div className="crm-header-mobile-brand">VILEORUF</div>
          <LanguageSwitcher compact />
          <div className="crm-user-menu">
            <span className="user-avatar" aria-hidden="true">{user.display_name.slice(0, 1).toUpperCase()}</span>
            <span className="crm-user-copy"><strong>{user.display_name}</strong><small>{t(`employees.roles.${user.role}`)}</small></span>
            <button className="text-button" type="button" onClick={handleLogout}>{t("auth.logout")}</button>
          </div>
        </header>
        <main className="crm-content">{children}</main>
      </div>
    </div>
  );
}


export default CrmShell;
