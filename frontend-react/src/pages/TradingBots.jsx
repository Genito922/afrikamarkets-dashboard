/**
 * TradingBots — gestion multi-tenant des bots HFT
 * Route : /bots  (ProtectedRoute, plan STARTER+)
 *
 * Sections :
 *  1. Liste bots actifs (statut live, PnL, actions start/stop/delete)
 *  2. Créer un bot (modal)
 *  3. Gérer les credentials broker (accordéon)
 */
import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useBots, useCredentials } from "../hooks/useBots";
import { botsApi, credentialsApi } from "../api/bots";

// ── Constantes ────────────────────────────────────────────────────────────────

const PLAN_BOT_LIMIT = {
  free:           0,
  starter:        1,
  pro:            2,
  expert:         5,
  expert_premium: 5,
};

const PLAN_ALLOWED_MODES = {
  free:           [],
  starter:        ["paper"],
  pro:            ["paper", "testnet"],
  expert:         ["paper", "testnet", "live"],
  expert_premium: ["paper", "testnet", "live"],
};

const MODE_LABEL  = { paper: "Paper", testnet: "Testnet", live: "Live" };
const MODE_COLOR  = {
  paper:   "bg-gray-700 text-gray-300",
  testnet: "bg-blue-900/60 text-blue-300",
  live:    "bg-red-900/60 text-red-400",
};

const STATUS_COLOR = {
  idle:    "bg-gray-700 text-gray-400",
  running: "bg-green-900/60 text-green-400",
  stopped: "bg-yellow-900/60 text-yellow-400",
  error:   "bg-red-900/60 text-red-400",
};

