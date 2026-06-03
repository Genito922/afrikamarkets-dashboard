import { useLang } from "../context/LanguageContext";

export default function LanguageSelector({ className = "" }) {
  const { lang, changeLang, langs } = useLang();

  return (
    <select
      value={lang}
      onChange={(e) => changeLang(e.target.value)}
      className={`bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-1.5
                  focus:outline-none focus:ring-1 focus:ring-brand-500 cursor-pointer ${className}`}
      aria-label="Language selector"
    >
      {langs.map((l) => (
        <option key={l.code} value={l.code}>
          {l.label}
        </option>
      ))}
    </select>
  );
}
