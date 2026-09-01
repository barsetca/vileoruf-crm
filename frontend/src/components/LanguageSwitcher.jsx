import { useTranslation } from "react-i18next";

import { setLanguage, supportedLanguages } from "../i18n/index.js";


function LanguageSwitcher({ compact = false }) {
  const { t, i18n } = useTranslation();

  return (
    <div className={`language-switcher ${compact ? "language-switcher--compact" : ""}`}>
      <span className="language-label">{t("language.label")}</span>
      <div className="language-options">
        {supportedLanguages.map((language) => (
          <button
            className="language-button"
            type="button"
            key={language}
            aria-pressed={i18n.resolvedLanguage === language}
            onClick={() => setLanguage(language)}
          >
            {t(`language.${language}`)}
          </button>
        ))}
      </div>
    </div>
  );
}


export default LanguageSwitcher;
