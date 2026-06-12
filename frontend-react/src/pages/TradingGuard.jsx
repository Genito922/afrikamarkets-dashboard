/**
 * TradingGuard — Verrou d'accès aux modules algorithmiques
 *
 * Étape 0 — Avertissement risque + 3 cases obligatoires
 * Étape 1 — Quiz Senior (THF & Architecture, 4 questions)
 * Étape 2 — Résultat (seuil de passage : 3/4)
 *
 * Accessible via /trading-guard (plan Expert requis).
 * Ne modifie pas Overview.jsx (parcours éducatif BRVM distinct).
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import ComplianceBanner from "../components/ComplianceBanner";

// ── Logo ──────────────────────────────────────────────────────
function Logo() {
  return (
    <div className="flex items-center gap-2">
      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-green-600 to-emerald-800
                      flex items-center justify-center font-black text-white shadow-lg text-base">
        Af
      </div>
      <div>
        <p className="text-base font-black text-white leading-none tracking-tight">
          Afrika<span className="text-brand-400">Markets</span>
        </p>
        <p className="text-xs text-gray-500 leading-none">Algo · Execution</p>
      </div>
    </div>
  );
}

// ── Données quiz ──────────────────────────────────────────────
const SENIOR_QUIZ = [
  {
    id: "q1",
    section: "High-Frequency Trading",
    q: "En Market Making HFT, comment gérez-vous l'Adverse Selection Risk lorsque le flux d'ordres (VPIN) augmente significativement ?",
    opts: [
      { label: "Élargir le spread Bid-Ask en réponse à la toxicité du flux d'ordres.", correct: true },
      { label: "Augmenter le levier pour absorber le flux directionnel entrant.", correct: false },
      { label: "Désactiver les sockets d'écoute pour éviter la congestion mémoire.", correct: false },
      { label: "Passer en ordre Market pour forcer l'exécution immédiate.", correct: false },
    ],
  },
  {
    id: "q2",
    section: "Infrastructure",
    q: "Votre boucle d'arbitrage cross-broker subit un slippage récurrent de 15 pips à l'exécution. Quel est le premier diagnostic infrastructurel ?",
    opts: [
      { label: "Changer de modèle de ML pour améliorer la prédiction de prix.", correct: false },
      { label: "Mesurer la latence réseau (RTT) et envisager une colocalisation VPS.", correct: true },
      { label: "Augmenter la taille des lots pour compenser le coût de slippage.", correct: false },
      { label: "Réécrire le script en C++ pour réduire le temps de calcul.", correct: false },
    ],
  },
  {
    id: "q3",
    section: "Concurrency Python",
    q: "Pour traiter 50 flux WebSocket temps réel sans bloquer la boucle d'événements asyncio, quelle approche appliquez-vous ?",
    opts: [
      { label: "Une boucle for synchrone sur chaque connexion WebSocket.", correct: false },
      { label: "asyncio.gather() ou TaskGroup pour 50 tâches asynchrones indépendantes.", correct: true },
      { label: "50 processus séparés via le module multiprocessing.", correct: false },
      { label: "time.sleep() entre chaque traitement de tick pour éviter la saturation.", correct: false },
    ],
  },
  {
    id: "q4",
    section: "Risk Management",
    q: "Quel design pattern appliquez-vous pour un coupe-circuit automatique stoppant le scalping si le Max Drawdown horaire est dépassé ?",
    opts: [
      { label: "Singleton centralisant le compteur de pertes — lève une exception fatale au seuil.", correct: true },
      { label: "Observer envoyant un e-mail en attente de validation manuelle de l'opérateur.", correct: false },
      { label: "Factory instanciant un broker de secours à la volée.", correct: false },
      { label: "Decorator journalisant l'erreur sans interrompre l'exécution des ordres.", correct: false },
    ],
  },
];

const PASS_THRESHOLD = 3; // 3/4 = 75%

// ── Barre de progression ──────────────────────────────────────
function StepBar({ step }) {
  const STEPS = ["Risques", "Quiz Senior", "Résultat"];
  return (
    <div className="flex items-center justify-center mb-8 max-w-xs mx-auto">
      {STEPS.map((label, i) => {
        const n = i + 1, done = step > n, active = step === n;
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

// ── Page principale ───────────────────────────────────────────
export default function TradingGuard() {
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [checks, setChecks] = useState({
    capital:  false,
    leverage: false,
    apikeys:  false,
  });
  const [answers, setAnswers]   = useState({});
  const [score,   setScore]     = useState(null);

  const allChecked = Object.values(checks).every(Boolean);
  const answered   = Object.keys(answers).length;

  function toggle(key) {
    setChecks((c) => ({ ...c, [key]: !c[key] }));
  }

  function selectAnswer(qid, correct) {
    if (qid in answers) return;
    const next = { ...answers, [qid]: correct };
    setAnswers(next);
    if (Object.keys(next).length === SENIOR_QUIZ.length) {
      const s = Object.values(next).filter(Boolean).length;
      setScore(s);
      setTimeout(() => setStep(3), 600);
    }
  }

  const passed = score !== null && score >= PASS_THRESHOLD;

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="max-w-2xl mx-auto px-4 pt-10 pb-20">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <Logo />
          <span className="text-xs text-gray-600 font-mono">Algo · Module d'accès</span>
        </div>

        <StepBar step={step} />

        {/* ── ÉTAPE 1 — AVERTISSEMENT & CASES ─────────────── */}
        {step === 1 && (
          <div className="space-y-5">
            <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6">
              <div className="flex items-start gap-3 mb-5">
                <span className="text-amber-400 text-xl flex-shrink-0 mt-0.5">⚠️</span>
                <div>
                  <h2 className="text-lg font-bold text-white mb-1">
                    Accès aux modules algorithmiques
                  </h2>
                  <p className="text-xs text-gray-400 leading-relaxed">
                    Le trading automatisé sur instruments à effet de levier (Futures Binance,
                    CFD Exness, indices synthétiques Deriv) comporte un risque de perte
                    supérieure au capital investi. L'automatisation amplifie la vitesse
                    d'exécution — et donc la vitesse de perte. Ces modules sont réservés aux
                    opérateurs ayant une expérience avérée en trading algorithmique.
                  </p>
                </div>
              </div>

              <div className="space-y-4 border-t border-gray-800 pt-5">
                {[
                  {
                    key: "capital",
                    text: "Je reconnais que le trading algorithmique peut entraîner des pertes supérieures au dépôt initial si les coupe-circuits API échouent.",
                  },
                  {
                    key: "leverage",
                    text: "Je comprends les mécanismes de l'effet de levier et de la latence réseau susceptibles de provoquer des slippages majeurs en conditions de forte volatilité.",
                  },
                  {
                    key: "apikeys",
                    text: "Je confirme avoir configuré mes clés API de production avec des restrictions d'IP strictes et le retrait de fonds désactivé.",
                  },
                ].map(({ key, text }) => (
                  <label key={key} className="flex items-start gap-3 cursor-pointer group">
                    <div
                      onClick={() => toggle(key)}
                      className={`mt-0.5 w-5 h-5 rounded border-2 flex-shrink-0 flex items-center
                                  justify-center cursor-pointer transition-all
                                  ${checks[key]
                                    ? "bg-brand-500 border-brand-500"
                                    : "border-gray-600 group-hover:border-gray-400"}`}
                    >
                      {checks[key] && (
                        <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                          <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2"
                                strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      )}
                    </div>
                    <span className="text-sm text-gray-300 leading-relaxed">{text}</span>
                  </label>
                ))}
              </div>
            </div>

            <button
              disabled={!allChecked}
              onClick={() => setStep(2)}
              className={`w-full py-3 rounded-xl font-semibold text-sm transition-all
                          ${allChecked
                            ? "bg-brand-500 hover:bg-brand-400 text-white"
                            : "bg-gray-800 text-gray-600 cursor-not-allowed"}`}
            >
              {allChecked
                ? "Accéder à l'évaluation technique →"
                : "Validez les 3 conditions pour continuer"}
            </button>

            <ComplianceBanner variant="compact" />
          </div>
        )}

        {/* ── ÉTAPE 2 — QUIZ SENIOR ─────────────────────────── */}
        {step === 2 && (
          <div className="space-y-5">
            <div className="bg-gray-900 rounded-2xl border border-gray-800 p-5">
              <div className="flex items-center justify-between mb-1">
                <h2 className="text-lg font-bold text-white">Évaluation Senior — THF & Architecture</h2>
                <span className="text-xs text-gray-500 font-mono">{answered}/{SENIOR_QUIZ.length}</span>
              </div>
              <div className="h-1 bg-gray-800 rounded-full overflow-hidden mb-1">
                <div
                  className="h-full bg-brand-500 rounded-full transition-all duration-500"
                  style={{ width: `${(answered / SENIOR_QUIZ.length) * 100}%` }}
                />
              </div>
              <p className="text-xs text-gray-600 mb-5">Seuil de passage : {PASS_THRESHOLD}/{SENIOR_QUIZ.length}</p>

              <div className="space-y-6">
                {SENIOR_QUIZ.map((q) => {
                  const done = q.id in answers;
                  return (
                    <div key={q.id}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] text-gray-600 uppercase tracking-widest font-mono">
                          {q.section}
                        </span>
                      </div>
                      <p className="text-sm font-semibold text-white mb-3 leading-snug">{q.q}</p>
                      <div className="space-y-2">
                        {q.opts.map((opt, i) => {
                          let cls = "border-gray-700 text-gray-400 hover:border-gray-500 hover:text-white";
                          if (done) {
                            if (opt.correct) cls = "border-brand-500 bg-brand-500/10 text-brand-300";
                            else             cls = "border-gray-800 text-gray-600 opacity-40";
                          }
                          return (
                            <button
                              key={i}
                              disabled={done}
                              onClick={() => selectAnswer(q.id, opt.correct)}
                              className={`flex items-start gap-3 px-4 py-3 rounded-xl border-2
                                          text-left text-sm w-full transition-all ${cls}`}
                            >
                              <span className={`w-4 h-4 rounded-full border-2 flex-shrink-0 mt-0.5
                                              ${done && opt.correct
                                                ? "bg-brand-500 border-brand-500"
                                                : "border-gray-600"}`} />
                              <span>{opt.label}</span>
                              {done && opt.correct && (
                                <span className="ml-auto text-brand-400 text-xs shrink-0">✓</span>
                              )}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── ÉTAPE 3 — RÉSULTAT ────────────────────────────── */}
        {step === 3 && score !== null && (
          <div className="space-y-5">
            <div className={`bg-gray-900 rounded-2xl border p-8 text-center
                            ${passed ? "border-brand-500/30" : "border-red-800/30"}`}>
              <span className="text-5xl block mb-4">{passed ? "✅" : "❌"}</span>
              <h2 className="text-2xl font-black text-white mb-2">
                {passed ? "Évaluation réussie" : "Score insuffisant"}
              </h2>
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border mb-4
                              font-mono text-sm
                              border-gray-700 bg-gray-800 text-gray-300">
                Score : {score} / {SENIOR_QUIZ.length}
                <span className={passed ? "text-brand-400" : "text-red-400"}>
                  ({Math.round((score / SENIOR_QUIZ.length) * 100)}%)
                </span>
              </div>
              <p className="text-gray-400 text-sm max-w-sm mx-auto">
                {passed
                  ? "Vous avez démontré la maîtrise nécessaire en trading algorithmique et gestion du risque."
                  : `Seuil requis : ${Math.round((PASS_THRESHOLD / SENIOR_QUIZ.length) * 100)}%. Révisez les sections Infrastructure et Risk Management avant de recommencer.`}
              </p>
            </div>

            {passed ? (
              <div className="space-y-3">
                <div className="grid grid-cols-1 gap-3">
                  {[
                    { label: "Crypto · Binance Futures",   sub: "CCXT Pro · WebSocket orderbook", soon: false },
                    { label: "Forex · Exness MT5",         sub: "MetaTrader5 SDK · asyncio.to_thread", soon: true },
                    { label: "Indices synthétiques · Deriv", sub: "WebSocket persistant · JSON API",  soon: true },
                  ].map((m) => (
                    <div
                      key={m.label}
                      className={`flex items-center justify-between px-4 py-3 rounded-xl border
                                  ${m.soon
                                    ? "border-gray-800 bg-gray-900/50 opacity-60"
                                    : "border-brand-500/30 bg-brand-500/5"}`}
                    >
                      <div>
                        <p className="text-sm font-semibold text-white">{m.label}</p>
                        <p className="text-xs text-gray-500 font-mono">{m.sub}</p>
                      </div>
                      {m.soon
                        ? <span className="text-xs text-gray-600 font-mono">prochainement</span>
                        : <span className="text-xs text-brand-400 font-mono">disponible</span>}
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => navigate("/crypto")}
                  className="w-full py-3 rounded-xl bg-brand-500 hover:bg-brand-400
                             text-white font-semibold text-sm transition-all"
                >
                  Accéder à l'analyse crypto →
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <button
                  onClick={() => { setStep(1); setAnswers({}); setScore(null); setChecks({ capital: false, leverage: false, apikeys: false }); }}
                  className="w-full py-3 rounded-xl border border-gray-700 text-gray-300
                             hover:border-gray-500 hover:text-white transition-all text-sm"
                >
                  Recommencer l'évaluation
                </button>
                <button
                  onClick={() => navigate("/dashboard")}
                  className="w-full py-3 rounded-xl bg-gray-800 text-gray-400
                             hover:text-white transition-all text-sm"
                >
                  Retour au tableau de bord
                </button>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
