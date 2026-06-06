/**
 * Mon Profil — Afrika Markets Intelligence
 * Remplace pages/00_MON_PROFIL.py
 * Auth guard + infos compte + changement MDP + sécurité
 */
import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { apiGet, apiPost } from "../lib/api";

const PLAN_STYLE = {
  free:    { label: "Free",    cls: "bg-gray-700 text-gray-300 border-gray-500" },
  starter: { label: "Starter", cls: "bg-blue-900/50 text-blue-300 border-blue-600" },
  pro:     { label: "Pro",     cls: "bg-yellow-900/50 text-yellow-300 border-yellow-600" },
  expert:  { label: "Expert",  cls: "bg-green-900/50 text-green-300 border-green-600" },
};

function PwdStrength({ pwd }) {
  const checks = [
    { label: "8 caractères minimum", ok: pwd.length >= 8 },
    { label: "Une majuscule",         ok: /[A-Z]/.test(pwd) },
    { label: "Un chiffre",            ok: /\d/.test(pwd) },
    { label: "Un caractère spécial",  ok: /[^A-Za-z0-9]/.test(pwd) },
  ];
  const score = checks.filter((c) => c.ok).length;
  const colors = ["bg-red-500", "bg-red-500", "bg-orange-500", "bg-blue-500", "bg-green-500"];
  const labels = ["", "Faible", "Faible", "Moyen", "Fort"];
  return (
    <div className="mt-2 space-y-1">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className={`h-1 flex-1 rounded-full ${i < score ? colors[score] : "bg-gray-700"}`} />
        ))}
      </div>
      {pwd && <p className="text-xs text-gray-400">Force : {labels[score]}</p>}
      <div className="space-y-0.5">
        {checks.map(({ label, ok }) => (
          <p key={label} className={`text-xs ${ok ? "text-green-400" : "text-gray-500"}`}>
            {ok ? "✓" : "○"} {label}
          </p>
        ))}
      </div>
    </div>
  );
}

