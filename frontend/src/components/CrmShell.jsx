import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import logoUrl from "../assets/vileoruf-logo.png";
import LanguageSwitcher from "./LanguageSwitcher.jsx";


function CrmShell({ children, pathname, onNavigate }) {
  const { t } = useTranslation();
  const { user, logout } = useAuth();

  return (
    <div className="crm-shell">
      <aside className="crm-sidebar" aria-label={t("crm.navigation.label")}>
        <button className="crm-brand" type="button" onClick={() => onNavigate("/crm/clients")}>
          <img className="brand-logo" src={logoUrl} alt="" />
          <span>VILEORUF</span>
        </button>
        <nav className="crm-nav">
          <button className={`crm-nav-item ${pathname === "/crm/clients" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm/clients")}>
            <span aria-hidden="true">◫</span>{t("crm.navigation.clients")}
          </button>
          <button className={`crm-nav-item ${pathname === "/crm/deals" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm/deals")}><span aria-hidden="true">◇</span>{t("crm.navigation.deals")}</button>
          <button className={`crm-nav-item ${pathname === "/crm/pipeline" ? "is-active" : ""}`} type="button" onClick={() => onNavigate("/crm/pipeline")}><span aria-hidden="true">▤</span>{t("crm.navigation.pipeline")}</button>
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
            <button className="text-button" type="button" onClick={logout}>{t("auth.logout")}</button>
          </div>
        </header>
        <main className="crm-content">{children}</main>
      </div>
    </div>
  );
}


export default CrmShell;
