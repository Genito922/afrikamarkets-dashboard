import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function Register() {
  const { t } = useTranslation();
  const [form, setForm] = useState({ name: "", email: "", password: "" });

  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: call POST /api/auth/register
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <span className="text-4xl">🌍</span>
          <h1 className="text-2xl font-bold text-white mt-3">Afrika Markets Intelligence</h1>
          <p className="text-gray-400 mt-1">{t("free_trial_btn")} — 14 jours gratuits</p>
        </div>

        <form onSubmit={handleSubmit} className="card flex flex-col gap-5">
          <div>
            <label className="block text-sm text-gray-400 mb-1">{t("full_name")}</label>
            <input
              type="text" required value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-2.5
                         focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">{t("email_label")}</label>
            <input
              type="email" required value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-2.5
                         focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">{t("new_password")}</label>
            <input
              type="password" required minLength={8} value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-2.5
                         focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
            <p className="text-xs text-gray-500 mt-1">{t("min_8_chars")}</p>
          </div>

          <button type="submit" className="btn-primary w-full">
            {t("free_trial_btn")}
          </button>

          <p className="text-center text-xs text-gray-500">{t("legal_note")}</p>

          <p className="text-center text-sm text-gray-400">
            {t("already_account", "Déjà un compte ?")}{" "}
            <Link to="/login" className="text-brand-400 hover:underline">
              {t("login_btn", "Se connecter")}
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
