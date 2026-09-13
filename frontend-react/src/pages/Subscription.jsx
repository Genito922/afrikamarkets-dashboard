/**
 * Subscription — gestion du cycle de vie de l'abonnement
 * Route : /subscription (ProtectedRoute)
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSubscription } from "../hooks/useSubscription";
import { subscriptionsApi } from "../api/subscriptions";

// ── Constantes ────────────────────────────────────────────────

const PLAN_LABELS = {
  free:           "Gratuit",
  starter:        "Starter",
  pro:            "Pro",
  expert:         "Expert",
  expert_premium: "Expert Premium",
};

const PLAN_ORDER = ["free", "starter", "pro", "expert", "expert_premium"];

const PLAN_PRICES = {
  free:           { xof: "0",       usd: "$0" },
  starter:        { xof: "18 000",  usd: "$29.99" },
  pro:            { xof: "45 000",  usd: "$74.99" },
  expert:         { xof: "115 000", usd: "$199.99" },
  expert_premium: { xof: "170 000", usd: "$299.99" },
};

// ── Toast inline ──────────────────────────────────────────────

function Toast({ toast }) {
  if (!toast) return null;
  const base = "px-4 py-3 rounded-xl text-sm font-medium border";
  const styles = {
    success: "bg-green-900/40 border-green-700 text-green-300",
    error:   "bg-red-900/40  border-red-700  text-red-300",
  };
  return <div className={`${base} ${styles[toast.type] || styles.error}`}>{toast.message}</div>;
}

// ── Composant principal ───────────────────────────────────────

export default function Subscription() {
  const { data, loading, error, refresh } = useSubscription();
  const [busy,  setBusy]  = useState(null);   // clé de l'action en cours
  const [toast, setToast] = useState(null);
  const navigate = useNavigate();

  function notify(type, message) {
    setToast({ type, message });
    setTimeout(() => setToast(null), 4500);
  }

  async function run(key, action) {
    setBusy(key);
    try {
      await action();
      await refresh();
    } catch (err) {
      notify("error", err.message || "Action impossible");
    } finally {
      setBusy(null);
    }
  }

  // ── Skeleton ─────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="animate-pulse text-gray-500 text-sm">Chargement de votre abonnement…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-6">
        <div className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-xl px-6 py-4">
          {error}
        </div>
      </div>
    );
  }

  const {
    plan,
    status,
    cancel_at_period_end,
    pending_plan,
    current_period_end,
    days_remaining,
    payment_history = [],
  } = data;

  const currentIdx  = PLAN_ORDER.indexOf(plan);
  const isCancelled = Boolean(cancel_at_period_end);
  const hasPending  = Boolean(pending_plan);
  const isActive    = status === "active";
  const periodEnd   = current_period_end
    ? new Date(current_period_end).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })
    : null;

  // ── Render ────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-950 px-4 py-10">
      <div className="max-w-2xl mx-auto space-y-6">

        {/* Titre */}
        <div>
          <h1 className="text-2xl font-bold text-white">Mon abonnement</h1>
          <p className="text-gray-500 text-sm mt-1">Gérez votre plan, vos renouvellements et votre historique.</p>
        </div>

        <Toast toast={toast} />

        {/* ── État courant ─────────────────────────────── */}
        <section className="bg-gray-900 border border-gray-700 rounded-2xl p-6 space-y-3">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Plan actuel</h2>

          <div className="flex items-center justify-between">
            <div>
              <span className="text-xl font-bold text-white">{PLAN_LABELS[plan] || plan}</span>
              <span className="ml-3 text-sm text-gray-500">
                {PLAN_PRICES[plan]?.xof} FCFA / mois
              </span>
            </div>
            <span className={`text-xs font-medium px-3 py-1 rounded-full border ${
              isActive
                ? "bg-green-900/30 border-green-700 text-green-400"
                : "bg-gray-800 border-gray-600 text-gray-400"
            }`}>
              {status === "active" ? "Actif" : status === "trial" ? "Essai" : "Inactif"}
            </span>
          </div>

          {periodEnd && (
            <p className="text-sm text-gray-400">
              Prochaine échéance :{" "}
              <span className="text-white font-medium">{periodEnd}</span>
              {days_remaining !== null && (
                <span className="text-gray-500 ml-2">({days_remaining} j restants)</span>
              )}
            </p>
          )}

          {isCancelled && (
            <div className="flex items-start gap-2 bg-amber-900/20 border border-amber-800 rounded-xl px-4 py-3">
              <span className="text-amber-400 mt-0.5">⚠</span>
              <p className="text-amber-300 text-sm">
                Annulation programmée — accès maintenu jusqu'au {periodEnd || "fin de période"}.
              </p>
            </div>
          )}

          {hasPending && !isCancelled && (
            <div className="flex items-start gap-2 bg-blue-900/20 border border-blue-800 rounded-xl px-4 py-3">
              <span className="text-blue-400 mt-0.5">↓</span>
              <p className="text-blue-300 text-sm">
                Downgrade vers <strong>{PLAN_LABELS[pending_plan]}</strong> programmé le {periodEnd || "fin de période"}.
              </p>
            </div>
          )}
        </section>

        {/* ── Actions ──────────────────────────────────── */}
        <section className="bg-gray-900 border border-gray-700 rounded-2xl p-6 space-y-3">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Actions</h2>

          {/* Reprendre (si annulation ou downgrade en attente) */}
          {(isCancelled || hasPending) && (
            <button
              disabled={busy !== null}
              onClick={() => run("resume", async () => {
                await subscriptionsApi.resume();
                notify("success", "Abonnement maintenu — aucun changement programmé");
              })}
              className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-semibold transition"
            >
              {busy === "resume" ? "…" : "Reprendre mon abonnement"}
            </button>
          )}

          {/* Upgrade (plan suivant) */}
          {currentIdx < PLAN_ORDER.length - 1 && !isCancelled && !hasPending && (
            <button
              disabled={busy !== null}
              onClick={() => {
                const target = PLAN_ORDER[currentIdx + 1];
                navigate(`/checkout?plan=${target}`);
              }}
              className="w-full py-3 rounded-xl bg-brand-500 hover:bg-brand-400 disabled:opacity-50 text-white text-sm font-semibold transition"
              style={{ backgroundColor: busy ? undefined : "#16a34a" }}
            >
              {busy?.startsWith("upgrade")
                ? "…"
                : `Passer à ${PLAN_LABELS[PLAN_ORDER[currentIdx + 1]]} — ${PLAN_PRICES[PLAN_ORDER[currentIdx + 1]]?.xof} FCFA/mois`}
            </button>
          )}

          {/* Downgrade (plan précédent) */}
          {currentIdx > 0 && plan !== "free" && !isCancelled && !hasPending && (
            <button
              disabled={busy !== null}
              onClick={() => {
                const target = PLAN_ORDER[currentIdx - 1];
                run("downgrade", async () => {
                  await subscriptionsApi.downgrade(target);
                  notify("success", `Downgrade vers ${PLAN_LABELS[target]} programmé pour le ${periodEnd || "fin de période"}`);
                });
              }}
              className="w-full py-3 rounded-xl bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white text-sm font-semibold transition"
            >
              {busy === "downgrade"
                ? "…"
                : `Rétrograder vers ${PLAN_LABELS[PLAN_ORDER[currentIdx - 1]]}`}
            </button>
          )}

          {/* Annuler */}
          {isActive && plan !== "free" && !isCancelled && !hasPending && (
            <button
              disabled={busy !== null}
              onClick={() => run("cancel", async () => {
                await subscriptionsApi.cancel();
                notify("success", `Annulation programmée — accès maintenu jusqu'au ${periodEnd || "fin de période"}`);
              })}
              className="w-full py-3 rounded-xl border border-red-800 hover:bg-red-900/20 disabled:opacity-50 text-red-400 text-sm font-semibold transition"
            >
              {busy === "cancel" ? "…" : "Annuler à la fin de période"}
            </button>
          )}

          {plan === "free" && (
            <button
              onClick={() => navigate("/pricing")}
              className="w-full py-3 rounded-xl text-sm font-semibold text-white transition"
              style={{ backgroundColor: "#16a34a" }}
            >
              Voir les plans →
            </button>
          )}
        </section>

        {/* ── Historique paiements ──────────────────────── */}
        <section className="bg-gray-900 border border-gray-700 rounded-2xl p-6">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
            Historique des paiements
          </h2>

          {payment_history.length === 0 ? (
            <p className="text-gray-500 text-sm">Aucun paiement enregistré.</p>
          ) : (
            <div className="divide-y divide-gray-800">
              {payment_history.map((p, i) => (
                <div key={i} className="flex items-center justify-between py-3 text-sm">
                  <div>
                    <p className="text-white font-medium">{PLAN_LABELS[p.plan] || p.plan}</p>
                    <p className="text-gray-500 text-xs mt-0.5">
                      {p.date ? new Date(p.date).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" }) : "—"}
                      {p.method && <span className="ml-2 capitalize">{p.method.replace(/-/g, " ")}</span>}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-white font-semibold">{p.amount?.toLocaleString("fr-FR")} {p.currency}</p>
                    <p className="text-xs text-gray-600 font-mono mt-0.5">{p.ref}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ── Note migration ───────────────────────────── */}
        <p className="text-xs text-gray-600 text-center pb-4">
          Les changements de plan prennent effet à la fin de la période en cours · Support : support@afrikamarkets.com
        </p>
      </div>
    </div>
  );
}
