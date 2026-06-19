/**
 * PaydunyaCheckout — page de paiement Mobile Money
 * Route : /checkout?plan=starter|pro|expert|expert_premium
 */
import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const PLANS_INFO = {
  starter:        { label: "Starter",        price_xof: "18 000", price_usd: "$29.99" },
  pro:            { label: "Pro",             price_xof: "45 000", price_usd: "$74.99" },
  expert:         { label: "Expert",          price_xof: "115 000", price_usd: "$199.99" },
  expert_premium: { label: "Expert Premium",  price_xof: "170 000", price_usd: "$299.99" },
};

// Opérateurs groupés par pays
const COUNTRIES = [
  {
    code: "CI", name: "Côte d'Ivoire", flag: "🇨🇮",
    operators: [
      { id: "wave-ci",          label: "Wave CI",         flag: "🌊", type: "wave",     frais: "1%" },
      { id: "orange-money-ci",  label: "Orange Money CI", flag: "🟠", type: "orange_ci",frais: "2%" },
      { id: "mtn-ci",           label: "MTN MoMo CI",     flag: "🟡", type: "phone",    frais: "2%" },
      { id: "moov-ci",          label: "Moov Money CI",   flag: "🔵", type: "phone",    frais: "2%" },
      { id: "djamo-ci",         label: "Djamo CI",        flag: "💜", type: "phone",    frais: "1.5%" },
    ],
  },
  {
    code: "SN", name: "Sénégal", flag: "🇸🇳",
    operators: [
      { id: "wave-senegal",          label: "Wave Sénégal",      flag: "🌊", type: "wave",  frais: "1%" },
      { id: "orange-money-senegal",  label: "Orange Money SN",   flag: "🟠", type: "phone", frais: "2%" },
      { id: "free-money-senegal",    label: "Free Money SN",     flag: "🟣", type: "phone", frais: "2%" },
      { id: "expresso-sn",           label: "Expresso SN",       flag: "🔴", type: "phone", frais: "2%" },
      { id: "wizall-senegal",        label: "Wizall SN",         flag: "🟢", type: "phone", frais: "2%" },
      { id: "djamo-sn",             label: "Djamo SN",           flag: "💜", type: "phone", frais: "1.5%" },
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
      { id: "mtn-benin",   label: "MTN MoMo BJ", flag: "🟡", type: "phone", frais: "2%" },
      { id: "moov-benin",  label: "Moov Bénin",  flag: "🔵", type: "phone", frais: "2%" },
    ],
  },
  {
    code: "CM", name: "Cameroun", flag: "🇨🇲",
    operators: [
      { id: "mtn-cameroun", label: "MTN MoMo CM", flag: "🟡", type: "phone", frais: "2%" },
    ],
  },
  {
    code: "ALL", name: "Carte bancaire (internationale)", flag: "🌍",
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

export default function PaydunyaCheckout() {
  const [params]   = useSearchParams();
  const navigate   = useNavigate();
  const { user, isAuthenticated } = useAuth();

  const planKey  = params.get("plan") || "starter";
  const planInfo = PLANS_INFO[planKey] || PLANS_INFO.starter;

  const [selectedOp, setSelectedOp] = useState(null);
  const [phone,      setPhone]      = useState("");
  const [loading,    setLoading]    = useState(false);
  const [result,     setResult]     = useState(null); // { success, redirect_url, payment_token, ussd_code, ... }
  const [error,      setError]      = useState("");

  useEffect(() => {
    if (!isAuthenticated) navigate("/login?redirect=/checkout?plan=" + planKey);
  }, [isAuthenticated]);

  const op = selectedOp ? findOperator(selectedOp) : null;
  const needsPhone = op && op.type !== "wave" && op.type !== "card";

  async function handleSubmit(e) {
    e.preventDefault();
    if (!selectedOp) { setError("Choisissez un opérateur de paiement."); return; }
    if (needsPhone && !phone.trim()) { setError("Entrez votre numéro de téléphone."); return; }
    setError("");
    setLoading(true);

    try {
      const resp = await fetch(`${API}/api/v1/paydunya/pay`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id:        user.id,
          plan:           planKey,
          operator:       selectedOp,
          phone:          phone.trim() || null,
          customer_name:  user.name || user.email || "Client Afrika Markets",
          customer_email: user.email || null,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Erreur PayDunya");
      setResult(data);

      // Wave & Card → redirection automatique
      if (data.redirect_url) {
        window.location.href = data.redirect_url;
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Affichage résultat (USSD / token) ────────────────────
  if (result && !result.redirect_url) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
        <div className="bg-gray-900 border border-gray-700 rounded-2xl p-8 max-w-md w-full text-center">
          <div className="text-4xl mb-4">📲</div>
          <h2 className="text-xl font-bold text-white mb-2">Paiement initié</h2>
          <p className="text-gray-400 text-sm mb-6">
            Validez la transaction sur votre téléphone — opérateur&nbsp;
            <strong className="text-white">{op?.label}</strong>.
          </p>

          {result.ussd_code && (
            <div className="bg-gray-800 rounded-xl p-4 mb-4">
              <p className="text-xs text-gray-500 mb-1">Code USSD</p>
              <p className="text-2xl font-mono font-bold text-brand-400">{result.ussd_code}</p>
            </div>
          )}

          {result.payment_token && (
            <div className="bg-gray-800 rounded-xl p-4 mb-4">
              <p className="text-xs text-gray-500 mb-1">Référence</p>
              <p className="font-mono text-sm text-gray-300 break-all">{result.ref}</p>
            </div>
          )}

          <p className="text-xs text-gray-500 mt-4">
            Votre licence sera activée automatiquement après confirmation du paiement.
          </p>

          <button
            onClick={() => navigate("/dashboard")}
            className="mt-6 w-full py-3 rounded-xl bg-brand-500 hover:bg-brand-400 text-white font-semibold text-sm transition"
          >
            Accéder à l'application →
          </button>
        </div>
      </div>
    );
  }

  // ── Formulaire de paiement ────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl p-8 max-w-lg w-full">

        {/* En-tête plan */}
        <div className="mb-6">
          <button onClick={() => navigate("/pricing")} className="text-gray-500 hover:text-gray-300 text-sm mb-4 flex items-center gap-1">
            ← Retour aux plans
          </button>
          <h1 className="text-2xl font-bold text-white">Souscrire — {planInfo.label}</h1>
          <p className="text-brand-400 text-lg font-semibold mt-1">
            {planInfo.price_xof} FCFA
            <span className="text-gray-500 text-sm font-normal ml-2">/ mois ({planInfo.price_usd})</span>
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">

          {/* Sélection opérateur par pays */}
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
                  {country.operators.map((op) => (
                    <button
                      key={op.id}
                      type="button"
                      onClick={() => { setSelectedOp(op.id); setError(""); }}
                      className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-sm transition-all
                                  ${selectedOp === op.id
                                    ? "border-brand-500 bg-brand-500/10 text-white"
                                    : "border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-500"}`}
                    >
                      <span>{op.flag}</span>
                      <span className="flex-1 text-left leading-tight">{op.label}</span>
                      <span className="text-xs text-gray-500">{op.frais}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Numéro de téléphone */}
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
                           placeholder-gray-500 focus:outline-none focus:border-brand-500 text-sm"
              />
              <p className="text-xs text-gray-500 mt-1">
                Format international recommandé (ex : +225 pour CI)
              </p>
            </div>
          )}

          {op?.type === "wave" && (
            <p className="text-sm text-gray-400 bg-gray-800 rounded-xl px-4 py-3">
              🌊 Vous serez redirigé vers l'application Wave pour valider le paiement.
            </p>
          )}

          {op?.type === "card" && (
            <p className="text-sm text-gray-400 bg-gray-800 rounded-xl px-4 py-3">
              💳 Vous serez redirigé vers la page de paiement sécurisée par carte bancaire.
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
            className="w-full py-3 rounded-xl bg-brand-500 hover:bg-brand-400 disabled:opacity-50
                       disabled:cursor-not-allowed text-white font-semibold text-sm transition"
          >
            {loading ? "Traitement en cours…" : `Payer ${planInfo.price_xof} FCFA`}
          </button>

          <p className="text-xs text-gray-600 text-center">
            Paiement sécurisé par PayDunya · Licence activée instantanément
          </p>
        </form>
      </div>
    </div>
  );
}