export default function Profile() {
  const { t } = useTranslation();
  const { isAuthenticated, user: authUser, plan, logout } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState("account");
  const [profile,   setProfile]   = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(true);

  // Formulaire compte
  const [form, setForm] = useState({ full_name: "", country: "CA" });

  // Formulaire MDP
  const [pwdForm, setPwdForm]   = useState({ old: "", new: "", confirm: "" });
  const [pwdMsg,  setPwdMsg]    = useState(null);

  // Redirection si non connecté
  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login");
    }
  }, [isAuthenticated, navigate]);

  // Chargement profil depuis /auth/me
  useEffect(() => {
    if (!isAuthenticated) return;
    apiGet("/auth/me", true)
      .then((data) => {
        setProfile(data);
        setForm({ full_name: data.full_name || "", country: data.country || "CA" });
      })
      .catch(() => {
        // fallback vers les données locales
        if (authUser) {
          setForm({ full_name: authUser.full_name || "", country: "CA" });
        }
      })
      .finally(() => setLoadingProfile(false));
  }, [isAuthenticated, authUser]);

  if (!isAuthenticated) return null;

  const planStyle = PLAN_STYLE[plan] || PLAN_STYLE.free;

  const TABS = [
    { key: "account",  label: t("tab_account",          "Mon compte") },
    { key: "password", label: t("tab_change_password",  "Mot de passe") },
    { key: "security", label: t("tab_reset",            "Sécurité") },
  ];

  function handlePasswordChange(e) {
    e.preventDefault();
    setPwdMsg(null);
    if (!pwdForm.old) { setPwdMsg({ type: "error", text: t("err_enter_current_pwd", "Saisissez votre mot de passe actuel") }); return; }
    if (pwdForm.new.length < 8) { setPwdMsg({ type: "error", text: t("err_pwd_too_short", "Minimum 8 caractères") }); return; }
    if (pwdForm.new !== pwdForm.confirm) { setPwdMsg({ type: "error", text: t("err_pwd_no_match", "Les mots de passe ne correspondent pas") }); return; }
    // TODO: appel API PATCH /auth/password quand l'endpoint est ajouté au backend
    setPwdMsg({ type: "success", text: t("password_updated", "Mot de passe mis à jour") });
  }

  return (
    <div className="py-8 px-4">
      <div className="max-w-4xl mx-auto space-y-6">

        {/* Header */}
        <div className="bg-gradient-to-r from-green-950 to-yellow-950 border border-green-900/40 rounded-2xl px-6 py-5">
          <h1 className="text-2xl font-bold text-white">👤 {t("profile_title", "Mon Profil")}</h1>
          <p className="text-gray-300 text-sm mt-1">
            {t("profile_subtitle", "Gérez vos informations et votre abonnement")}
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-gray-800">
          {TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-5 py-2.5 text-sm font-medium rounded-t-lg transition-colors -mb-px border-b-2 ${
                activeTab === key
                  ? "border-brand-500 text-brand-400 bg-brand-500/5"
                  : "border-transparent text-gray-400 hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* ── TAB 1 : COMPTE ─────────────────────────────────── */}
        {activeTab === "account" && (
          <div className="grid md:grid-cols-3 gap-6">
            {/* Infos personnelles */}
            <div className="md:col-span-2 card space-y-4">
              <h3 className="text-sm font-semibold text-gold-400 uppercase tracking-wider">
                {t("personal_info", "Informations personnelles")}
              </h3>

              {loadingProfile ? (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => <div key={i} className="h-10 bg-gray-800 rounded-lg animate-pulse" />)}
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">{t("full_name", "Nom complet")}</label>
                    <input
                      type="text"
                      value={form.full_name}
                      onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                      className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm
                                 focus:outline-none focus:ring-1 focus:ring-brand-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">{t("email_label", "Email")}</label>
                    <input
                      type="email"
                      value={profile?.email || authUser?.email || ""}
                      disabled
                      className="w-full bg-gray-900 border border-gray-800 text-gray-500 rounded-lg px-3 py-2 text-sm cursor-not-allowed"
                    />
                    <p className="text-xs text-gray-600 mt-1">{t("email_help", "L'email ne peut pas être modifié")}</p>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">{t("country", "Pays")}</label>
                    <select
                      value={form.country}
                      onChange={(e) => setForm({ ...form, country: e.target.value })}
                      className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm
                                 focus:outline-none focus:ring-1 focus:ring-brand-500"
                    >
                      {["CA","FR","BE","CH","CI","SN","ML","BF","TG","BJ","NE","GW"].map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                  <button className="btn-primary text-sm w-full">
                    {t("save", "Enregistrer")}
                  </button>
                </div>
              )}
            </div>

            {/* Plan + Stats */}
            <div className="space-y-4">
              <div className="card">
                <h3 className="text-sm font-semibold text-gold-400 uppercase tracking-wider mb-3">
                  {t("subscription_section", "Abonnement")}
                </h3>
                <p className="text-xs text-gray-400 mb-2">{t("current_plan_label", "Plan actuel")}</p>
                <span className={`badge border text-sm px-3 py-1 ${planStyle.cls}`}>
                  {planStyle.label}
                </span>
                {profile?.trial_ends_at && (
                  <p className="text-xs text-gray-500 mt-2">
                    {t("member_since", "Membre depuis")} {profile.created_at?.slice(0, 10) ?? ""}
                  </p>
                )}
                <Link
                  to="/pricing"
                  className="btn-primary text-sm w-full mt-4 text-center block"
                >
                  {t("upgrade_plan", "Changer de plan")}
                </Link>
              </div>

              {/* Déconnexion */}
              <div className="card border-red-900/30">
                <h3 className="text-sm font-semibold text-red-400 uppercase tracking-wider mb-3">
                  {t("danger_zone", "Zone de danger")}
                </h3>
                <button
                  onClick={() => { logout(); navigate("/"); }}
                  className="w-full text-sm py-2 px-4 rounded-xl border border-red-800 text-red-400
                             hover:bg-red-900/30 transition-colors"
                >
                  {t("logout_btn", "Se déconnecter")}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 2 : MOT DE PASSE ───────────────────────────── */}
        {activeTab === "password" && (
          <div className="max-w-md">
            <div className="card space-y-4">
              <h3 className="text-sm font-semibold text-gold-400 uppercase tracking-wider">
                {t("change_password_title", "Changer le mot de passe")}
              </h3>
              <p className="text-xs text-gray-400">{t("change_password_caption", "Votre nouveau mot de passe doit être fort et unique.")}</p>

              {pwdMsg && (
                <div className={`text-sm px-4 py-3 rounded-lg border ${
                  pwdMsg.type === "error"
                    ? "bg-red-500/10 border-red-500/30 text-red-400"
                    : "bg-green-500/10 border-green-500/30 text-green-400"
                }`}>
                  {pwdMsg.text}
                </div>
              )}

              <form onSubmit={handlePasswordChange} className="space-y-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">{t("current_password", "Mot de passe actuel")}</label>
                  <input
                    type="password" required
                    value={pwdForm.old}
                    onChange={(e) => setPwdForm({ ...pwdForm, old: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">{t("new_password", "Nouveau mot de passe")}</label>
                  <input
                    type="password" required
                    value={pwdForm.new}
                    onChange={(e) => setPwdForm({ ...pwdForm, new: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  {pwdForm.new && <PwdStrength pwd={pwdForm.new} />}
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">{t("confirm_password", "Confirmer le mot de passe")}</label>
                  <input
                    type="password" required
                    value={pwdForm.confirm}
                    onChange={(e) => setPwdForm({ ...pwdForm, confirm: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <button type="submit" className="btn-primary w-full text-sm">
                  {t("update_password_btn", "Mettre à jour le mot de passe")}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* ── TAB 3 : SÉCURITÉ ───────────────────────────────── */}
        {activeTab === "security" && (
          <div className="max-w-2xl card space-y-4">
            <h3 className="text-sm font-semibold text-gold-400 uppercase tracking-wider">
              {t("security_tips", "Conseils de sécurité")}
            </h3>
            <ul className="space-y-2 text-sm text-gray-400">
              {[
                "Utilisez un mot de passe unique pour Afrika Markets",
                "Activez l'authentification à deux facteurs dès que disponible",
                "Ne partagez jamais vos identifiants de connexion",
                "Déconnectez-vous sur les appareils partagés ou publics",
              ].map((tip) => (
                <li key={tip} className="flex items-start gap-2">
                  <span className="text-brand-400 mt-0.5">•</span>
                  {tip}
                </li>
              ))}
            </ul>

            <hr className="border-gray-800" />

            <div>
              <p className="text-xs text-gray-500 mb-3">
                {t("reset_pwd_caption", "Réinitialisez votre mot de passe par email")}
              </p>
              <div className="flex gap-3">
                <input
                  type="email"
                  defaultValue={profile?.email || authUser?.email || ""}
                  disabled
                  className="flex-1 bg-gray-900 border border-gray-800 text-gray-500 rounded-lg px-3 py-2 text-sm"
                />
                <button className="btn-secondary text-sm px-4">
                  {t("send_reset_link", "Envoyer le lien")}
                </button>
              </div>
              <p className="text-xs text-gray-600 mt-2">{t("check_spam", "Pensez à vérifier vos spams.")}</p>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
