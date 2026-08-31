import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import { getBackendHealth } from "../services/api.js";
import LanguageSwitcher from "./LanguageSwitcher.jsx";
import EmployeeManagement from "./EmployeeManagement.jsx";


function AuthenticatedApp() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const [backendStatus, setBackendStatus] = useState("checking");
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getBackendHealth(controller.signal)
      .then((data) => setBackendStatus(data.status === "ok" ? "available" : "unavailable"))
      .catch((error) => {
        if (error.name !== "AbortError") setBackendStatus("unavailable");
      });
    return () => controller.abort();
  }, []);

  async function handleLogout() {
    setIsLoggingOut(true);
    await logout();
  }

  return (
    <main className="foundation-shell">
      <section className="foundation-card" aria-labelledby="product-title">
        <div className="app-toolbar">
          <div className="brand-mark" aria-hidden="true">V</div>
          <div className="identity-card" aria-label={t("auth.currentUser")}>
            <strong>{user.display_name}</strong>
            <span>{user.email}</span>
            <span className="role-badge">{user.role}</span>
          </div>
        </div>

        <p className="eyebrow">{t("product.kind")}</p>
        <h1 id="product-title">{t("product.name")}</h1>
        <p className="subtitle">{t("product.subtitleAuthenticated")}</p>

        <div className="status-grid">
          <article className="status-item">
            <span>{t("status.frontend.label")}</span>
            <strong className="status status--available"><span className="status-dot" aria-hidden="true" />{t("status.frontend.ready")}</strong>
          </article>
          <article className="status-item">
            <span>{t("status.backend.label")}</span>
            <strong className={`status status--${backendStatus}`}><span className="status-dot" aria-hidden="true" />{t(`status.backend.${backendStatus}`)}</strong>
          </article>
        </div>

        <button className="secondary-button" type="button" onClick={handleLogout} disabled={isLoggingOut}>
          {t(isLoggingOut ? "auth.signingOut" : "auth.logout")}
        </button>
        <LanguageSwitcher />
        {user.role === "ADMIN" && <EmployeeManagement />}
      </section>
    </main>
  );
}


export default AuthenticatedApp;
