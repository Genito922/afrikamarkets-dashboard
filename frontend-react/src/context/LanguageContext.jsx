import { createContext, useContext, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { LANGS } from "../i18n";

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const { i18n } = useTranslation();
  const [lang, setLang] = useState(() => localStorage.getItem("ami_lang") || "fr");
  const currentLang = LANGS.find((l) => l.code === lang) || LANGS[0];

  useEffect(() => {
    i18n.changeLanguage(lang);
    localStorage.setItem("ami_lang", lang);
    // RTL support
    document.documentElement.dir = currentLang.dir || "ltr";
    document.documentElement.lang = lang;
  }, [lang, i18n, currentLang]);

  const changeLang = (code) => {
    if (LANGS.some((l) => l.code === code)) setLang(code);
  };

  return (
    <LanguageContext.Provider value={{ lang, changeLang, langs: LANGS, currentLang }}>
      {children}
    </LanguageContext.Provider>
  );
}

export const useLang = () => {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLang must be used within LanguageProvider");
  return ctx;
};
