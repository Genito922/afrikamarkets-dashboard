/**
 * Overview — Profil Investisseur + Connaissances Trading
 * Wizard 5 étapes :
 *   1. Profil        → type d'investisseur
 *   2. Risque        → quiz 4 questions (horizon/tolérance/objectif/style)
 *   3. Connaissances → quiz MiFID 7 questions + avertissement de perte
 *   4. Résultat      → profil combiné + plan recommandé
 *   5. Accès         → CTA inscription / connexion
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";

// ── Données ───────────────────────────────────────────────────

const INVESTOR_TYPES = [
  { id: "diaspora", icon: "✈️",  label: "Diaspora",      desc: "Investisseur à l'étranger" },
  { id: "local",    icon: "🏠",  label: "Local UEMOA",   desc: "Résident Afrique de l'Ouest" },
  { id: "instit",   icon: "🏦",  label: "Institutionnel",desc: "Fonds, banque, assurance" },
  { id: "debutant", icon: "🌱",  label: "Débutant",      desc: "Premier investissement" },
];

const RISK_QUIZ = [
  {
    id: "risk",
    q: "Quelle est votre tolérance au risque ?",
    opts: [
      { label: "Faible — je préfère la sécurité", score: 1 },
      { label: "Modérée — équilibre rendement / risque", score: 2 },
      { label: "Élevée — je vise la performance maximale", score: 3 },
    ],
  },
  {
    id: "horizon",
    q: "Quel est votre horizon d'investissement ?",
    opts: [
      { label: "Court terme — moins d'1 an", score: 1 },
      { label: "Moyen terme — 1 à 5 ans", score: 2 },
      { label: "Long terme — plus de 5 ans", score: 3 },
    ],
  },
  {
    id: "goal",
    q: "Quel est votre objectif principal ?",
    opts: [
      { label: "Revenus réguliers (dividendes)", score: 1 },
      { label: "Croissance du capital", score: 2 },
      { label: "Les deux — stratégie mixte", score: 3 },
    ],
  },
  {
    id: "style",
    q: "Comment gérez-vous votre portefeuille ?",
    opts: [
      { label: "Passivement — je suis des recommandations", score: 1 },
      { label: "En combinant conseils et analyses perso", score: 2 },
      { label: "Activement — j'analyse moi-même", score: 3 },
    ],
  },
];

// 7 questions MiFID II / ESMA — connaissances trading
const KNOWLEDGE_QUIZ = [
  {
    id: "q1",
    q: "La BRVM (Bourse Régionale des Valeurs Mobilières) est :",
    opts: [
      { label: "Une banque centrale de l'UEMOA", correct: false },
      { label: "La bourse commune de 8 pays d'Afrique de l'Ouest", correct: true },
      { label: "Un organisme de crédit immobilier", correct: false },
      { label: "La monnaie officielle de la zone UEMOA", correct: false },
    ],
  },
  {
    id: "q2",
    q: "Vous investissez 500 000 FCFA. Le marché chute de 40 %. Quel est votre capital restant ?",
    opts: [
      { label: "460 000 FCFA", correct: false },
      { label: "350 000 FCFA", correct: false },
      { label: "300 000 FCFA", correct: true },
      { label: "Je ne peux pas perdre en bourse", correct: false },
    ],
  },
  {
    id: "q3",
    q: "L'analyse technique consiste à :",
    opts: [
      { label: "Analyser les bilans comptables et états financiers", correct: false },
      { label: "Étudier l'historique des prix et volumes pour anticiper les mouvements", correct: true },
      { label: "Consulter uniquement des analystes financiers", correct: false },
      { label: "Suivre l'actualité politique africaine", correct: false },
    ],
  },
  {
    id: "q4",
    q: "La diversification d'un portefeuille vise principalement à :",
    opts: [
      { label: "Maximiser les gains en concentrant les investissements", correct: false },
      { label: "Réduire le risque global en répartissant sur plusieurs actifs", correct: true },
      { label: "Réduire les frais de courtage", correct: false },
      { label: "Éviter de payer des impôts sur les plus-values", correct: false },
    ],
  },
  {
    id: "q5",
    q: "La liquidité d'une action désigne :",
    opts: [
      { label: "Le montant des dividendes versés chaque année", correct: false },
      { label: "La valeur totale de l'entreprise en bourse", correct: false },
      { label: "La facilité à acheter ou vendre rapidement sans impacter le cours", correct: true },
      { label: "Le capital social de l'entreprise cotée", correct: false },
    ],
  },
  {
    id: "q6",
    q: "En bourse, un ordre « Stop-Loss » est :",
    opts: [
      { label: "Un ordre d'achat automatique en cas de hausse", correct: false },
      { label: "Un ordre de vente automatique si le cours descend sous un seuil fixé", correct: true },
      { label: "Un frais de transaction supplémentaire", correct: false },
      { label: "Une limitation imposée par la BRVM aux investisseurs étrangers", correct: false },
    ],
  },
  {
    id: "q7",
    q: "Un dividende représente :",
    opts: [
      { label: "Une taxe prélevée sur les plus-values boursières", correct: false },
      { label: "Le cours d'ouverture d'une action chaque matin", correct: false },
      { label: "Un frais de gestion annuel facturé par le SGI", correct: false },
      { label: "Une partie des bénéfices de l'entreprise reversée aux actionnaires", correct: true },
    ],
  },
];

// Profils combinés (riskScore 4–12 + knowledgeScore 0–7 → total 4–19)
const PROFILES = [
  {
    range: [4, 8],
    emoji: "🌿", label: "Profil Novice Prudent",
    desc:  "Vous débutez en investissement. Commencez par les valeurs solides de la BRVM et construisez progressivement vos connaissances.",
    knowledge: "Novice", plan: "starter",
    alloc: { brvm: "80%", cash: "15%", intl: "5%" },
  },
  {
    range: [9, 12],
    emoji: "⚖️", label: "Profil Débutant Équilibré",
    desc:  "Vous avez les bases. L'analyse technique et les alertes vous aideront à optimiser vos points d'entrée sur la BRVM.",
    knowledge: "Débutant", plan: "starter",
    alloc: { brvm: "70%", cash: "15%", intl: "15%" },
  },
  {
    range: [13, 16],
    emoji: "📊", label: "Profil Intermédiaire",
    desc:  "Bonne maîtrise des marchés. Les outils d'analyse avancés, la war room géopolitique et la gestion de portefeuille sont vos atouts.",
    knowledge: "Intermédiaire", plan: "pro",
    alloc: { brvm: "60%", cash: "10%", intl: "30%" },
  },
  {
    range: [17, 19],
    emoji: "🚀", label: "Profil Averti Dynamique",
    desc:  "Vous maîtrisez les marchés financiers. Les marchés internationaux, l'analyse multi-actifs et les briefings 1-on-1 maximiseront votre performance.",
    knowledge: "Averti", plan: "expert",
    alloc: { brvm: "50%", cash: "5%", intl: "45%" },
  },
];

const PLAN_LABELS  = { starter: "Starter", pro: "Pro", expert: "Expert" };
const PLAN_PRICES  = { starter: "$29.99/mo", pro: "$74.99/mo", expert: "$199.99/mo" };
const PLAN_COLORS  = {
  starter: "border-blue-600",
  pro:     "border-brand-500",
  expert:  "border-yellow-600",
};
const PLAN_FEATS   = {
  starter: ["Dashboard BRVM complet", "Indices & secteurs", "Analyse technique MA/RSI", "Top 10 mouvements journaliers"],
  pro:     ["Tout Starter +", "War Room géopolitique", "Simulateur de portefeuille", "Alertes prix & risques", "SGI & OPCVM Intelligence"],
  expert:  ["Tout Pro +", "Marchés internationaux", "Briefing 1-on-1 mensuel", "Export CSV/PDF", "Support prioritaire"],
};

// ── Sous-composants ───────────────────────────────────────────

function StepsBar({ step }) {
  const STEPS = ["Profil", "Risque", "Connaissances", "Résultat", "Accès"];
  return (
    <div className="flex items-center justify-center mb-8 max-w-md mx-auto">
      {STEPS.map((label, i) => {
        const n = i + 1;
        const done = step > n, active = step === n;
        return (
          <div key={label} className="flex-1 text-center relative">
            {i < STEPS.length - 1 && (
              <div className={`absolute top-[17px] left-1/2 w-full h-0.5
                ${done ? "bg-brand-500" : "bg-gray-700"}`} />
            )}
            <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center
                             text-xs font-bold mx-auto mb-1 relative z-10 transition-all
                             ${done   ? "bg-brand-500 border-brand-500 text-white"
                                      : active
                                          ? "bg-brand-500/20 border-brand-500 text-brand-400"
                                          : "bg-gray-900 border-gray-700 text-gray-500"}`}>
              {done ? "✓" : n}
            </div>
            <p className={`text-[10px] tracking-wide hidden sm:block
                           ${active ? "text-brand-400" : "text-gray-600"}`}>
              {label}
            </p>
          </div>
        );
      })}
    </div>
  );
}

function QuizOption({ label, selected, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-3 px-4 py-3 rounded-xl border-2 text-left text-sm
                  transition-all w-full
                  ${selected
                    ? "border-brand-500 bg-brand-500/10 text-white"
                    : "border-gray-700 text-gray-400 hover:border-gray-500 hover:text-white"}`}
    >
      <span className={`w-4 h-4 rounded-full border-2 flex-shrink-0
                        ${selected ? "bg-brand-500 border-brand-500" : "border-gray-600"}`} />
      {label}
    </button>
  );
}

// ── Page principale ───────────────────────────────────────────

export default function Overview() {
  const navigate = useNavigate();

  const [step,         setStep]         = useState(1);
  const [profil,       setProfil]       = useState({ name: "", type: "" });
  const [riskAnswers,  setRiskAnswers]  = useState({});   // { qid: score }
  const [knowAnswers,  setKnowAnswers]  = useState({});   // { qid: boolean }
  const [profile,      setProfile]      = useState(null);

  // ── Calcul profil combiné ─────────────────────────────────
  function computeProfile(risk, know) {
    const riskScore  = Object.values(risk).reduce((a, b) => a + b, 0); // 4–12
    const knowScore  = Object.values(know).filter(Boolean).length;      // 0–7
    const total      = riskScore + knowScore;                            // 4–19
    return PROFILES.find((p) => total >= p.range[0] && total <= p.range[1])
        ?? PROFILES[1];
  }

  // ── Step 1 — Profil ───────────────────────────────────────
  function submitProfil(e) {
    e.preventDefault();
    if (!profil.type) return;
    setStep(2);
  }

  // ── Step 2 — Quiz risque ──────────────────────────────────
  function selectRisk(qid, score) {
    const next = { ...riskAnswers, [qid]: score };
    setRiskAnswers(next);
    if (Object.keys(next).length === RISK_QUIZ.length) {
      setTimeout(() => setStep(3), 400);
    }
  }

  // ── Step 3 — Connaissances ────────────────────────────────
  function selectKnow(qid, correct) {
    const next = { ...knowAnswers, [qid]: correct };
    setKnowAnswers(next);
    if (Object.keys(next).length === KNOWLEDGE_QUIZ.length) {
      const p = computeProfile(riskAnswers, next);
      setProfile(p);
      setTimeout(() => setStep(4), 400);
    }
  }

  const knowScore    = Object.values(knowAnswers).filter(Boolean).length;
  const knowProgress = (Object.keys(knowAnswers).length / KNOWLEDGE_QUIZ.length) * 100;
  const riskProgress = (Object.keys(riskAnswers).length / RISK_QUIZ.length) * 100;

  // ── Render ────────────────────────────────────────────────

  return (
    <div className="min-h-[90vh] px-4 py-10">
      <div className="max-w-xl mx-auto">
        <StepsBar step={step} />

        {/* ══ ÉTAPE 1 — PROFIL ══════════════════════════════ */}
        {step === 1 && (
          <form onSubmit={submitProfil} className="card flex flex-col gap-6">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">👤 Créez votre profil</h2>
              <p className="text-gray-400 text-sm">Personnalisez votre expérience Afrika Markets Intelligence.</p>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Prénom (optionnel)</label>
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

        {/* ══ ÉTAPE 2 — QUIZ RISQUE ═════════════════════════ */}
        {step === 2 && (
          <div className="card flex flex-col gap-5">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">📊 Profil de risque</h2>
              <p className="text-gray-400 text-sm mb-3">
                {Object.keys(riskAnswers).length}/{RISK_QUIZ.length} questions
              </p>
              <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full bg-brand-500 rounded-full transition-all duration-500"
                     style={{ width: `${riskProgress}%` }} />
              </div>
            </div>

            {RISK_QUIZ.map((q) => (
              <div key={q.id}>
                <h3 className="text-sm font-semibold text-white mb-3">{q.q}</h3>
                <div className="flex flex-col gap-2">
                  {q.opts.map((opt) => (
                    <QuizOption
                      key={opt.label}
                      label={opt.label}
                      selected={riskAnswers[q.id] === opt.score}
                      onClick={() => selectRisk(q.id, opt.score)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ══ ÉTAPE 3 — CONNAISSANCES TRADING (MiFID II) ════ */}
        {step === 3 && (
          <div className="flex flex-col gap-5">

            {/* ── Avertissement réglementaire MiFID II ─────── */}
            <div className="bg-yellow-900/20 border border-yellow-700/40 rounded-xl p-4 flex gap-3">
              <span className="text-yellow-400 text-xl flex-shrink-0">⚠️</span>
              <div>
                <p className="text-yellow-300 text-sm font-semibold mb-1">
                  Avertissement sur les risques de perte en capital
                </p>
                <p className="text-yellow-200/70 text-xs leading-relaxed">
                  Les investissements en bourse comportent un risque de perte en capital,
                  pouvant aller jusqu'à la <strong className="text-yellow-300">perte totale de votre investissement</strong>.
                  Les performances passées ne préjugent pas des performances futures.
                  La valeur de vos placements peut varier à la hausse comme à la baisse.
                  Assurez-vous de comprendre les risques avant d'investir.
                </p>
              </div>
            </div>

            {/* ── Quiz connaissances ───────────────────────── */}
            <div className="card flex flex-col gap-5">
              <div>
                <h2 className="text-2xl font-bold text-white mb-1">🎓 Connaissances en trading</h2>
                <p className="text-gray-400 text-sm mb-3">
                  {Object.keys(knowAnswers).length}/{KNOWLEDGE_QUIZ.length} questions
                  {Object.keys(knowAnswers).length === KNOWLEDGE_QUIZ.length && (
                    <span className="text-brand-400 ml-2">
                      · Score : {knowScore}/7 ({
                        knowScore <= 2 ? "Novice" :
                        knowScore <= 4 ? "Débutant" :
                        knowScore <= 6 ? "Intermédiaire" : "Averti"
                      })
                    </span>
                  )}
                </p>
                <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
                  <div className="h-full bg-brand-500 rounded-full transition-all duration-500"
                       style={{ width: `${knowProgress}%` }} />
                </div>
              </div>

              {KNOWLEDGE_QUIZ.map((q) => (
                <div key={q.id}>
                  <h3 className="text-sm font-semibold text-white mb-3">{q.q}</h3>
                  <div className="flex flex-col gap-2">
                    {q.opts.map((opt, i) => {
                      const answered = q.id in knowAnswers;
                      const chosen   = answered && knowAnswers[q.id] === opt.correct && opt.correct;
                      const wrong    = answered && knowAnswers[q.id] === opt.correct && !opt.correct;
                      return (
                        <button
                          key={i}
                          disabled={answered}
                          onClick={() => selectKnow(q.id, opt.correct)}
                          className={`flex items-center gap-3 px-4 py-3 rounded-xl border-2 text-left
                                      text-sm transition-all w-full
                                      ${!answered
                                        ? "border-gray-700 text-gray-400 hover:border-gray-500 hover:text-white"
                                        : opt.correct
                                            ? "border-green-500 bg-green-900/20 text-green-300"
                                            : "border-gray-700 text-gray-600 opacity-50"}`}
                        >
                          <span className={`w-4 h-4 rounded-full border-2 flex-shrink-0
                                            ${!answered ? "border-gray-600"
                                              : opt.correct ? "bg-green-500 border-green-500"
                                                           : "border-gray-600"}`} />
                          {opt.label}
                          {answered && opt.correct && (
                            <span className="ml-auto text-green-400 text-xs">✓ Bonne réponse</span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ══ ÉTAPE 4 — RÉSULTAT ════════════════════════════ */}
        {step === 4 && profile && (
          <div className="flex flex-col gap-5">

            <div className="card text-center">
              <span className="text-6xl block mb-3">{profile.emoji}</span>
              <h2 className="text-2xl font-bold text-white mb-1">{profile.label}</h2>
              <span className="inline-block text-xs text-brand-400 bg-brand-500/10 border
                               border-brand-500/20 px-3 py-1 rounded-full mb-3">
                Connaissances : {profile.knowledge}
              </span>
              <p className="text-gray-400 text-sm max-w-sm mx-auto">{profile.desc}</p>
            </div>

            <div className="card">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">
                Allocation recommandée
              </h3>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: "BRVM",  value: profile.alloc.brvm, color: "text-brand-400" },
                  { label: "Cash",  value: profile.alloc.cash, color: "text-yellow-400" },
                  { label: "Intl",  value: profile.alloc.intl, color: "text-purple-400" },
                ].map((a) => (
                  <div key={a.label} className="bg-gray-800 rounded-xl p-3 text-center">
                    <span className={`text-2xl font-bold block ${a.color}`}>{a.value}</span>
                    <span className="text-xs text-gray-500 uppercase">{a.label}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className={`card border-2 ${PLAN_COLORS[profile.plan]}`}>
              <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Plan recommandé</p>
              <div className="flex items-baseline gap-2 mb-1">
                <h3 className="text-xl font-bold text-white">{PLAN_LABELS[profile.plan]}</h3>
                <span className="text-brand-400 font-semibold text-sm">{PLAN_PRICES[profile.plan]}</span>
              </div>
              <ul className="mt-2 space-y-1">
                {PLAN_FEATS[profile.plan].map((f) => (
                  <li key={f} className="text-xs text-gray-400 flex gap-2">
                    <span className="text-brand-400">✓</span>{f}
                  </li>
                ))}
              </ul>
            </div>

            <button onClick={() => setStep(5)} className="btn-primary w-full">
              Obtenir mon accès →
            </button>
          </div>
        )}

        {/* ══ ÉTAPE 5 — ACCÈS ══════════════════════════════ */}
        {step === 5 && profile && (
          <div className="card flex flex-col gap-5">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">🚀 Commencez maintenant</h2>
              <p className="text-gray-400 text-sm">14 jours gratuits — aucune carte bancaire requise.</p>
            </div>

            <button
              onClick={() => navigate(
                `/register?plan=${profile.plan}${profil.name ? `&name=${encodeURIComponent(profil.name)}` : ""}`
              )}
              className="btn-primary w-full py-4 text-base"
            >
              Créer mon compte {PLAN_LABELS[profile.plan]} gratuitement
            </button>

            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-gray-700" />
              <span className="text-xs text-gray-500">ou</span>
              <div className="flex-1 h-px bg-gray-700" />
            </div>

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

            {/* Rappel réglementaire pied de page */}
            <p className="text-xs text-gray-600 text-center border-t border-gray-800 pt-4">
              ⚠️ Investir comporte un risque de perte en capital.
              Les performances passées ne préjugent pas des résultats futurs.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
