import { useTranslation } from "react-i18next";
import logoUrl from "../assets/vileoruf-logo.png";


function AuthLoading() {
  const { t } = useTranslation();

  return (
    <main className="auth-shell" aria-live="polite" aria-busy="true">
      <section className="auth-card auth-card--loading">
        <img className="brand-logo brand-logo--login" src={logoUrl} alt="" />
        <span className="auth-spinner" aria-hidden="true" />
        <p className="auth-loading-text">{t("auth.loading")}</p>
      </section>
    </main>
  );
}


export default AuthLoading;
