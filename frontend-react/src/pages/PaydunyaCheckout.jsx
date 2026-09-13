/**
 * PaydunyaCheckout — paiement Mobile Money + retour PayDunya + polling
 * Route : /checkout?plan=X                     → sélection opérateur
 *         /checkout?payment=success&ref=X&plan=Y → polling post-redirection
 *         /checkout?payment=cancelled&plan=Y     → annulation
 */
import { useState, useEffect, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiGet } from "../lib/api";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ── Constantes ────────────────────────────────────────────────

const PLAN_ORDER = ["free", "starter", "pro", "expert", "expert_premium"];

const PLANS_INFO = {
  starter:        { label: "Starter",        price_xof: "18 000",  price_usd: "$29.99"  },
  pro:            { label: "Pro",             price_xof: "45 000",  price_usd: "$74.99"  },
  expert:         { label: "Expert",          price_xof: "115 000", price_usd: "$199.99" },
  expert_premium: { label: "Expert Premium",  price_xof: "170 000", price_usd: "$299.99" },
};

const COUNTRIES = [
  {
    code: "CI", name: "Côte d'Ivoire", flag: "🇨🇮",
    operators: [
      { id: "wave-ci",         label: "Wave CI",         flag: "🌊", type: "wave",      frais: "1%"   },
      { id: "orange-money-ci", label: "Orange Money CI", flag: "🟠", type: "orange_ci", frais: "2%"   },
      { id: "mtn-ci",          label: "MTN MoMo CI",     flag: "🟡", type: "phone",     frais: "2%"   },
      { id: "moov-ci",         label: "Moov Money CI",   flag: "🔵", type: "phone",     frais: "2%"   },
      { id: "djamo-ci",        label: "Djamo CI",        flag: "💜", type: "phone",     frais: "1.5%" },
    ],
  },
  {
    code: "SN", name: "Sénégal", flag: "🇸🇳",
    operators: [
      { id: "wave-senegal",         label: "Wave Sénégal",    flag: "🌊", type: "wave",  frais: "1%"   },
      { id: "orange-money-senegal", label: "Orange Money SN", flag: "🟠", type: "phone", frais: "2%"   },
      { id: "free-money-senegal",   label: "Free Money SN",   flag: "🟣", type: "phone", frais: "2%"   },
      { id: "expresso-sn",          label: "Expresso SN",     flag: "🔴", type: "phone", frais: "2%"   },
      { id: "wizall-senegal",       label: "Wizall SN",       flag: "🟢", type: "phone", frais: "2%"   },
      { id: "djamo-sn",             label: "Djamo SN",        flag: "💜", type: "phone", frais: "1.5%" },
    ],
  },
  {
    code: "BF", name: "Burkina Faso", flag: "🇧🇫",
    operators: [
      { id: "orange-money-burkina", label: "Orange Money BF", flag: "🟠", type: "phone", frais: "2%" },
      { id: "moov-burkina-faso",    label: "Moov BF",         flag: "🔵", type: "phone", frais: "2%" },
    ],
  },
  {
    code: "ML", name: "Mali", flag: "🇲🇱",
    operators: [
      { id: "orange-money-mali", label: "Orange Money ML", flag: "🟠", type: "phone", frais: "2%" },
      { id: "moov-ml",           label: "Moov Mali",       flag: "🔵", type: "phone", frais: "2%" },
    ],
  },
  {
    code: "TG", name: "Togo", flag: "🇹🇬",
    operators: [
      { id: "t-money-togo", label: "T-Money TG", flag: "🟤", type: "phone", frais: "2%" },
      { id: "moov-togo",    label: "Moov Togo",  flag: "🔵", type: "phone", frais: "2%" },
    ],
  },
  {
    code: "BJ", name: "Bénin", flag: "🇧🇯",
    operators: [
      { id: "mtn-benin",  label: "MTN MoMo BJ", flag: "🟡", type: "phone", frais: "2%" },
      { id: "moov-benin", label: "Moov Bénin",  flag: "🔵", type: "phone", frais: "2%" },
    ],
  },
  {
    code: "CM", name: "Cameroun", flag: "🇨🇲",
    operators: [
      { id: "mtn-cameroun", label: "MTN MoMo CM", flag: "🟡", type: "phone", frais: "2%" },
    ],
  },
  {
    code: "ALL", name: "Carte bancaire", flag: "🌍",
    operators: [
      { id: "card", label: "Carte bancaire", flag: "💳", type: "card", frais: "3%" },
    ],
  },
];