const BROKERS    = ["binance", "exness", "deriv"];
const STRATEGIES = ["sma_crossover"];
const STRATEGY_LABEL = { sma_crossover: "SMA Crossover (Signal B)" };

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n) {
  if (n === null || n === undefined) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(2)} $`;
}

function fmtDate(d) {
  if (!d) return "—";
  return new Date(d).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function Toast({ toast }) {
  if (!toast) return null;
  const styles = {
    success: "bg-green-900/40 border-green-700 text-green-300",
    error:   "bg-red-900/40 border-red-700 text-red-300",
    info:    "bg-blue-900/40 border-blue-700 text-blue-300",
  };
  return (
    <div className={`px-4 py-3 rounded-xl text-sm font-medium border ${styles[toast.type] || styles.info}`}>
      {toast.message}
    </div>
  );
}

// ── BotCard ───────────────────────────────────────────────────────────────────

function BotCard({ bot, onAction, busy }) {
  const isRunning = bot.status === "running";
  const pnlColor  = bot.pnl_total >= 0 ? "text-green-400" : "text-red-400";
  const actionBusy = busy === bot.id;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-white">{bot.name}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${MODE_COLOR[bot.mode]}`}>
              {MODE_LABEL[bot.mode]}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[bot.status]}`}>
              {isRunning && (
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse mr-1" />
              )}
              {bot.status}
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {bot.broker.toUpperCase()} · {bot.symbol} · {STRATEGY_LABEL[bot.strategy] || bot.strategy}
          </div>
        </div>

        {/* PnL */}
        <div className="text-right shrink-0">
          <div className={`text-lg font-bold tabular-nums ${pnlColor}`}>{fmt(bot.pnl_total)}</div>
          <div className="text-xs text-gray-500">{bot.trades_count} trades</div>
        </div>
      </div>

      {/* Stats row */}
      {bot.mode === "paper" && (
        <div className="text-xs text-gray-400">
          Solde paper : <span className="text-white font-medium">{bot.paper_balance?.toFixed(2)} $</span>
        </div>
      )}

      {bot.last_error && (
        <div className="text-xs text-red-400 bg-red-900/20 rounded-lg px-3 py-2 break-words">
          {bot.last_error}
        </div>
      )}

      {bot.started_at && (
        <div className="text-xs text-gray-500">
          {isRunning ? "Démarré" : "Arrêté"} le {fmtDate(bot.started_at)}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 flex-wrap pt-1">
        {!isRunning ? (
          <button
            disabled={actionBusy}
            onClick={() => onAction("start", bot)}
            className="flex-1 btn-primary text-xs py-2 disabled:opacity-50"
          >
            {actionBusy ? "..." : "Démarrer"}
          </button>
        ) : (
          <button
            disabled={actionBusy}
            onClick={() => onAction("stop", bot)}
            className="flex-1 bg-yellow-900/40 hover:bg-yellow-800/60 border border-yellow-700 text-yellow-300 text-xs py-2 px-4 rounded-xl font-medium transition-colors disabled:opacity-50"
          >
            {actionBusy ? "..." : "Arrêter"}
          </button>
        )}

        {bot.mode === "live" && !bot.confirmed_live && (
          <button
            disabled={actionBusy}
            onClick={() => onAction("confirmLive", bot)}
            className="text-xs px-3 py-2 rounded-xl border border-orange-700 text-orange-400 hover:bg-orange-900/30 transition-colors disabled:opacity-50"
          >
            Confirmer live
          </button>
        )}

        <button
          disabled={actionBusy || isRunning}
          onClick={() => onAction("delete", bot)}
          className="text-xs px-3 py-2 rounded-xl border border-gray-700 text-gray-400 hover:text-red-400 hover:border-red-700 transition-colors disabled:opacity-50"
          title={isRunning ? "Arrêtez le bot avant de supprimer" : "Supprimer"}
        >
          Supprimer
        </button>
      </div>
    </div>
  );
}

// ── CreateBotModal ────────────────────────────────────────────────────────────

function CreateBotModal({ plan, creds, onClose, onCreated }) {
  const allowedModes = PLAN_ALLOWED_MODES[plan] || [];
  const [form, setForm] = useState({
    name: "",
    broker: "binance",
    symbol: "BTCUSDT",
    strategy: "sma_crossover",
    mode: allowedModes[0] || "paper",
    paper_balance: 10000,
    credential_id: "",
    params: { fast: 9, slow: 21, qty: 0.01, stop_pct: 0.015, tp_pct: 0.03 },
  });
  const [busy,  setBusy]  = useState(false);
  const [error, setError] = useState(null);

  const needsCredential = form.mode !== "paper";

  function set(k, v) { setForm(p => ({ ...p, [k]: v })); }
  function setParam(k, v) { setForm(p => ({ ...p, params: { ...p.params, [k]: parseFloat(v) || 0 } })); }

  async function submit(e) {
    e.preventDefault();
    setError(null);
    if (!form.name.trim()) { setError("Donnez un nom au bot."); return; }
    if (needsCredential && !form.credential_id) {
      setError("Sélectionnez un credential broker pour les modes Testnet/Live."); return;
    }
    setBusy(true);
    try {
      await botsApi.create({
        name:          form.name.trim(),
        broker:        form.broker,
        symbol:        form.symbol.toUpperCase().trim(),
        strategy:      form.strategy,
        mode:          form.mode,
        paper_balance: parseFloat(form.paper_balance) || 10000,
        credential_id: form.credential_id || null,
        params:        form.params,
      });
      onCreated();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="bg-gray-950 border border-gray-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-y-auto max-h-[90vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h2 className="text-white font-semibold text-base">Nouveau bot</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl leading-none">×</button>
        </div>

        <form onSubmit={submit} className="px-6 py-5 flex flex-col gap-4">
          {error && (
            <div className="text-sm text-red-400 bg-red-900/20 rounded-xl px-4 py-3">{error}</div>
          )}

          {/* Nom */}
          <label className="flex flex-col gap-1">
            <span className="text-xs text-gray-400 font-medium">Nom du bot</span>
            <input
              className="input-dark"
              value={form.name}
              onChange={e => set("name", e.target.value)}
              placeholder="Mon bot BTC"
              required
            />
          </label>

          {/* Broker + Symbol */}
          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1">
              <span className="text-xs text-gray-400 font-medium">Broker</span>
              <select className="input-dark" value={form.broker} onChange={e => set("broker", e.target.value)}>
                {BROKERS.map(b => <option key={b} value={b}>{b.charAt(0).toUpperCase() + b.slice(1)}</option>)}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs text-gray-400 font-medium">Symbole</span>
              <input
                className="input-dark"
                value={form.symbol}
                onChange={e => set("symbol", e.target.value)}
                placeholder="BTCUSDT"
              />
            </label>
          </div>

          {/* Mode */}
          <label className="flex flex-col gap-1">
            <span className="text-xs text-gray-400 font-medium">Mode d'exécution</span>
            <div className="flex gap-2 flex-wrap">
              {["paper", "testnet", "live"].map(m => {
                const allowed = allowedModes.includes(m);
                return (
                  <button
                    key={m}
                    type="button"
                    disabled={!allowed}
                    onClick={() => allowed && set("mode", m)}
                    className={`px-4 py-2 rounded-xl text-xs font-medium border transition-colors ${
                      form.mode === m
                        ? "bg-brand-600 border-brand-500 text-white"
                        : allowed
                          ? "border-gray-700 text-gray-400 hover:border-gray-500"
                          : "border-gray-800 text-gray-600 cursor-not-allowed"
                    }`}
                  >
                    {MODE_LABEL[m]}
                    {!allowed && " 🔒"}
                  </button>
                );
              })}
            </div>
            {form.mode === "live" && (
              <p className="text-xs text-orange-400 mt-1">
                Mode live : vous devrez confirmer explicitement avant de démarrer.
              </p>
            )}
          </label>

          {/* Paper balance */}
          {form.mode === "paper" && (
            <label className="flex flex-col gap-1">
              <span className="text-xs text-gray-400 font-medium">Solde paper ($)</span>
              <input
                type="number"
                className="input-dark"
                value={form.paper_balance}
                onChange={e => set("paper_balance", e.target.value)}
                min={100}
              />
            </label>
          )}

          {/* Credential */}
          {needsCredential && (
            <label className="flex flex-col gap-1">
              <span className="text-xs text-gray-400 font-medium">Credential broker</span>
              <select
                className="input-dark"
                value={form.credential_id}
                onChange={e => set("credential_id", e.target.value)}
                required
              >
                <option value="">-- Sélectionner --</option>
                {creds
                  .filter(c => c.broker === form.broker)
                  .map(c => (
                    <option key={c.id} value={c.id}>
                      {c.label} {c.is_testnet ? "(testnet)" : "(prod)"}
                    </option>
                  ))
                }
              </select>
              {creds.filter(c => c.broker === form.broker).length === 0 && (
                <span className="text-xs text-yellow-400">
                  Aucun credential {form.broker} enregistré — ajoutez-en un ci-dessous.
                </span>
              )}
            </label>
          )}

          {/* Paramètres SMA */}
          <div className="border border-gray-800 rounded-xl p-4 flex flex-col gap-3">
            <span className="text-xs text-gray-400 font-medium">Paramètres SMA Crossover</span>
            <div className="grid grid-cols-2 gap-3">
              {[
                ["fast",     "SMA rapide (périodes)", 1],
                ["slow",     "SMA lente (périodes)",  1],
                ["qty",      "Taille position",        0.0001],
                ["stop_pct", "Stop-loss (%)",           0.001],
                ["tp_pct",   "Take-profit (%)",         0.001],
              ].map(([k, label, step]) => (
                <label key={k} className="flex flex-col gap-1">
                  <span className="text-xs text-gray-500">{label}</span>
                  <input
                    type="number"
                    step={step}
                    className="input-dark text-sm"
                    value={form.params[k]}
                    onChange={e => setParam(k, e.target.value)}
                  />
                </label>
              ))}
            </div>
          </div>

          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} className="flex-1 btn-secondary text-sm py-2.5">
              Annuler
            </button>
            <button type="submit" disabled={busy} className="flex-1 btn-primary text-sm py-2.5 disabled:opacity-50">
              {busy ? "Création..." : "Créer le bot"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── CredentialPanel ───────────────────────────────────────────────────────────

function CredentialPanel({ creds, onRefresh }) {
  const [open,  setOpen]  = useState(false);
  const [form,  setForm]  = useState({ broker: "binance", api_key: "", api_secret: "", label: "default", is_testnet: false, extra: "" });
  const [busy,  setBusy]  = useState(false);
  const [error, setError] = useState(null);

  function set(k, v) { setForm(p => ({ ...p, [k]: v })); }

  async function save(e) {
    e.preventDefault();
    setError(null);
    if (!form.api_key) { setError("API key requise."); return; }
    setBusy(true);
    try {
      let extra = undefined;
      if (form.extra.trim()) {
        try { extra = JSON.parse(form.extra); }
        catch { setError("Extra doit être un JSON valide."); setBusy(false); return; }
      }
      await credentialsApi.save({
        broker:     form.broker,
        api_key:    form.api_key,
        api_secret: form.api_secret || undefined,
        label:      form.label || "default",
        is_testnet: form.is_testnet,
        extra,
      });
      setForm({ broker: "binance", api_key: "", api_secret: "", label: "default", is_testnet: false, extra: "" });
      setOpen(false);
      onRefresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function del(id) {
    if (!window.confirm("Supprimer ce credential ?")) return;
    try {
      await credentialsApi.delete(id);
      onRefresh();
    } catch (e) {
      alert(e.message);
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-800/50 transition-colors"
      >
        <span className="text-sm font-medium text-white">
          Credentials broker
          <span className="ml-2 text-xs text-gray-500">({creds.length})</span>
        </span>
        <span className="text-gray-400 text-lg leading-none">{open ? "−" : "+"}</span>
      </button>

      {open && (
        <div className="border-t border-gray-800 px-5 py-4 flex flex-col gap-4">

          {/* Liste */}
          {creds.length === 0 ? (
            <p className="text-sm text-gray-500">Aucun credential enregistré.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {creds.map(c => (
                <div key={c.id} className="flex items-center justify-between bg-gray-950 rounded-xl px-4 py-3">
                  <div>
                    <span className="text-sm text-white font-medium">{c.broker.toUpperCase()}</span>
                    <span className="text-xs text-gray-400 ml-2">{c.label}</span>
                    {c.is_testnet && <span className="ml-2 text-xs text-blue-400">(testnet)</span>}
                    <div className="text-xs text-gray-500 mt-0.5">
                      {c.has_api_key && "key ✓"} {c.has_api_secret && "secret ✓"} {c.has_extra && "extra ✓"}
                    </div>
                  </div>
                  <button
                    onClick={() => del(c.id)}
                    className="text-xs text-gray-500 hover:text-red-400 transition-colors px-2"
                  >
                    Supprimer
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Formulaire ajout */}
          <form onSubmit={save} className="flex flex-col gap-3 border-t border-gray-800 pt-4">
            <span className="text-xs text-gray-400 font-medium">Ajouter un credential</span>
            {error && <div className="text-xs text-red-400">{error}</div>}

            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1">
                <span className="text-xs text-gray-500">Broker</span>
                <select className="input-dark text-sm" value={form.broker} onChange={e => set("broker", e.target.value)}>
                  {BROKERS.map(b => <option key={b} value={b}>{b}</option>)}
                </select>
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-gray-500">Label</span>
                <input className="input-dark text-sm" value={form.label} onChange={e => set("label", e.target.value)} placeholder="default" />
              </label>
            </div>

            <label className="flex flex-col gap-1">
              <span className="text-xs text-gray-500">API Key</span>
              <input type="password" className="input-dark text-sm" value={form.api_key} onChange={e => set("api_key", e.target.value)} placeholder="••••••••••••" />
            </label>

            <label className="flex flex-col gap-1">
              <span className="text-xs text-gray-500">API Secret (optionnel selon broker)</span>
              <input type="password" className="input-dark text-sm" value={form.api_secret} onChange={e => set("api_secret", e.target.value)} placeholder="••••••••••••" />
            </label>

            <label className="flex flex-col gap-1">
              <span className="text-xs text-gray-500">Extra (JSON, ex: {"{"}"login":12345,"server":"Exness-MT5Real"{"}"} pour Exness)</span>
              <textarea
                className="input-dark text-sm font-mono resize-none h-16"
                value={form.extra}
                onChange={e => set("extra", e.target.value)}
                placeholder='{}'
              />
            </label>

            <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer select-none">
              <input type="checkbox" checked={form.is_testnet} onChange={e => set("is_testnet", e.target.checked)} className="accent-brand-500" />
              Compte testnet / sandbox
            </label>

            <button type="submit" disabled={busy} className="btn-primary text-sm py-2.5 disabled:opacity-50">
              {busy ? "Enregistrement..." : "Enregistrer (chiffré)"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

// ── LiveConfirmBanner ─────────────────────────────────────────────────────────

function LiveConfirmBanner({ bot, onConfirmed }) {
  const [busy, setBusy] = useState(false);
  async function confirm() {
    setBusy(true);
    try { await botsApi.confirmLive(bot.id); onConfirmed(); }
    catch (e) { alert(e.message); }
    finally { setBusy(false); }
  }
  return (
    <div className="bg-orange-900/20 border border-orange-700 rounded-xl px-5 py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
      <div>
        <p className="text-sm font-medium text-orange-300">Confirmation requise — Mode Live</p>
        <p className="text-xs text-orange-400/80 mt-0.5">
          Le bot <span className="font-semibold">{bot.name}</span> utilisera des fonds réels. Confirmez avant de démarrer.
        </p>
      </div>
      <button disabled={busy} onClick={confirm} className="shrink-0 px-4 py-2 rounded-xl bg-orange-700 hover:bg-orange-600 text-white text-xs font-medium transition-colors disabled:opacity-50">
        {busy ? "..." : "Je confirme — mode live"}
      </button>
    </div>
  );
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function TradingBots() {
  const { plan } = useAuth();
  const { bots,  loading: botsLoading,  error: botsError,  refresh: refreshBots  } = useBots();
  const { creds, loading: credsLoading, error: credsError, refresh: refreshCreds } = useCredentials();

  const [showCreate, setShowCreate] = useState(false);
  const [busy, setBusy]  = useState(null);  // bot_id en cours d'action
  const [toast, setToast] = useState(null);

  // Polling statut bots en cours (toutes les 5s si au moins un bot running)
  const pollRef = useRef(null);
  useEffect(() => {
    const hasRunning = bots.some(b => b.status === "running");
    if (hasRunning) {
      pollRef.current = setInterval(refreshBots, 5000);
    } else {
      clearInterval(pollRef.current);
    }
    return () => clearInterval(pollRef.current);
  }, [bots, refreshBots]);

  const limit = PLAN_BOT_LIMIT[plan] || 0;
  const atLimit = bots.length >= limit;

  function notify(type, message) {
    setToast({ type, message });
    setTimeout(() => setToast(null), 4000);
  }

  async function handleAction(action, bot) {
    setBusy(bot.id);
    try {
      if (action === "start")       await botsApi.start(bot.id);
      if (action === "stop")        await botsApi.stop(bot.id);
      if (action === "confirmLive") await botsApi.confirmLive(bot.id);
      if (action === "delete") {
        if (!window.confirm(`Supprimer "${bot.name}" ?`)) { setBusy(null); return; }
        await botsApi.delete(bot.id);
        notify("success", `Bot "${bot.name}" supprimé.`);
      } else {
        const labels = { start: "démarré", stop: "arrêté", confirmLive: "mode live confirmé" };
        notify("success", `Bot "${bot.name}" ${labels[action]}.`);
      }
      refreshBots();
    } catch (e) {
      notify("error", e.message);
    } finally {
      setBusy(null);
    }
  }

  // Bots nécessitant une confirmation live
  const pendingLiveConfirm = bots.filter(b => b.mode === "live" && !b.confirmed_live);

  if (plan === "free") {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12 text-center">
        <div className="text-5xl mb-4">🤖</div>
        <h1 className="text-2xl font-bold text-white mb-2">Bots de trading</h1>
        <p className="text-gray-400 mb-6">
          Automatisez vos stratégies sur Binance, Exness et Deriv. Disponible dès le plan Starter.
        </p>
        <a href="/pricing" className="btn-primary px-8 py-3">Voir les plans</a>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 flex flex-col gap-6">

      {/* En-tête */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <span>🤖</span> Bots de trading
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            {bots.length}/{limit} bot{limit > 1 ? "s" : ""} · plan{" "}
            <span className="text-white font-medium capitalize">{plan}</span>
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/bots/dashboard" className="btn-secondary text-sm py-2.5 px-4">
            📊 Dashboard
          </Link>
          <button
            onClick={() => setShowCreate(true)}
            disabled={atLimit || limit === 0}
            className="btn-primary text-sm py-2.5 px-5 disabled:opacity-40"
            title={atLimit ? "Limite de bots atteinte" : ""}
          >
            + Nouveau bot
          </button>
        </div>
      </div>

      {/* Toast */}
      <Toast toast={toast} />

      {/* Banners confirmation live */}
      {pendingLiveConfirm.map(b => (
        <LiveConfirmBanner key={b.id} bot={b} onConfirmed={refreshBots} />
      ))}

      {/* Liste bots */}
      {botsLoading ? (
        <div className="text-center text-gray-500 py-10">Chargement...</div>
      ) : botsError ? (
        <div className="text-red-400 text-sm">{botsError}</div>
      ) : bots.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 border-dashed rounded-2xl px-6 py-12 text-center">
          <p className="text-gray-500 text-sm">Aucun bot configuré.</p>
          <button onClick={() => setShowCreate(true)} className="mt-3 text-brand-400 text-sm hover:underline">
            Créer votre premier bot →
          </button>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {bots.map(bot => (
            <BotCard key={bot.id} bot={bot} onAction={handleAction} busy={busy} />
          ))}
        </div>
      )}

      {/* Credentials */}
      {(plan === "pro" || plan === "expert" || plan === "expert_premium") && (
        <CredentialPanel
          creds={creds}
          onRefresh={refreshCreds}
        />
      )}

      {/* Info plans */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-2xl px-5 py-4">
        <h3 className="text-xs font-semibold text-gray-400 mb-3 uppercase tracking-wider">Limites par plan</h3>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
          {[
            { p: "free",           label: "Free",           limit: "0 bot",    modes: "—" },
            { p: "starter",        label: "Starter",        limit: "1 bot",    modes: "Paper" },
            { p: "pro",            label: "Pro",            limit: "2 bots",   modes: "Paper + Testnet" },
            { p: "expert",         label: "Expert",         limit: "5 bots",   modes: "Paper + Testnet + Live" },
            { p: "expert_premium", label: "Expert Premium", limit: "5 bots",   modes: "Paper + Testnet + Live" },
          ].map(({ p, label, limit, modes }) => (
            <div
              key={p}
              className={`rounded-xl p-3 border ${p === plan ? "border-brand-600 bg-brand-900/20" : "border-gray-800 bg-gray-900/30"}`}
            >
              <div className={`font-semibold mb-1 ${p === plan ? "text-brand-300" : "text-white"}`}>{label}</div>
              <div className="text-gray-400">{limit}</div>
              <div className="text-gray-500 mt-1">{modes}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Modal création */}
      {showCreate && (
        <CreateBotModal
          plan={plan}
          creds={creds}
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); refreshBots(); notify("success", "Bot créé avec succès."); }}
        />
      )}
    </div>
  );
}
