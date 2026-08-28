import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import LanguageSwitcher from "./components/LanguageSwitcher.jsx";
import { getBackendHealth } from "./services/api.js";


function App() {
  const { t, i18n } = useTranslation();
  const [backendStatus, setBackendStatus] = useState("checking");

  useEffect(() => {
    document.documentElement.lang = i18n.resolvedLanguage ?? "ru";
    document.title = t("product.name");
  }, [i18n.resolvedLanguage, t]);

  useEffect(() => {
    const controller = new AbortController();

    getBackendHealth(controller.signal)
      .then((data) => {
        setBackendStatus(data.status === "ok" ? "available" : "unavailable");
      })
      .catch((error) => {
        if (error.name !== "AbortError") {
          setBackendStatus("unavailable");
        }
      });

    return () => controller.abort();
  }, []);

  return (
    <main className="foundation-shell">
      <section className="foundation-card" aria-labelledby="product-title">
        <div className="brand-mark" aria-hidden="true">V</div>
        <p className="eyebrow">{t("product.kind")}</p>
        <h1 id="product-title">{t("product.name")}</h1>
        <p className="subtitle">{t("product.subtitle")}</p>

        <div className="status-grid">
          <article className="status-item">
            <span>{t("status.frontend.label")}</span>
            <strong className="status status--available">
              <span className="status-dot" aria-hidden="true" />
              {t("status.frontend.ready")}
            </strong>
          </article>

          <article className="status-item">
            <span>{t("status.backend.label")}</span>
            <strong className={`status status--${backendStatus}`}>
              <span className="status-dot" aria-hidden="true" />
              {t(`status.backend.${backendStatus}`)}
            </strong>
          </article>
        </div>

        <LanguageSwitcher />
      </section>
    </main>
  );
}


export default App;
