import { useState } from "react";
import { useTranslation } from "react-i18next";
import SGICard from "../components/SGICard";

// SGI data mirrors pages/08_SGI_OPCVM.py
const WEIGHTS = {
  frais: 0.25, facilite_ouverture: 0.15, app_mobile: 0.10,
  service_client: 0.15, recherche: 0.15, rapidite: 0.10, reputation: 0.10,
};

const SGI_DATA = [
  { nom: "NSIA Finance",           pays: "Côte d'Ivoire", founded: 2001, courtage: "0.80%", depot_min: 100_000, presence_diaspora: true,  ouverture_en_ligne: true,  app_mobile: true,  url: "https://www.nsiafinance.com",        scores: { frais: 8.0, facilite_ouverture: 9.0, app_mobile: 9.5, service_client: 8.5, recherche: 8.0, rapidite: 8.5, reputation: 9.0 }, strengths_fr: ["Ouverture 100 % en ligne", "App mobile bien notée", "Présence diaspora Canada/France"], strengths_en: ["100% online account opening", "Well-rated mobile app", "Diaspora-friendly (Canada/France)"], weaknesses_fr: ["Frais légèrement supérieurs aux boutiques", "Support en heures ouvrées uniquement"], weaknesses_en: ["Fees slightly above boutique brokers", "Support during business hours only"] },
  { nom: "Hudson & Cie",           pays: "Côte d'Ivoire", founded: 1998, courtage: "0.70%", depot_min: 500_000, presence_diaspora: false, ouverture_en_ligne: false, app_mobile: false, url: "https://www.hudsonetcie.com",         scores: { frais: 9.0, facilite_ouverture: 4.5, app_mobile: 3.0, service_client: 9.0, recherche: 9.5, rapidite: 7.5, reputation: 9.5 }, strengths_fr: ["Recherche de pointe", "Clientèle institutionnelle", "Réputation historique BRVM"], strengths_en: ["Cutting-edge research", "Institutional client base", "Historical BRVM reputation"], weaknesses_fr: ["Pas d'ouverture en ligne", "Dépôt minimum élevé", "Non adapté à la diaspora"], weaknesses_en: ["No online account opening", "High minimum deposit", "Not diaspora-friendly"] },
  { nom: "CGF Bourse",             pays: "Côte d'Ivoire", founded: 1994, courtage: "0.65%", depot_min: 50_000,  presence_diaspora: false, ouverture_en_ligne: true,  app_mobile: false, url: "https://www.cgfbourse.com",          scores: { frais: 9.5, facilite_ouverture: 7.0, app_mobile: 2.0, service_client: 7.5, recherche: 7.5, rapidite: 8.0, reputation: 8.5 }, strengths_fr: ["Frais parmi les plus bas BRVM", "Dépôt minimum accessible", "Ancienneté et fiabilité"], strengths_en: ["Among the lowest BRVM fees", "Accessible minimum deposit", "Track record and reliability"], weaknesses_fr: ["Pas d'application mobile", "Interface web datée", "Support lent"], weaknesses_en: ["No mobile app", "Outdated web interface", "Slow support"] },
  { nom: "BOA Capital Securities", pays: "Mali",           founded: 2010, courtage: "0.85%", depot_min: 100_000, presence_diaspora: true,  ouverture_en_ligne: true,  app_mobile: true,  url: "https://www.boacapitalsecurities.com", scores: { frais: 7.5, facilite_ouverture: 8.5, app_mobile: 8.0, service_client: 8.0, recherche: 7.0, rapidite: 8.5, reputation: 8.0 }, strengths_fr: ["Réseau bancaire BOA (13 pays)", "Idéal pour débutants", "Accès diaspora Afrique de l'Ouest"], strengths_en: ["BOA banking network (13 countries)", "Ideal for beginners", "West African diaspora access"], weaknesses_fr: ["Frais légèrement élevés", "Recherche limitée vs indépendants", "Couverture partielle BRVM"], weaknesses_en: ["Slightly high fees", "Limited research vs independents", "Partial BRVM coverage"] },
  { nom: "Coris Bourse",           pays: "Burkina Faso",   founded: 2008, courtage: "0.75%", depot_min: 75_000,  presence_diaspora: true,  ouverture_en_ligne: true,  app_mobile: false, url: "https://www.corisbourse.com",        scores: { frais: 8.5, facilite_ouverture: 7.5, app_mobile: 3.5, service_client: 7.5, recherche: 6.5, rapidite: 7.5, reputation: 7.5 }, strengths_fr: ["Solide réseau Coris Bank", "Bon rapport qualité/prix", "Accessible diaspora Burkina"], strengths_en: ["Strong Coris Bank network", "Good value for money", "Burkina Faso diaspora access"], weaknesses_fr: ["Pas d'app mobile", "Recherche macro limitée", "Couverture géographique restreinte"], weaknesses_en: ["No mobile app", "Limited macro research", "Restricted geographic coverage"] },
  { nom: "Africabourse",           pays: "Côte d'Ivoire", founded: 2015, courtage: "0.72%", depot_min: 50_000,  presence_diaspora: true,  ouverture_en_ligne: true,  app_mobile: true,  url: "https://www.africabourse.net",       scores: { frais: 8.8, facilite_ouverture: 9.0, app_mobile: 8.5, service_client: 7.0, recherche: 6.0, rapidite: 9.0, reputation: 7.0 }, strengths_fr: ["Plateforme digitale moderne", "Ouverture 100 % en ligne", "Exécution rapide des ordres"], strengths_en: ["Modern digital platform", "100% online opening", "Fast order execution"], weaknesses_fr: ["Structure plus récente", "Recherche en développement", "Service client perfectible"], weaknesses_en: ["Newer structure", "Research still developing", "Customer service needs improvement"] },
  { nom: "Sogebourse",             pays: "Côte d'Ivoire", founded: 2000, courtage: "0.90%", depot_min: 200_000, presence_diaspora: false, ouverture_en_ligne: false, app_mobile: false, url: "https://www.sogebourse.sn",          scores: { frais: 7.0, facilite_ouverture: 5.0, app_mobile: 2.0, service_client: 8.5, recherche: 8.5, rapidite: 7.0, reputation: 9.0 }, strengths_fr: ["Appui Société Générale", "Service client premium", "Sérieux institutionnel"], strengths_en: ["Société Générale backing", "Premium customer service", "Institutional credibility"], weaknesses_fr: ["Frais élevés", "Pas d'ouverture en ligne", "Pas adapté à la diaspora"], weaknesses_en: ["High fees", "No online opening", "Not diaspora-friendly"] },
  { nom: "Impaxis Securities",     pays: "Sénégal",        founded: 2007, courtage: "0.80%", depot_min: 150_000, presence_diaspora: true,  ouverture_en_ligne: true,  app_mobile: false, url: "https://www.impaxis.com",           scores: { frais: 8.0, facilite_ouverture: 7.0, app_mobile: 2.0, service_client: 8.0, recherche: 9.0, rapidite: 7.5, reputation: 8.5 }, strengths_fr: ["Recherche macroéconomique reconnue", "Présence forte au Sénégal", "Accès diaspora France/Belgique"], strengths_en: ["Recognized macroeconomic research", "Strong Senegalese presence", "France/Belgium diaspora access"], weaknesses_fr: ["Pas d'app mobile", "Dépôt minimum modéré", "Délais de traitement variables"], weaknesses_en: ["No mobile app", "Moderate minimum deposit", "Variable processing times"] },
];