function findOperator(id) {
  for (const c of COUNTRIES) {
    const op = c.operators.find((o) => o.id === id);
    if (op) return op;
  }
  return null;
}

const POLL_INTERVAL  = 3000;   // 3s
const POLL_MAX       = 20;     // 60s max
const REDIRECT_DELAY = 2500;   // 2.5s avant redirection /subscription

// ── Hook polling ──────────────────────────────────────────────

function usePlanPolling({ active, targetPlan, onSuccess, onTimeout }) {
  const attempts = useRef(0);
  const timer    = useRef(null);

  useEffect(() => {
    if (!active) return;
    attempts.current = 0;

    async function tick() {
      attempts.current += 1;
      try {
        const me = await apiGet("/subscriptions/me", true);
        const meIdx     = PLAN_ORDER.indexOf(me?.plan);
        const targetIdx = PLAN_ORDER.indexOf(targetPlan);
        if (meIdx >= targetIdx && meIdx > 0) {
          onSuccess(me.plan);
          return;
        }
      } catch {
        // Erreur réseau transitoire — on continue
      }
      if (attempts.current >= POLL_MAX) {
        onTimeout();
        return;
      }
      timer.current = setTimeout(tick, POLL_INTERVAL);
    }

    tick();
    return () => clearTimeout(timer.current);
  }, [active, targetPlan]);   // eslint-disable-line

  return attempts;
}

// ── Écran polling ─────────────────────────────────────────────

function PollingScreen({ targetPlan, attempts, onRetry, onGiveUp }) {
  const pct = Math.min((attempts.current / POLL_MAX) * 100, 100);
  return (
    <div className="text-center space-y-6">
      <div className="text-4xl animate-pulse">⏳</div>
      <div>
        <h2 className="text-lg font-bold text-white">Vérification du paiement…</h2>
        <p className="text-gray-400 text-sm mt-1">
          Confirmation du plan <strong className="text-white">{PLANS_INFO[targetPlan]?.label || targetPlan}</strong> en cours.
        </p>
      </div>
      <div className="w-full bg-gray-800 rounded-full h-2">
        <div
          className="bg-green-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-gray-600">
        Tentative {attempts.current}/{POLL_MAX} · Validation automatique en cours
      </p>
      <button
        onClick={onGiveUp}
        className="text-xs text-gray-600 hover:text-gray-400 underline"
      >
        Vérifier plus tard →
      </button>
    </div>
  );
}

// ── Écran succès ──────────────────────────────────────────────

function SuccessScreen({ plan }) {
  return (
    <div className="text-center space-y-4">
      <div className="text-5xl">✅</div>
      <h2 className="text-xl font-bold text-white">Paiement confirmé</h2>
      <p className="text-gray-300">
        Plan <strong className="text-green-400">{PLANS_INFO[plan]?.label || plan}</strong> activé.
      </p>
      <p className="text-sm text-gray-500">Redirection vers votre abonnement…</p>
    </div>
  );
}

// ── Écran timeout ─────────────────────────────────────────────

function TimeoutScreen({ targetPlan, onRetry, navigate }) {
  return (
    <div className="text-center space-y-5">
      <div className="text-4xl">⏱</div>
      <h2 className="text-lg font-bold text-white">Validation en cours de traitement</h2>
      <p className="text-gray-400 text-sm">
        Votre paiement est probablement validé côté PayDunya — la confirmation peut prendre
        quelques minutes supplémentaires.
      </p>
      <div className="flex flex-col gap-3">
        <button
          onClick={onRetry}
          className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition"
        >
          Revérifier maintenant
        </button>
        <button
          onClick={() => navigate("/subscription")}
          className="w-full py-3 rounded-xl border border-gray-700 text-gray-400 hover:text-white text-sm transition"
        >
          Voir mon abonnement →
        </button>
      </div>
      <p className="text-xs text-gray-600">
        Si le problème persiste, contactez support@afrikamarkets.com avec la référence de votre transaction.
      </p>
    </div>
  );
}

// ── Composant principal ───────────────────────────────────────

