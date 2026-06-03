import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

// Reuse the exact same JSON files as the Streamlit backend
import fr from "@translations/fr.json";
import en from "@translations/en.json";
import es from "@translations/es.json";
import pt from "@translations/pt.json";
import zh from "@translations/zh.json";
import ar from "@translations/ar.json";

const resources = {
  fr: { translation: fr },
  en: { translation: en },
  es: { translation: es },
  pt: { translation: pt },
  zh: { translation: zh },
  ar: { translation: ar },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "fr",
    defaultNS: "translation",
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "ami_lang",
    },
  });

export default i18n;

export const LANGS = [
  { code: "fr", label: "🇫🇷 Français" },
  { code: "en", label: "🇬🇧 English" },
  { code: "es", label: "🇪🇸 Español" },
  { code: "pt", label: "🇧🇷 Português" },
  { code: "zh", label: "🇨🇳 中文" },
  { code: "ar", label: "🇸🇦 العربية", dir: "rtl" },
];