function calcScore(sgi) {
  return Object.entries(WEIGHTS).reduce((s, [k, w]) => s + sgi.scores[k] * w, 0);
}

function scoreForProfile(sgi, profile) {
  let score = calcScore(sgi);
  if (profile.diaspora && sgi.presence_diaspora)       score += 0.5;
  if (profile.amount < 500_000 && sgi.depot_min <= 100_000) score += 0.3;
  if (profile.experience === "beginner" && sgi.ouverture_en_ligne) score += 0.3;
  if (profile.experience === "beginner" && sgi.app_mobile)         score += 0.2;
  if (profile.advice === "yes" && sgi.scores.service_client >= 8)  score += 0.4;
  if (profile.style === "active"   && sgi.scores.rapidite  >= 8.5) score += 0.3;
  if (profile.style === "longterm" && sgi.scores.recherche >= 8.5) score += 0.3;
  if (profile.experience === "expert" && sgi.scores.recherche >= 9) score += 0.3;
  return Math.min(parseFloat(score.toFixed(2)), 10);
}

export default function SGICenter() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;

  const [activeTab, setActiveTab] = useState("ranking");
  const [filterPays, setFilterPays] = useState("all");
  const [profile, setProfile] = useState(null);

  const [form, setForm] = useState({
    pays: "Canada", montant: 10000, experience: "beginner",
    style: "mixed", advice: "yes",
  });

  const pays_list = ["all", ...new Set(SGI_DATA.map((s) => s.pays))];

  const ranked = SGI_DATA.map((s) => ({
    ...s,
    score_global: parseFloat(calcScore(s).toFixed(2)),
  })).sort((a, b) => b.score_global - a.score_global);

  const filtered = filterPays === "all"
    ? ranked
    : ranked.filter((s) => s.pays === filterPays);

  const handleReco = (e) => {
    e.preventDefault();
    const diasporaPays = ["Canada", "France", "Belgique", "Suisse"];
    const p = {
      diaspora:   diasporaPays.includes(form.pays),
      amount:     form.montant * 655.957,
      experience: form.experience,
      style:      form.style,
      advice:     form.advice,
    };
    setProfile(p);
  };

  const top3 = profile
    ? [...SGI_DATA]
        .map((s) => ({ ...s, profile_score: scoreForProfile(s, profile) }))
        .sort((a, b) => b.profile_score - a.profile_score)
        .slice(0, 3)
    : [];

  const TABS = [
    { key: "ranking", label: t("sgi_module1") },
    { key: "reco",    label: t("sgi_module2") },
  ];

  return (
    <div className="py-12 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">{t("sgi_title")}</h1>
          <p className="text-gray-400 mt-2">{t("sgi_subtitle")}</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-8 border-b border-gray-800 pb-0">
          {TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-5 py-2.5 text-sm font-medium rounded-t-lg transition-colors -mb-px border-b-2
                ${activeTab === key
                  ? "border-brand-500 text-brand-400 bg-brand-500/5"
                  : "border-transparent text-gray-400 hover:text-white"}`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Tab: Ranking */}
        {activeTab === "ranking" && (
          <div>
            <div className="flex items-center gap-4 mb-6">
              <label className="text-sm text-gray-400">{t("sgi_country_filter")}</label>
              <select
                value={filterPays}
                onChange={(e) => setFilterPays(e.target.value)}
                className="bg-gray-800 border border-gray-700 text-sm text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                {pays_list.map((p) => (
                  <option key={p} value={p}>
                    {p === "all" ? t("sgi_all_countries") : p}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
              {filtered.map((sgi, i) => (
                <SGICard key={sgi.nom} sgi={sgi} rank={i + 1} />
              ))}
            </div>
          </div>
        )}

        {/* Tab: AI Recommendation */}
        {activeTab === "reco" && (
          <div className="max-w-3xl">
            <form onSubmit={handleReco} className="card mb-8">
              <h2 className="text-lg font-semibold text-white mb-6">{t("sgi_module2")}</h2>

              <div className="grid sm:grid-cols-2 gap-5">
                {/* Pays */}
                <div>
                  <label className="block text-sm text-gray-400 mb-1">{t("sgi_q_country")}</label>
                  <select
                    value={form.pays}
                    onChange={(e) => setForm({ ...form, pays: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  >
                    {["Canada", "France", "Belgique", "Suisse", "Côte d'Ivoire", "Sénégal", "Mali", "Burkina Faso", "Autre"].map((p) => (
                      <option key={p}>{p}</option>
                    ))}
                  </select>
                </div>

                {/* Montant */}
                <div>
                  <label className="block text-sm text-gray-400 mb-1">{t("sgi_q_amount")}</label>
                  <input
                    type="number" min={0} step={1000}
                    value={form.montant}
                    onChange={(e) => setForm({ ...form, montant: Number(e.target.value) })}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>

                {/* Expérience */}
                <div>
                  <label className="block text-sm text-gray-400 mb-1">{t("sgi_q_experience")}</label>
                  <select
                    value={form.experience}
                    onChange={(e) => setForm({ ...form, experience: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  >
                    <option value="beginner">{t("sgi_exp_beginner")}</option>
                    <option value="intermediate">{t("sgi_exp_intermediate")}</option>
                    <option value="expert">{t("sgi_exp_expert")}</option>
                  </select>
                </div>

                {/* Style */}
                <div>
                  <label className="block text-sm text-gray-400 mb-1">{t("sgi_q_style")}</label>
                  <select
                    value={form.style}
                    onChange={(e) => setForm({ ...form, style: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  >
                    <option value="active">{t("sgi_style_active")}</option>
                    <option value="longterm">{t("sgi_style_longterm")}</option>
                    <option value="mixed">{t("sgi_style_mixed")}</option>
                  </select>
                </div>

                {/* Conseils */}
                <div className="sm:col-span-2">
                  <label className="block text-sm text-gray-400 mb-2">{t("sgi_q_advice")}</label>
                  <div className="flex gap-4">
                    {[
                      { value: "yes", label: t("sgi_advice_yes") },
                      { value: "no",  label: t("sgi_advice_no") },
                    ].map(({ value, label }) => (
                      <label key={value} className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio" name="advice" value={value}
                          checked={form.advice === value}
                          onChange={() => setForm({ ...form, advice: value })}
                          className="accent-brand-500"
                        />
                        <span className="text-sm text-gray-300">{label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <button type="submit" className="btn-primary mt-6 w-full">
                {t("sgi_get_reco")}
              </button>
            </form>

            {/* Results */}
            {top3.length > 0 && (
              <div>
                <h3 className="text-xl font-semibold text-white mb-5">{t("sgi_top_reco")}</h3>
                <div className="flex flex-col gap-4">
                  {top3.map((sgi, i) => (
                    <SGICard key={sgi.nom} sgi={sgi} rank={i + 1} profileScore={sgi.profile_score} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
