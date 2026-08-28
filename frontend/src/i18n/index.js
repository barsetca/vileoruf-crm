import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";
import es from "./locales/es.json";
import ru from "./locales/ru.json";


export const LANGUAGE_STORAGE_KEY = "vileoruf.language";
export const supportedLanguages = ["ru", "en", "es"];

function readStoredLanguage() {
  try {
    const storedLanguage = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return supportedLanguages.includes(storedLanguage) ? storedLanguage : "ru";
  } catch {
    return "ru";
  }
}

i18n.use(initReactI18next).init({
  resources: {
    ru: { translation: ru },
    en: { translation: en },
    es: { translation: es },
  },
  lng: readStoredLanguage(),
  fallbackLng: "ru",
  supportedLngs: supportedLanguages,
  interpolation: {
    escapeValue: false,
  },
});

export async function setLanguage(language) {
  if (!supportedLanguages.includes(language)) {
    return;
  }

  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  } catch {
    // The language still changes when browser storage is unavailable.
  }

  await i18n.changeLanguage(language);
}

export default i18n;