export default function PaydunyaCheckout() {
  const [searchParams] = useSearchParams();
  const navigate        = useNavigate();
  const { user, isAuthenticated } = useAuth();

  const planKey     = searchParams.get("plan")    || "starter";
  const paymentState = searchParams.get("payment"); // "success" | "cancelled" | null
  const planInfo    = PLANS_INFO[planKey] || PLANS_INFO.starter;

  // ── États ──────────────────────────────────────────────────
  // "form"     → sélection opérateur
  // "polling"  → attente confirmation
  // "ussd"     → USSD/token affiché, polling optionnel
  // "success"  → plan activé
  // "timeout"  → 60s écoulées sans confirmation
  // "cancelled"→ utilisateur a annulé sur PayDunya
  const [screen,    setScreen]    = useState(() => {
    if (paymentState === "success")   return "polling";
    if (paymentState === "cancelled") return "cancelled";
    return "form";
  });

  const [selectedOp, setSelectedOp] = useState(null);
  const [phone,      setPhone]      = useState("");
  const [loading,    setLoading]    = useState(false);
  const [payResult,  setPayResult]  = useState(null);
  const [error,      setError]      = useState("");
  const [confirmedPlan, setConfirmedPlan] = useState(null);

  // Polling actif quand screen === "polling" ou "ussd" (si user clique "vérifier")
  const [pollActive, setPollActive] = useState(screen === "polling");

  const attempts = usePlanPolling({
    active:     pollActive,
    targetPlan: planKey,
    onSuccess:  (plan) => {
      setPollActive(false);
      setConfirmedPlan(plan);
      setScreen("success");
    },
    onTimeout: () => {
      setPollActive(false);
      setScreen("timeout");
    },
  });

  // Redirection auto après succès
  useEffect(() => {
    if (screen !== "success") return;
    const t = setTimeout(() => navigate("/subscription"), REDIRECT_DELAY);
    return () => clearTimeout(t);
  }, [screen, navigate]);

  // Redirect si non authentifié
  useEffect(() => {
    if (!isAuthenticated) navigate("/login?redirect=/checkout?plan=" + planKey);
  }, [isAuthenticated]);

  // ── Soumission du formulaire ────────────────────────────────
  const op       = selectedOp ? findOperator(selectedOp) : null;
  const needsPhone = op && op.type !== "wave" && op.type !== "card";

  async function handleSubmit(e) {
    e.preventDefault();
    if (!selectedOp) { setError("Choisissez un opérateur de paiement."); return; }
    if (needsPhone && !phone.trim()) { setError("Entrez votre numéro de téléphone."); return; }
    setError("");
    setLoading(true);

    try {
      const resp = await fetch(`${API}/api/v1/paydunya/pay`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id:        user.id,
          plan:           planKey,
          operator:       selectedOp,
          phone:          phone.trim() || null,
          customer_name:  user.full_name || user.email || "Client Afrika Markets",
          customer_email: user.email || null,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Erreur PayDunya");

      setPayResult(data);

      if (data.redirect_url) {
        // Wave / Card → redirection vers PayDunya
        // La return_url pointe sur /checkout?payment=success&ref=...&plan=...
        window.location.href = data.redirect_url;
      } else {
        // USSD / token → on reste sur la page et on montre le code
        setScreen("ussd");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Wrappers de rendu ─────────────────────────────────────

  function Shell({ children }) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
        <div className="bg-gray-900 border border-gray-700 rounded-2xl p-8 max-w-lg w-full">
          {children}
        </div>
      </div>
    );
  }

  // ── Écrans ────────────────────────────────────────────────

  if (screen === "polling") {
    return (
      <Shell>
        <PollingScreen
          targetPlan={planKey}
          attempts={attempts}
          onGiveUp={() => navigate("/subscription")}
        />
      </Shell>
    );
  }

  if (screen === "success") {
    return (
      <Shell>
        <SuccessScreen plan={confirmedPlan || planKey} />
      </Shell>
    );
  }

  if (screen === "timeout") {
    return (
      <Shell>
        <TimeoutScreen
          targetPlan={planKey}
          onRetry={() => { attempts.current = 0; setPollActive(true); setScreen("polling"); }}
          navigate={navigate}
        />
      </Shell>
    );
  }

  if (screen === "cancelled") {
    return (
      <Shell>
        <div className="text-center space-y-4">
          <div className="text-4xl">❌</div>
          <h2 className="text-lg font-bold text-white">Paiement annulé</h2>
          <p className="text-gray-400 text-sm">Aucun montant n'a été prélevé.</p>
          <div className="flex flex-col gap-3 mt-2">
            <button
              onClick={() => setScreen("form")}
              className="w-full py-3 rounded-xl bg-green-600 hover:bg-green-500 text-white text-sm font-semibold transition"
            >
              Réessayer
            </button>
            <button
              onClick={() => navigate("/pricing")}
              className="w-full py-3 rounded-xl border border-gray-700 text-gray-400 hover:text-white text-sm transition"
            >
              Voir les plans
            </button>
          </div>
        </div>
      </Shell>
    );
  }

  if (screen === "ussd") {
    return (
      <Shell>
        <div className="text-center space-y-5">
          <div className="text-4xl">📲</div>
          <h2 className="text-xl font-bold text-white">Paiement initié</h2>
          <p className="text-gray-400 text-sm">
            Validez la transaction sur votre téléphone —{" "}
            <strong className="text-white">{op?.label}</strong>.
          </p>

          {payResult?.ussd_code && (
            <div className="bg-gray-800 rounded-xl p-4">
              <p className="text-xs text-gray-500 mb-1">Code USSD</p>
              <p className="text-2xl font-mono font-bold text-green-400">{payResult.ussd_code}</p>
            </div>
          )}

          {payResult?.ref && (
            <div className="bg-gray-800 rounded-xl p-3">
              <p className="text-xs text-gray-500 mb-1">Référence</p>
              <p className="font-mono text-sm text-gray-300 break-all">{payResult.ref}</p>
            </div>
          )}

          <p className="text-xs text-gray-500">
            Votre licence sera activée automatiquement après confirmation.
          </p>

          {/* Polling à la demande après validation téléphone */}
          {!pollActive ? (
            <button
              onClick={() => { setPollActive(true); setScreen("polling"); }}
              className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition"
            >
              J'ai validé sur mon téléphone — Vérifier
            </button>
          ) : null}

          <button
            onClick={() => navigate("/dashboard")}
            className="w-full py-3 rounded-xl border border-gray-700 text-gray-400 hover:text-white text-sm transition"
          >
            Accéder à l'application →
          </button>
        </div>
      </Shell>
    );
  }

  // ── Formulaire de sélection opérateur (écran par défaut) ──
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl p-8 max-w-lg w-full">

        <div className="mb-6">
          <button
            onClick={() => navigate("/pricing")}
            className="text-gray-500 hover:text-gray-300 text-sm mb-4 flex items-center gap-1"
          >
            ← Retour aux plans
          </button>
          <h1 className="text-2xl font-bold text-white">Souscrire — {planInfo.label}</h1>
          <p className="text-green-400 text-lg font-semibold mt-1">
            {planInfo.price_xof} FCFA
            <span className="text-gray-500 text-sm font-normal ml-2">/ mois ({planInfo.price_usd})</span>
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-3">
              Choisissez votre moyen de paiement
            </label>
            {COUNTRIES.map((country) => (
              <div key={country.code} className="mb-4">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
                  {country.flag} {country.name}
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {country.operators.map((o) => (
                    <button
                      key={o.id}
                      type="button"
                      onClick={() => { setSelectedOp(o.id); setError(""); }}
                      className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-sm transition-all
                        ${selectedOp === o.id
                          ? "border-green-500 bg-green-500/10 text-white"
                          : "border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-500"}`}
                    >
                      <span>{o.flag}</span>
                      <span className="flex-1 text-left leading-tight">{o.label}</span>
                      <span className="text-xs text-gray-500">{o.frais}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {needsPhone && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Numéro de téléphone
              </label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+225 07 00 00 00 00"
                className="w-full bg-gray-800 border border-gray-600 rounded-xl px-4 py-3 text-white
                           placeholder-gray-500 focus:outline-none focus:border-green-500 text-sm"
              />
              <p className="text-xs text-gray-500 mt-1">Format international (ex : +225 pour CI)</p>
            </div>
          )}

          {op?.type === "wave" && (
            <p className="text-sm text-gray-400 bg-gray-800 rounded-xl px-4 py-3">
              🌊 Vous serez redirigé vers Wave pour valider le paiement.
            </p>
          )}
          {op?.type === "card" && (
            <p className="text-sm text-gray-400 bg-gray-800 rounded-xl px-4 py-3">
              💳 Vous serez redirigé vers la page de paiement sécurisée par carte.
            </p>
          )}

          {error && (
            <p className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-xl px-4 py-3">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !selectedOp}
            className="w-full py-3 rounded-xl bg-green-600 hover:bg-green-500 disabled:opacity-50
                       disabled:cursor-not-allowed text-white font-semibold text-sm transition"
          >
            {loading ? "Traitement en cours…" : `Payer ${planInfo.price_xof} FCFA`}
          </button>

          <p className="text-xs text-gray-600 text-center">
            Paiement sécurisé par PayDunya · Licence activée après confirmation
          </p>
        </form>
      </div>
    </div>
  );
}
