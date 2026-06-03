import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function Login() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: call POST /api/auth/login
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <span className="text-4xl">🌍</span>
          <h1 className="text-2xl font-bold text-white mt-3">Afrika Markets Intelligence</h1>
          <p className="text-gray-400 mt-1">{t("login_btn", "Connexion")}</p>
        </div>

        <form onSubmit={handleSubmit} className="card flex flex-col gap-5">
          <div>
            <label className="block text-sm text-gray-400 mb-1">{t("email_label")}</label>
            <input
              type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-2.5
                         focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">{t("current_password", "Mot de passe")}</label>
            <input
              type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-2.5
                         focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>

          <button type="submit" className="btn-primary w-full">
            {t("login_btn", "Se connecter")}
          </button>

          <p className="text-center text-sm text-gray-400">
            {t("no_account", "Pas encore de compte ?")}{" "}
            <Link to="/register" className="text-brand-400 hover:underline">
              {t("register_btn", "S'inscrire")}
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
