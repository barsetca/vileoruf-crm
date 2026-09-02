import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import logoUrl from "../assets/vileoruf-logo.png";
import LanguageSwitcher from "./LanguageSwitcher.jsx";


function LoginPage({ onHome }) {
  const { t } = useTranslation();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorKey, setErrorKey] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorKey(null);

    const result = await login(email, password);
    setPassword("");
    setIsSubmitting(false);
    if (!result.ok) {
      setErrorKey(`auth.errors.${result.reason}`);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="login-title">
        <div className="auth-heading">
          <img className="brand-logo brand-logo--login" src={logoUrl} alt="" />
          <div>
            <p className="eyebrow">{t("auth.internalAccess")}</p>
            <h1 id="login-title">{t("auth.title")}</h1>
          </div>
        </div>
        <p className="auth-intro">{t("auth.subtitle")}</p>

        <form className="login-form" onSubmit={handleSubmit}>
          <label htmlFor="login-email">{t("auth.email")}</label>
          <input
            id="login-email"
            name="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={isSubmitting}
            required
          />

          <label htmlFor="login-password">{t("auth.password")}</label>
          <input
            id="login-password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={isSubmitting}
            required
          />

          {errorKey && <p className="form-error" role="alert">{t(errorKey)}</p>}

          <button className="primary-button" type="submit" disabled={isSubmitting}>
            {t(isSubmitting ? "auth.signingIn" : "auth.signIn")}
          </button>
        </form>

        <button className="text-button auth-home-link" type="button" onClick={onHome}>
          {t("auth.backToHome")}
        </button>
        <LanguageSwitcher />
      </section>
    </main>
  );
}


export default LoginPage;
