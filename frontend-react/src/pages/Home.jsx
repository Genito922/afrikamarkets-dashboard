import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

const FEATURES = [
  { icon: "📈", key: "home_feat_market" },
  { icon: "🏦", key: "sgi_title" },
  { icon: "🤖", key: "sgi_module2" },
  { icon: "📊", key: "sgi_module3" },
  { icon: "🎯", key: "sgi_module4" },
  { icon: "🔔", key: "home_feat_alerts" },
];

const STATS = [
  { value: "120+",   label: "Titres BRVM" },
  { value: "8",      label: "SGI analysées" },
  { value: "7",      label: "OPCVM scorés" },
  { value: "6",      label: "Langues" },
];

export default function Home() {
  const { t } = useTranslation();

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden py-24 px-4">
        {/* Background glow */}
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px]
                          rounded-full bg-brand-500/5 blur-3xl" />
        </div>

        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-brand-500/10 border border-brand-500/20
                          text-brand-400 text-sm px-4 py-2 rounded-full mb-6">
            🌍 <span>Marchés africains — BRVM · UEMOA</span>
          </div>

          <h1 className="text-5xl sm:text-6xl font-extrabold text-white leading-tight mb-6">
            {t("home_hero_title", "Investissez sur la BRVM")}
            <span className="block text-brand-400">
              {t("home_hero_subtitle", "avec intelligence")}
            </span>
          </h1>

          <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10">
            {t("home_hero_desc",
              "Données en temps réel, analyse technique avancée, classement SGI & OPCVM, " +
              "et recommandations IA pour la diaspora africaine."
            )}
          </p>

          <div className="flex flex-wrap justify-center gap-4">
            <Link to="/register" className="btn-primary text-base px-8 py-3">
              {t("free_trial_btn")} →
            </Link>
            <Link to="/dashboard" className="btn-secondary text-base px-8 py-3">
              {t("home_see_demo", "Voir la démo")}
            </Link>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="border-y border-gray-800 py-10 px-4">
        <div className="max-w-5xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-8 text-center">
          {STATS.map((s) => (
            <div key={s.label}>
              <p className="text-3xl font-bold text-brand-400">{s.value}</p>
              <p className="text-sm text-gray-400 mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-white mb-4">
            {t("home_features_title", "Tout ce dont vous avez besoin")}
          </h2>
          <p className="text-gray-400 text-center mb-12 max-w-xl mx-auto">
            {t("home_features_desc",
              "Une plateforme complète pour analyser, comparer et investir sur les marchés africains."
            )}
          </p>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map(({ icon, key }) => (
              <div key={key} className="card hover:-translate-y-1 transition-transform duration-200">
                <div className="text-3xl mb-3">{icon}</div>
                <h3 className="font-semibold text-white">{t(key)}</h3>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Banner */}
      <section className="py-16 px-4">
        <div className="max-w-3xl mx-auto text-center card border-brand-500/30">
          <h2 className="text-3xl font-bold text-white mb-4">
            {t("home_cta_title", "Prêt à investir sur la BRVM ?")}
          </h2>
          <p className="text-gray-400 mb-8">
            {t("legal_note",
              "Essai gratuit 14 jours — Aucune carte bancaire requise · Annulation à tout moment"
            )}
          </p>
          <Link to="/register" className="btn-primary text-lg px-10 py-4">
            {t("free_trial_btn")}
          </Link>
        </div>
      </section>
    </div>
  );
}
