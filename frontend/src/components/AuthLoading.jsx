import { useTranslation } from "react-i18next";


function AuthLoading() {
  const { t } = useTranslation();

  return (
    <main className="auth-shell" aria-live="polite" aria-busy="true">
      <section className="auth-card auth-card--loading">
        <div className="brand-mark" aria-hidden="true">V</div>
        <span className="auth-spinner" aria-hidden="true" />
        <p className="auth-loading-text">{t("auth.loading")}</p>
      </section>
    </main>
  );
}


export default AuthLoading;
