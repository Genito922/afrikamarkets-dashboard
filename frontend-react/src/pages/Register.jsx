import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

const API = import.meta.env.VITE_API_URL || "";

export default function Register() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [form, setForm]     = useState({ name: "", email: "", password: "", country: "CA" });
  const [error, setError]   = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.email,
          password: form.password,
          full_name: form.name,
          country: form.country,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Erreur d'inscription");
      } else {
        localStorage.setItem("ami_token", data.access_token);
        localStorage.setItem("ami_user", JSON.stringify({
          full_name: data.full_name,
          plan: data.plan,
          status: data.status,
        }));
        navigate("/dashboard");
      }
    } catch {
      setError("Serveur inaccessible — vérifiez votre connexion");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <span className="text-4xl">🌍</span>
          <h1 className="text-2xl font-bold text-white mt-3">Afrika Markets Intelligence</h1>
          <p className="text-gray-400 mt-1">{t("register_btn")} — 14 jours gratuits</p>
        </div>

        <form onSubmit={handleSubmit} className="card flex flex-col gap-5">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

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

          <div>
            <label className="block text-sm text-gray-400 mb-1">{t("country")}</label>
            <select
              value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })}
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-2.5
                         focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {["CA","FR","BE","CH","CI","SN","ML","BF","TG","BJ","NE","GW"].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full disabled:opacity-50">
            {loading ? "..." : t("register_btn")}
          </button>

          <p className="text-center text-xs text-gray-500">{t("legal_note")}</p>

          <p className="text-center text-sm text-gray-400">
            {t("already_account")}{" "}
            <Link to="/login" className="text-brand-400 hover:underline">{t("login_btn")}</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
