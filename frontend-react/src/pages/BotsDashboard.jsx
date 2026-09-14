/**
 * BotsDashboard — Analytics fleet des bots de trading
 * Route : /bots/dashboard  (ProtectedRoute, plan STARTER+)
 *
 * Sections :
 *  1. KPI fleet : PnL total, bots actifs, nb trades, win rate
 *  2. Equity curve cumulée (AreaChart recharts)
 *  3. Table bots : PnL / win rate / statut par bot
 *  4. Log 20 derniers trades (avec filtre par bot)
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { apiGet } from "../lib/api";
import { useAuth } from "../context/AuthContext";

// ── Constantes ────────────────────────────────────────────────────────────────

const MODE_COLOR = {
  paper:   "text-gray-400",
  testnet: "text-blue-400",
  live:    "text-red-400",
};

const STATUS_DOT = {
  running: "bg-green-400 animate-pulse",
  idle:    "bg-gray-500",
  stopped: "bg-yellow-500",
  error:   "bg-red-500",
};

const REASON_BADGE = {
  signal:      "bg-gray-800 text-gray-300",
  stop_loss:   "bg-red-900/60 text-red-400",
  take_profit: "bg-green-900/60 text-green-400",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function pnlCls(v) { return v >= 0 ? "text-green-400" : "text-red-400"; }
function pnlFmt(v, prefix = true) {
  if (v == null) return "—";
  const sign = prefix && v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(4)} $`;
}
function pct(v) { return v == null ? "—" : `${v.toFixed(1)} %`; }
function fmtDt(s) {
  if (!s) return "—";
  return new Date(s).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

// ── Squelette (skeleton loader) ───────────────────────────────────────────────

function Skeleton({ className = "" }) {
  return <div className={`bg-gray-800 rounded-lg animate-pulse ${className}`} />;
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, colorCls = "text-white", loading }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl px-5 py-4">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      {loading
        ? <Skeleton className="h-7 w-3/4 mt-1" />
        : <p className={`text-2xl font-bold tabular-nums ${colorCls}`}>{value ?? "—"}</p>
      }
      {sub && !loading && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

// ── Custom Tooltip recharts ───────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const v = payload[0]?.value;
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-xs shadow-xl">
      <p className="text-gray-400 mb-1">{label}</p>
      <p className={`font-bold ${v >= 0 ? "text-green-400" : "text-red-400"}`}>
        Cumul : {v >= 0 ? "+" : ""}{v?.toFixed(4)} $
      </p>
    </div>
  );
}

// ── Per-bot row ───────────────────────────────────────────────────────────────

function BotRow({ bot, selected, onSelect }) {
  return (
    <tr
      onClick={() => onSelect(bot.id === selected ? null : bot.id)}
      className={`border-b border-gray-800 cursor-pointer transition-colors text-sm ${
        bot.id === selected ? "bg-gray-800/60" : "hover:bg-gray-900/60"
      }`}
    >
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${STATUS_DOT[bot.status] || "bg-gray-600"}`} />
          <span className="text-white font-medium truncate max-w-[120px]">{bot.name}</span>
        </div>
      </td>
      <td className="px-4 py-3 text-gray-400">
        <span className="text-xs">{bot.broker.toUpperCase()}</span>
        <span className="text-gray-600 mx-1">·</span>
        <span className="font-mono text-xs">{bot.symbol}</span>
      </td>
      <td className={`px-4 py-3 text-xs font-medium ${MODE_COLOR[bot.mode]}`}>
        {bot.mode}
      </td>
      <td className={`px-4 py-3 font-bold tabular-nums ${pnlCls(bot.pnl_total)}`}>
        {pnlFmt(bot.pnl_total)}
      </td>
      <td className="px-4 py-3 text-gray-300 tabular-nums">{bot.trades_count}</td>
      <td className="px-4 py-3 text-gray-300 tabular-nums">{pct(bot.win_rate)}</td>
      <td className="px-4 py-3">
        <span className={`inline-block w-2 h-2 rounded-full mr-1 ${STATUS_DOT[bot.status] || "bg-gray-600"}`} />
        <span className="text-xs text-gray-400 capitalize">{bot.status}</span>
      </td>
    </tr>
  );
}

// ── Trade row ─────────────────────────────────────────────────────────────────

function TradeRow({ trade, botName }) {
  return (
    <tr className="border-b border-gray-800/60 text-xs hover:bg-gray-900/40 transition-colors">
      <td className="px-4 py-2.5 text-gray-500 whitespace-nowrap">{fmtDt(trade.created_at)}</td>
      <td className="px-4 py-2.5 text-gray-400 truncate max-w-[100px]">{botName}</td>
      <td className="px-4 py-2.5 font-mono text-gray-300">{trade.symbol}</td>
      <td className="px-4 py-2.5">
        <span className={`font-semibold ${trade.side === "buy" ? "text-green-400" : "text-red-400"}`}>
          {trade.side.toUpperCase()}
        </span>
      </td>
      <td className="px-4 py-2.5 text-gray-400 tabular-nums">{trade.qty}</td>
      <td className="px-4 py-2.5 text-gray-400 tabular-nums">{trade.entry_price?.toFixed(4) ?? "—"}</td>
      <td className="px-4 py-2.5 text-gray-400 tabular-nums">{trade.exit_price?.toFixed(4) ?? "—"}</td>
      <td className={`px-4 py-2.5 font-bold tabular-nums ${pnlCls(trade.pnl)}`}>
        {pnlFmt(trade.pnl)}
      </td>
      <td className="px-4 py-2.5">
        {trade.reason && (
          <span className={`px-2 py-0.5 rounded-full text-xs ${REASON_BADGE[trade.reason] || "bg-gray-800 text-gray-400"}`}>
            {trade.reason}
          </span>
        )}
      </td>
    </tr>
  );
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function BotsDashboard() {
  const { plan } = useAuth();
  const [data,       setData]       = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [selectedBot, setSelectedBot] = useState(null);  // filtre log par bot_id
  const [range,      setRange]      = useState("all");   // filtre equity curve
  const pollRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const d = await apiGet("/bots/dashboard/summary", true);
      setData(d);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Polling 10s si au moins un bot running
  useEffect(() => {
    if (!data) return;
    clearInterval(pollRef.current);
    if (data.running_count > 0) {
      pollRef.current = setInterval(load, 10_000);
    }
    return () => clearInterval(pollRef.current);
  }, [data, load]);

  // ── Dérivés ─────────────────────────────────────────────────────────────────

  const equity = (() => {
    if (!data?.equity_curve?.length) return [];
    const now = Date.now();
    const cutMap = { "7d": 7, "30d": 30, "90d": 90 };
    const days = cutMap[range];
    if (!days) return data.equity_curve;
    const cutoff = now - days * 86_400_000;
    return data.equity_curve.filter(p => new Date(p.date).getTime() >= cutoff);
  })();

  const equityMin = equity.length ? Math.min(...equity.map(p => p.cumul)) : 0;
  const equityMax = equity.length ? Math.max(...equity.map(p => p.cumul)) : 0;
  const equityColor = (data?.total_pnl ?? 0) >= 0 ? "#00c96a" : "#ff4d6d";

  const botNameMap = Object.fromEntries((data?.per_bot || []).map(b => [b.id, b.name]));

  const filteredTrades = selectedBot
    ? (data?.recent_trades || []).filter(t => t.bot_id === selectedBot)
    : (data?.recent_trades || []);

  // ── Render ───────────────────────────────────────────────────────────────────

  if (plan === "free") {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12 text-center">
        <div className="text-5xl mb-4">📊</div>
        <h1 className="text-2xl font-bold text-white mb-2">Dashboard Bots</h1>
        <p className="text-gray-400 mb-6">Disponible dès le plan Starter.</p>
        <Link to="/pricing" className="btn-primary px-8 py-3">Voir les plans</Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 flex flex-col gap-6">

      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            📊 Dashboard Bots
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            {data?.running_count > 0
              ? <span className="text-green-400 font-medium">{data.running_count} bot(s) en cours</span>
              : "Aucun bot en cours"
            }
            {data?.running_count > 0 && " — actualisation auto 10s"}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="btn-secondary text-xs py-2 px-4">
            Actualiser
          </button>
          <Link to="/bots" className="btn-primary text-xs py-2 px-4">
            Gérer les bots
          </Link>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-700 text-red-400 text-sm rounded-xl px-4 py-3">
          {error}
        </div>
      )}

      {/* KPIs fleet */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="PnL total"
          value={loading ? null : pnlFmt(data?.total_pnl ?? 0, true)}
          colorCls={pnlCls(data?.total_pnl ?? 0)}
          loading={loading}
        />
        <KpiCard
          label="Bots actifs"
          value={loading ? null : `${data?.running_count ?? 0} / ${data?.per_bot?.length ?? 0}`}
          sub="en cours d'exécution"
          loading={loading}
        />
        <KpiCard
          label="Trades clôturés"
          value={loading ? null : (data?.total_trades ?? 0).toString()}
          sub="tous bots confondus"
          loading={loading}
        />
        <KpiCard
          label="Win rate"
          value={loading ? null : (data?.win_rate != null ? `${data.win_rate} %` : "—")}
          colorCls={
            data?.win_rate == null ? "text-gray-400"
              : data.win_rate >= 50 ? "text-green-400" : "text-red-400"
          }
          sub={data?.total_trades ? `sur ${data.total_trades} trades` : "pas encore de trades"}
          loading={loading}
        />
      </div>

      {/* Equity curve */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <h2 className="text-sm font-semibold text-white">Courbe equity cumulée</h2>
          <div className="flex gap-1">
            {[
              { k: "7d",  l: "7j" },
              { k: "30d", l: "30j" },
              { k: "90d", l: "90j" },
              { k: "all", l: "Tout" },
            ].map(({ k, l }) => (
              <button
                key={k}
                onClick={() => setRange(k)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                  range === k
                    ? "bg-gray-700 text-white"
                    : "text-gray-500 hover:text-white hover:bg-gray-800"
                }`}
              >
                {l}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <Skeleton className="h-52 w-full" />
        ) : equity.length === 0 ? (
          <div className="h-52 flex items-center justify-center text-gray-600 text-sm">
            Aucun trade enregistré pour cette période
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={equity} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={equityColor} stopOpacity={0.18} />
                  <stop offset="95%" stopColor={equityColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#6b7280", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fill: "#6b7280", fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => `${v >= 0 ? "+" : ""}${v.toFixed(2)}`}
                domain={[equityMin * 1.05, equityMax * 1.05]}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={0} stroke="#374151" strokeDasharray="4 2" />
              <Area
                type="monotone"
                dataKey="cumul"
                stroke={equityColor}
                strokeWidth={2}
                fill="url(#equityGrad)"
                dot={false}
                activeDot={{ r: 4, fill: equityColor }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Table bots */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Performance par bot</h2>
          {selectedBot && (
            <button
              onClick={() => setSelectedBot(null)}
              className="text-xs text-gray-500 hover:text-white transition-colors"
            >
              Réinitialiser filtre ×
            </button>
          )}
        </div>
        <div className="overflow-x-auto">
          {loading ? (
            <div className="px-5 py-6 flex flex-col gap-3">
              {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
            </div>
          ) : !data?.per_bot?.length ? (
            <div className="px-5 py-8 text-center text-gray-600 text-sm">
              Aucun bot configuré. <Link to="/bots" className="text-brand-400 hover:underline">Créer un bot</Link>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  {["Nom", "Broker · Symbole", "Mode", "PnL", "Trades", "Win rate", "Statut"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.per_bot.map(bot => (
                  <BotRow
                    key={bot.id}
                    bot={bot}
                    selected={selectedBot}
                    onSelect={setSelectedBot}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>
        {data?.per_bot?.length > 0 && (
          <p className="text-xs text-gray-600 px-5 py-3">
            Cliquez sur une ligne pour filtrer le log de trades.
          </p>
        )}
      </div>

      {/* Log trades récents */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-sm font-semibold text-white">
            Trades récents
            {selectedBot && (
              <span className="ml-2 text-xs text-gray-500 font-normal">
                — filtre : {botNameMap[selectedBot] || selectedBot.slice(0, 8)}
              </span>
            )}
          </h2>
          <span className="text-xs text-gray-600">{filteredTrades.length} entrées</span>
        </div>
        <div className="overflow-x-auto">
          {loading ? (
            <div className="px-5 py-6 flex flex-col gap-3">
              {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-6 w-full" />)}
            </div>
          ) : filteredTrades.length === 0 ? (
            <div className="px-5 py-8 text-center text-gray-600 text-sm">
              Aucun trade enregistré.{" "}
              {data?.per_bot?.some(b => b.status === "idle") && (
                <Link to="/bots" className="text-brand-400 hover:underline">Démarrer un bot</Link>
              )}
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800">
                  {["Date", "Bot", "Symbole", "Side", "Qté", "Entrée", "Sortie", "PnL", "Raison"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredTrades.map(t => (
                  <TradeRow
                    key={t.id}
                    trade={t}
                    botName={botNameMap[t.bot_id] || t.bot_id.slice(0, 8)}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Footer note */}
      <p className="text-xs text-gray-700 text-center pb-2">
        Les performances passées ne préjugent pas des performances futures. Mode paper = simulation uniquement.
      </p>
    </div>
  );
}
