/**
 * Overview — Profil Investisseur
 * Wizard 4 étapes : Profil → Quiz → Résultat → Accès
 * Migré depuis afrikamarkets-site/overview.html
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";

// ── Data ──────────────────────────────────────────────────────

const INVESTOR_TYPES = [
  { id: "diaspora",  icon: "✈️",  label: "Diaspora",     desc: "Investisseur à l'étranger" },
  { id: "local",     icon: "🏠",  label: "Local UEMOA",  desc: "Résident Afrique de l'Ouest" },
  { id: "instit",    icon: "🏦",  label: "Institutionnel", desc: "Fonds, banque, assurance" },
  { id: "debutant",  icon: "🌱",  label: "Débutant",     desc: "Premier investissement" },
];

const QUIZ = [
  {
    id: "risk",
    question: "Quelle est votre tolérance au risque ?",
    options: [
      { id: "low",    label: "Faible — je préfère la sécurité",      score: 1 },
      { id: "medium", label: "Modérée — équilibre rendement/risque",   score: 2 },
      { id: "high",   label: "Élevée — je vise la performance max",    score: 3 },
    ],
  },
  {
    id: "horizon",
    question: "Quel est votre horizon d'investissement ?",
    options: [
      { id: "short",  label: "Court terme — moins d'1 an",            score: 1 },
      { id: "medium", label: "Moyen terme — 1 à 5 ans",               score: 2 },
      { id: "long",   label: "Long terme — plus de 5 ans",             score: 3 },
    ],
  },
  {
    id: "goal",
    question: "Quel est votre objectif principal ?",
    options: [
      { id: "income",  label: "Revenus réguliers (dividendes)",        score: 1 },
      { id: "growth",  label: "Croissance du capital",                 score: 2 },
      { id: "both",    label: "Les deux — stratégie mixte",            score: 3 },
    ],
  },
  {
    id: "research",
    question: "Comment abordez-vous la recherche ?",
    options: [
      { id: "guided",  label: "Guidé — recommandations IA",            score: 1 },
      { id: "mixed",   label: "Mixte — je combine analyse et IA",      score: 2 },
      { id: "own",     label: "Autonome — j'analyse moi-même",         score: 3 },
    ],
  },
];

const PROFILES = [
  {
    score:  [4, 6],
    emoji:  "🌿",
    label:  "Investisseur Prudent",
    desc:   "Vous privilégiez la stabilité et les revenus réguliers. La BRVM offre des valeurs solides et des dividendes attractifs.",
    plan:   "starter",
    alloc:  { brvm: "70%", cash: "20%", intl: "10%" },
  },
  {
    score:  [7, 9],
    emoji:  "⚖️",
    label:  "Investisseur Équilibré",
    desc:   "Vous cherchez un bon équilibre entre croissance et sécurité. L'analyse technique et les alertes vous aideront à optimiser vos entrées.",
    plan:   "pro",
    alloc:  { brvm: "60%", cash: "10%", intl: "30%" },
  },
  {
    score:  [10, 12],
    emoji:  "🚀",
    label:  "Investisseur Dynamique",
    desc:   "Vous cherchez la performance maximale. Les marchés internationaux et l'analyse approfondie sont vos alliés.",
    plan:   "expert",
    alloc:  { brvm: "50%", cash: "5%", intl: "45%" },
  },
];

const PLAN_LABELS = { starter: "Starter", pro: "Pro", expert: "Expert" };
const PLAN_PRICES = { starter: "$29.99/mo", pro: "$74.99/mo", expert: "$199.99/mo" };
const PLAN_DESC   = {
  starter: "Dashboard complet, indices, secteurs, war room basique.",
  pro:     "Tout Starter + analyse IA, simulateur, alertes, SGI & OPCVM.",
  expert:  "Tout Pro + marchés internationaux, briefing 1-on-1, export PDF.",
};

// ── Composants ────────────────────────────────────────────────

function StepsBar({ step }) {
  const STEPS = ["Profil", "Quiz", "Résultat", "Accès"];
  return (
    <div className="flex items-center justify-center gap-0 mb-8 max-w-sm mx-auto">
      {STEPS.map((label, i) => {
        const n    = i + 1;
        const done = step > n;
        const active = step === n;
        return (
          <div key={label} className="flex-1 text-center relative">
            {i < STEPS.length - 1 && (
              <div className={`absolute top-[18px] left-1/2 w-full h-0.5
                ${done ? "bg-brand-500" : "bg-gray-700"}`} />
            )}
            <div className={`w-9 h-9 rounded-full border-2 flex items-center justify-center
                             text-sm font-bold mx-auto mb-1 relative z-10
                             ${done   ? "bg-brand-500 border-brand-500 text-white"
                                      : active ? "bg-brand-500/20 border-brand-500 text-brand-400"
                                               : "bg-gray-900 border-gray-700 text-gray-500"}`}>
              {done ? "✓" : n}
            </div>
            <p className={`text-[10px] tracking-wide ${active ? "text-brand-400" : "text-gray-500"}`}>
              {label}
            </p>
          </div>
        );
      })}
    </div>
  );
}

// ── Page principale ───────────────────────────────────────────

export default function Overview() {
  const navigate = useNavigate();
  const [step, setStep]         = useState(1);
  const [profil, setProfil]     = useState({ name: "", type: "" });
  const [answers, setAnswers]   = useState({});
  const [profile, setProfile]   = useState(null);

  // ── Étape 1 : Profil ──────────────────────────────────────
  function submitProfil(e) {
    e.preventDefault();
    if (!profil.type) return;
    setStep(2);
  }

  // ── Étape 2 : Quiz ────────────────────────────────────────
  function selectAnswer(qid, score) {
    const next = { ...answers, [qid]: score };
    setAnswers(next);
    if (Object.keys(next).length === QUIZ.length) {
      const total = Object.values(next).reduce((a, b) => a + b, 0);
      const p = PROFILES.find((p) => total >= p.score[0] && total <= p.score[1])
             ?? PROFILES[1];
      setProfile(p);
      setStep(3);
    }
  }

  const quizDone    = Object.keys(answers).length;
  const quizProgress = (quizDone / QUIZ.length) * 100;

  // ── Render ────────────────────────────────────────────────

  return (
    <div className="min-h-[90vh] px-4 py-10">
      <div className="max-w-xl mx-auto">
        <StepsBar step={step} />

        {/* ── STEP 1 : PROFIL ─────────────────────────────── */}
        {step === 1 && (
          <form onSubmit={submitProfil} className="card flex flex-col gap-6">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">👤 Créez votre profil</h2>
              <p className="text-gray-400 text-sm">Quelques informations pour personnaliser votre expérience.</p>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Prénom</label>
              <input
                type="text"
                value={profil.name}
                onChange={(e) => setProfil({ ...profil, name: e.target.value })}
                placeholder="Marie"
                className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-2.5
                           focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-3">Quel type d'investisseur êtes-vous ?</label>
              <div className="grid grid-cols-2 gap-3">
                {INVESTOR_TYPES.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setProfil({ ...profil, type: t.id })}
                    className={`p-4 rounded-xl border-2 text-center transition-all
                      ${profil.type === t.id
                        ? "border-brand-500 bg-brand-500/10"
                        : "border-gray-700 bg-gray-800/50 hover:border-gray-600"}`}
                  >
                    <span className="text-2xl block mb-1">{t.icon}</span>
                    <span className="text-white text-sm font-semibold block">{t.label}</span>
                    <span className="text-gray-500 text-xs">{t.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={!profil.type}
              className="btn-primary w-full disabled:opacity-40"
            >
              Continuer →
            </button>
          </form>
        )}

        {/* ── STEP 2 : QUIZ ───────────────────────────────── */}
        {step === 2 && (
          <div className="card flex flex-col gap-6">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">📊 Votre profil risque</h2>
              <p className="text-gray-400 text-sm mb-4">
                {quizDone}/{QUIZ.length} questions répondues
              </p>
              <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-500 rounded-full transition-all duration-500"
                  style={{ width: `${quizProgress}%` }}
                />
              </div>
            </div>

            {QUIZ.map((q) => (
              <div key={q.id}>
                <h3 className="text-sm font-semibold text-white mb-3">{q.question}</h3>
                <div className="flex flex-col gap-2">
                  {q.options.map((opt) => {
                    const selected = answers[q.id] === opt.score;
                    return (
                      <button
                        key={opt.id}
                        onClick={() => selectAnswer(q.id, opt.score)}
                        className={`flex items-center gap-3 px-4 py-3 rounded-xl border-2 text-left
                          text-sm transition-all
                          ${selected
                            ? "border-brand-500 bg-brand-500/10 text-white"
                            : "border-gray-700 text-gray-400 hover:border-gray-500 hover:text-white"}`}
                      >
                        <span className={`w-4 h-4 rounded-full border-2 flex-shrink-0
                          ${selected ? "bg-brand-500 border-brand-500" : "border-gray-600"}`} />
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── STEP 3 : RÉSULTAT ───────────────────────────── */}
        {step === 3 && profile && (
          <div className="flex flex-col gap-5">
            <div className="card text-center">
              <span className="text-6xl block mb-3">{profile.emoji}</span>
              <h2 className="text-2xl font-bold text-white mb-2">{profile.label}</h2>
              <p className="text-gray-400 text-sm max-w-sm mx-auto">{profile.desc}</p>
            </div>

            <div className="card">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
                Allocation recommandée
              </h3>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: "BRVM",  value: profile.alloc.brvm,  color: "text-brand-400" },
                  { label: "Cash",  value: profile.alloc.cash,  color: "text-yellow-400" },
                  { label: "Intl",  value: profile.alloc.intl,  color: "text-purple-400" },
                ].map((a) => (
                  <div key={a.label} className="bg-gray-800 rounded-xl p-3 text-center">
                    <span className={`text-2xl font-bold block ${a.color}`}>{a.value}</span>
                    <span className="text-xs text-gray-500 uppercase">{a.label}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className={`card border-2 ${
              profile.plan === "pro" ? "border-brand-500" :
              profile.plan === "expert" ? "border-yellow-600" : "border-blue-600"
            }`}>
              <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Plan recommandé</p>
              <h3 className="text-xl font-bold text-white">{PLAN_LABELS[profile.plan]}</h3>
              <p className="text-brand-400 font-semibold">{PLAN_PRICES[profile.plan]}</p>
              <p className="text-sm text-gray-400 mt-1">{PLAN_DESC[profile.plan]}</p>
            </div>

            <button onClick={() => setStep(4)} className="btn-primary w-full">
              Choisir mon accès →
            </button>
          </div>
        )}

        {/* ── STEP 4 : ACCÈS ──────────────────────────────── */}
        {step === 4 && profile && (
          <div className="card flex flex-col gap-5">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">🚀 Commencez maintenant</h2>
              <p className="text-gray-400 text-sm">14 jours gratuits — aucune carte bancaire requise.</p>
            </div>

            <button
              onClick={() => navigate(`/register?plan=${profile.plan}${profil.name ? `&name=${encodeURIComponent(profil.name)}` : ""}`)}
              className="btn-primary w-full py-4 text-base"
            >
              Créer mon compte {PLAN_LABELS[profile.plan]} gratuitement
            </button>

            <button
              onClick={() => navigate("/pricing")}
              className="w-full py-3 rounded-xl border border-gray-700 text-gray-300
                         hover:border-gray-500 hover:text-white transition-all text-sm"
            >
              Voir tous les plans →
            </button>

            <p className="text-center text-xs text-gray-500">
              Déjà un compte ?{" "}
              <button
                onClick={() => navigate("/login")}
                className="text-brand-400 hover:underline"
              >
                Se connecter
              </button>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
