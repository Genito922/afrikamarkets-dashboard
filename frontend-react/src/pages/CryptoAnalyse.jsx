/**
 * Crypto Analyse — Plan Expert
 * Analyse technique approfondie : EMA · MACD · RSI · Bollinger · Volume · ATR
 * Screener multi-actifs · Corrélations · Sentiment marché
 */
import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  ResponsiveContainer,
  ComposedChart,
  AreaChart,
  LineChart,
  BarChart,
  Area,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Cell,
} from "recharts";
import { apiGet } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import ComplianceBanner from "../components/ComplianceBanner";
import TradingViewWidget, { TV_CRYPTO, TV_INTERVAL } from "../components/TradingViewWidget";
import MacroSidebar from "../components/MacroSidebar";

// ── Catalogue actifs ─────────────────────────────────────────
const ASSETS = [
  { ticker: "BTC-USD",  label: "Bitcoin",   icon: "₿",  color: "#F7931A", cap: "Large" },
  { ticker: "ETH-USD",  label: "Ethereum",  icon: "Ξ",  color: "#627EEA", cap: "Large" },
  { ticker: "BNB-USD",  label: "BNB",       icon: "🔶", color: "#F0B90B", cap: "Large" },
  { ticker: "SOL-USD",  label: "Solana",    icon: "◎",  color: "#9945FF", cap: "Large" },
  { ticker: "XRP-USD",  label: "XRP",       icon: "✦",  color: "#00AAE4", cap: "Large" },
  { ticker: "ADA-USD",  label: "Cardano",   icon: "₳",  color: "#0033AD", cap: "Mid"   },
  { ticker: "AVAX-USD", label: "Avalanche", icon: "🔺", color: "#E84142", cap: "Mid"   },
  { ticker: "DOGE-USD", label: "Dogecoin",  icon: "Ð",  color: "#C2A633", cap: "Mid"   },
  { ticker: "LINK-USD", label: "Chainlink", icon: "⬡",  color: "#375BD2", cap: "Mid"   },
  { ticker: "DOT-USD",  label: "Polkadot",  icon: "●",  color: "#E6007A", cap: "Mid"   },
];

const PERIODS = [
  { label: "7j",   days: 7   },
  { label: "30j",  days: 30  },
  { label: "90j",  days: 90  },
  { label: "180j", days: 180 },
  { label: "1an",  days: 365 },
];

const MAIN_TABS = [
  { key: "analyse",      label: "📈 Analyse",   plan: "expert" },
  { key: "screener",     label: "🔍 Screener",  plan: "expert" },
  { key: "correlations", label: "🔗 Corrélations", plan: "expert" },
  { key: "sentiment",    label: "🧠 Sentiment", plan: "expert" },
];

// ── Couleurs ──────────────────────────────────────────────────
const C = {
  grid:   "#1f2937",
  text:   "#6b7280",
  green:  "#22c55e",
  red:    "#ef4444",
  yellow: "#f59e0b",
  blue:   "#3b82f6",
  purple: "#a855f7",
  cyan:   "#06b6d4",
  orange: "#f97316",
  white:  "#f9fafb",
  ema9:   "#fbbf24",
  ema21:  "#f97316",
  ema50:  "#a78bfa",
  ema200: "#34d399",
  bb_up:  "#60a5fa",
  bb_lo:  "#60a5fa",
  macd:   "#818cf8",
  signal: "#f472b6",
  vol:    "#374151",
};

const TT = {
  contentStyle: {
    background: "#0f172a",
    border: "1px solid #374151",
    borderRadius: 8,
    fontSize: 11,
  },
  labelStyle: { color: "#6b7280" },
};

// ── Helpers ───────────────────────────────────────────────────
const fmtDate = (d) => {
  if (!d) return "";
  const p = d.split("-");
  return `${p[2]}/${p[1]}`;
};

const fmtPrice = (v) => {
  if (v == null) return "";
  if (v >= 10000) return v.toLocaleString("fr-FR", { maximumFractionDigits: 0 });
  if (v >= 1)     return v.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
  return v.toLocaleString("fr-FR", { maximumFractionDigits: 5 });
};

const fmtPct = (v) => (v == null ? "" : `${v > 0 ? "+" : ""}${v.toFixed(2)}%`);

// ── Composants utilitaires ────────────────────────────────────
function SignalBadge({ label, color, score }) {
  if (!label) return null;
  const arrow = score > 0 ? "▲" : score < 0 ? "▼" : "–";
  return (
    <span
      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold"
      style={{ background: color + "22", color, border: `1px solid ${color}55` }}
    >
      {arrow} {label}
    </span>
  );
}

function StatBox({ label, value, color, sub }) {
  return (
    <div className="text-center p-3 rounded-xl bg-gray-900/60 border border-gray-800">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-sm font-bold" style={{ color: color || C.white }}>{value}</p>
      {sub && <p className="text-xs text-gray-600 mt-0.5">{sub}</p>}
    </div>
  );
}

function LoadingSkeleton({ rows = 3 }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="card animate-pulse" style={{ height: i === 0 ? 56 : 180 }} />
      ))}
    </div>
  );
}

function ErrorPanel({ message, onRetry }) {
  return (
    <div className="card text-center py-12">
      <p className="text-4xl mb-3">⚠️</p>
      <p className="text-white font-medium mb-1">Données indisponibles</p>
      <p className="text-gray-400 text-sm mb-5">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary text-sm">
          Réessayer
        </button>
      )}
    </div>
  );
}

// ── INDICATEURS CALCULÉS CÔTÉ CLIENT ─────────────────────────
function calcEMA(data, key, period) {
  const k = 2 / (period + 1);
  const result = [];
  let prev = null;
  for (const row of data) {
    const v = row[key];
    if (v == null) { result.push(null); continue; }
    if (prev === null) { prev = v; result.push(v); continue; }
    prev = v * k + prev * (1 - k);
    result.push(prev);
  }
  return result;
}

function calcBollinger(data, key, period = 20, mult = 2) {
  return data.map((_, i) => {
    if (i < period - 1) return { mid: null, upper: null, lower: null };
    const slice = data.slice(i - period + 1, i + 1).map((r) => r[key]);
    const mean  = slice.reduce((a, b) => a + b, 0) / period;
    const std   = Math.sqrt(slice.reduce((s, v) => s + (v - mean) ** 2, 0) / period);
    return { mid: mean, upper: mean + mult * std, lower: mean - mult * std };
  });
}

function calcMACD(data, key, fast = 12, slow = 26, signal = 9) {
  const emaFast   = calcEMA(data, key, fast);
  const emaSlow   = calcEMA(data, key, slow);
  const macdLine  = emaFast.map((f, i) => (f != null && emaSlow[i] != null ? f - emaSlow[i] : null));
  const macdData  = data.map((r, i) => ({ [key]: macdLine[i] }));
  const signalLine = calcEMA(macdData, key, signal);
  const histogram  = macdLine.map((m, i) => (m != null && signalLine[i] != null ? m - signalLine[i] : null));
  return { macdLine, signalLine, histogram };
}

function enrichData(rawData) {
  if (!rawData || rawData.length === 0) return [];
  // EMAs
  const ema9   = calcEMA(rawData, "cours", 9);
  const ema21  = calcEMA(rawData, "cours", 21);
  const ema50  = calcEMA(rawData, "cours", 50);
  const ema200 = calcEMA(rawData, "cours", 200);
  // Bollinger 20
  const bolls  = calcBollinger(rawData, "cours", 20, 2);
  // MACD
  const { macdLine, signalLine, histogram } = calcMACD(rawData, "cours");

  return rawData.map((row, i) => ({
    ...row,
    ema9:      ema9[i],
    ema21:     ema21[i],
    ema50:     ema50[i],
    ema200:    ema200[i],
    bb_upper:  bolls[i].upper,
    bb_mid:    bolls[i].mid,
    bb_lower:  bolls[i].lower,
    macd:      macdLine[i],
    macd_signal: signalLine[i],
    macd_hist: histogram[i],
  }));
}

// ── ONGLET ANALYSE ────────────────────────────────────────────
function AnalyseTab({ ticker, days }) {
  const [result,  setResult]  = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const [showBB,  setShowBB]  = useState(true);
  const [showEMA, setShowEMA] = useState(true);
  const [showTV,  setShowTV]  = useState(false);

  const asset = ASSETS.find((a) => a.ticker === ticker);

  const fetchData = useCallback(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);
    setResult(null);
    apiGet(`/intel/international/${encodeURIComponent(ticker)}?days=${days}`)
      .then((r) => {
        const enriched = enrichData(r.data || []);
        setResult({ ...r, data: enriched });
      })
      .catch((e) => setError(e?.message || "Erreur de chargement"))
      .finally(() => setLoading(false));
  }, [ticker, days]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <LoadingSkeleton rows={5} />;
  if (error)   return <ErrorPanel message={error} onRetry={fetchData} />;
  if (!result) return null;

  const { data, last } = result;
  const last24h = data.length >= 2
    ? ((data.at(-1).cours - data.at(-2).cours) / data.at(-2).cours) * 100
    : null;

  // ATR (14)
  const atrValues = data.slice(1).map((r, i) => {
    const prev = data[i];
    if (!prev) return null;
    return Math.max(
      r.cours - (r.low ?? r.cours),
      Math.abs(r.cours - prev.cours),
      Math.abs((r.low ?? r.cours) - prev.cours)
    );
  });
  const atr14 = atrValues.slice(-14).filter(Boolean);
  const atrAvg = atr14.length ? atr14.reduce((a, b) => a + b, 0) / atr14.length : null;

  // Signal composite
  const lastRow  = data.at(-1);
  const rsiVal   = lastRow?.rsi;
  const mfiVal   = lastRow?.mfi;
  const macdHist = lastRow?.macd_hist;
  const ema9v    = lastRow?.ema9;
  const ema50v   = lastRow?.ema50;
  const ema200v  = lastRow?.ema200;
  const price    = lastRow?.cours;

  let score = last?.score ?? 0;
  if (macdHist != null) score += macdHist > 0 ? 1 : -1;
  if (ema9v != null && ema50v != null) score += ema9v > ema50v ? 1 : -1;
  if (ema50v != null && ema200v != null) score += ema50v > ema200v ? 1 : -1;

  const signalLabel =
    score >= 4  ? "Achat Fort"     :
    score >= 2  ? "Achat Modéré"   :
    score <= -4 ? "Vente Forte"    :
    score <= -2 ? "Vente Modérée"  : "Neutre";
  const signalColor =
    score >= 2  ? C.green :
    score <= -2 ? C.red   : "#94a3b8";

  return (
    <div className="space-y-4">
      {/* ── Signal header ───────────────────────── */}
      <div
        className="rounded-2xl p-4 border"
        style={{
          background: `linear-gradient(135deg, ${asset?.color}11, ${asset?.color}06)`,
          borderColor: asset?.color + "33",
        }}
      >
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-3">
            <span className="text-4xl">{asset?.icon}</span>
            <div>
              <p className="text-lg font-bold text-white">{asset?.label}</p>
              <p className="text-xs text-gray-400">{ticker}</p>
            </div>
          </div>
          <div>
            <p className="text-2xl font-bold text-white">{fmtPrice(price)} $</p>
            {last24h != null && (
              <p className={`text-sm font-medium ${last24h >= 0 ? "text-green-400" : "text-red-400"}`}>
                {fmtPct(last24h)} (24h)
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2 ml-auto">
            <SignalBadge label={signalLabel} color={signalColor} score={score} />
            <span className="text-xs px-2.5 py-1 rounded-full bg-gray-800 text-gray-300">
              Score: {score > 0 ? "+" : ""}{score}
            </span>
          </div>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
          <StatBox
            label="RSI (14)"
            value={rsiVal != null ? rsiVal.toFixed(1) : "—"}
            color={rsiVal > 70 ? C.red : rsiVal < 30 ? C.green : C.yellow}
            sub={rsiVal > 70 ? "Suracheté" : rsiVal < 30 ? "Survendu" : "Neutre"}
          />
          <StatBox
            label="MFI (14)"
            value={mfiVal != null ? mfiVal.toFixed(1) : "—"}
            color={mfiVal > 80 ? C.red : mfiVal < 20 ? C.green : C.yellow}
            sub={mfiVal > 80 ? "Sortie flux" : mfiVal < 20 ? "Entrée flux" : "Équilibré"}
          />
          <StatBox
            label="MACD Hist."
            value={macdHist != null ? (macdHist > 0 ? "+" : "") + macdHist.toFixed(4) : "—"}
            color={macdHist > 0 ? C.green : macdHist < 0 ? C.red : C.text}
            sub={macdHist > 0 ? "Momentum haussier" : "Momentum baissier"}
          />
          <StatBox
            label="ATR (14)"
            value={atrAvg != null ? fmtPrice(atrAvg) + " $" : "—"}
            color={C.orange}
            sub="Volatilité moyenne"
          />
        </div>

        {/* EMA structure */}
        {ema200v != null && (
          <div className="mt-3 flex flex-wrap gap-2">
            {[
              { label: "EMA 9",   val: ema9v,   col: C.ema9   },
              { label: "EMA 21",  val: ema21,   col: C.ema21  },
              { label: "EMA 50",  val: ema50v,  col: C.ema50  },
              { label: "EMA 200", val: ema200v, col: C.ema200 },
            ]
              .filter((e) => e.val != null)
              .map(({ label, val, col }) => (
                <span
                  key={label}
                  className="text-xs px-2.5 py-1 rounded-full font-mono"
                  style={{ background: col + "18", color: col, border: `1px solid ${col}44` }}
                >
                  {label}: {fmtPrice(val)}
                </span>
              ))}
          </div>
        )}
      </div>

      {/* ── Toggles ─────────────────────────────── */}
      <div className="flex gap-2 flex-wrap items-center">
        <button
          onClick={() => setShowTV((v) => !v)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border flex items-center gap-1.5 ${
            showTV
              ? "border-blue-500 bg-blue-950/60 text-blue-300"
              : "border-gray-600 bg-gray-800 text-gray-300 hover:text-white"
          }`}
        >
          <span>📈</span>
          <span>{showTV ? "Vue Recharts" : "Vue TradingView"}</span>
        </button>
        {!showTV && (
          <>
            <button
              onClick={() => setShowEMA(!showEMA)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
                showEMA ? "border-yellow-600 bg-yellow-950/40 text-yellow-300" : "border-gray-700 bg-gray-900 text-gray-400"
              }`}
            >
              EMA 9/21/50/200
            </button>
            <button
              onClick={() => setShowBB(!showBB)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
                showBB ? "border-blue-600 bg-blue-950/40 text-blue-300" : "border-gray-700 bg-gray-900 text-gray-400"
              }`}
            >
              Bandes de Bollinger (20)
            </button>
          </>
        )}
      </div>

      {/* ── Prix + EMAs + Bollinger / TradingView ─── */}
      <div className="card">
        {showTV ? (
          <TradingViewWidget
            symbol={TV_CRYPTO[ticker] || "BINANCE:BTCUSDT"}
            interval={TV_INTERVAL[days] || "D"}
            theme="dark"
            height={540}
            studies={["STD;RSI", "STD;MACD", "STD;Bollinger_Bands"]}
          />
        ) : (
        <>
        <p className="text-xs text-gray-400 mb-3 font-medium">
          Prix · {showEMA ? "EMA 9/21/50/200 · " : ""}{showBB ? "Bollinger (20, 2σ)" : ""}
        </p>
        <ResponsiveContainer width="100%" height={240}>
          <ComposedChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={C.grid} />
            <XAxis
              dataKey="date"
              tickFormatter={fmtDate}
              tick={{ fill: C.text, fontSize: 10 }}
              minTickGap={40}
            />
            <YAxis
              tick={{ fill: C.text, fontSize: 10 }}
              tickFormatter={fmtPrice}
              width={65}
              domain={["auto", "auto"]}
            />
            <Tooltip
              {...TT}
              formatter={(v, name) => [fmtPrice(v), name]}
              labelFormatter={fmtDate}
            />
            {/* Bollinger fill */}
            {showBB && (
              <Area
                dataKey="bb_upper"
                fill="transparent"
                stroke={C.bb_up}
                strokeWidth={0.8}
                strokeDasharray="3 2"
                dot={false}
                name="BB Haut"
                connectNulls
              />
            )}
            {showBB && (
              <Area
                dataKey="bb_lower"
                fill="#3b82f618"
                stroke={C.bb_lo}
                strokeWidth={0.8}
                strokeDasharray="3 2"
                dot={false}
                name="BB Bas"
                connectNulls
              />
            )}
            {showBB && (
              <Line
                dataKey="bb_mid"
                stroke={C.bb_up}
                strokeWidth={0.8}
                strokeDasharray="4 3"
                dot={false}
                name="BB Mid"
                connectNulls
              />
            )}
            {/* Price area */}
            <Area
              dataKey="cours"
              fill={`${asset?.color}18`}
              stroke={asset?.color || C.blue}
              strokeWidth={2}
              dot={false}
              name="Prix"
            />
            {/* EMAs */}
            {showEMA && (
              <Line dataKey="ema9"   stroke={C.ema9}   strokeWidth={1.2} dot={false} name="EMA 9"   connectNulls />
            )}
            {showEMA && (
              <Line dataKey="ema21"  stroke={C.ema21}  strokeWidth={1.2} dot={false} name="EMA 21"  connectNulls />
            )}
            {showEMA && (
              <Line dataKey="ema50"  stroke={C.ema50}  strokeWidth={1.5} dot={false} name="EMA 50"  connectNulls strokeDasharray="4 2" />
            )}
            {showEMA && (
              <Line dataKey="ema200" stroke={C.ema200} strokeWidth={1.5} dot={false} name="EMA 200" connectNulls strokeDasharray="4 2" />
            )}
          </ComposedChart>
        </ResponsiveContainer>
        </>
        )}
      </div>

      {/* ── Volume ──────────────────────────────── */}
      {data[0]?.volume != null && (
        <div className="card">
          <p className="text-xs text-gray-400 mb-3 font-medium">Volume</p>
          <ResponsiveContainer width="100%" height={90}>
            <BarChart data={data} margin={{ top: 0, right: 4, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={C.grid} />
              <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fill: C.text, fontSize: 10 }} minTickGap={40} />
              <YAxis tick={{ fill: C.text, fontSize: 10 }} width={50}
                tickFormatter={(v) => v >= 1e9 ? `${(v/1e9).toFixed(1)}B` : v >= 1e6 ? `${(v/1e6).toFixed(0)}M` : v}
              />
              <Tooltip {...TT} labelFormatter={fmtDate}
                formatter={(v) => [v >= 1e6 ? `${(v/1e6).toFixed(2)}M` : v, "Volume"]}
              />
              <Bar dataKey="volume" fill={C.vol} name="Volume" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── MACD ────────────────────────────────── */}
      <div className="card">
        <p className="text-xs text-gray-400 mb-3 font-medium">MACD (12, 26, 9)</p>
        <ResponsiveContainer width="100%" height={130}>
          <ComposedChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={C.grid} />
            <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fill: C.text, fontSize: 10 }} minTickGap={40} />
            <YAxis tick={{ fill: C.text, fontSize: 10 }} width={50}
              tickFormatter={(v) => (v >= 0 ? "+" : "") + v.toFixed(3)}
            />
            <Tooltip
              {...TT}
              labelFormatter={fmtDate}
              formatter={(v, name) => [v != null ? ((v > 0 ? "+" : "") + v.toFixed(4)) : "—", name]}
            />
            <ReferenceLine y={0} stroke="#4b5563" />
            {/* Histogram bars */}
            <Bar dataKey="macd_hist" name="Histogramme">
              {data.map((entry, i) => (
                <Cell
                  key={i}
                  fill={entry.macd_hist >= 0 ? "#22c55e88" : "#ef444488"}
                />
              ))}
            </Bar>
            <Line dataKey="macd"        stroke={C.macd}   strokeWidth={1.5} dot={false} name="MACD"   connectNulls />
            <Line dataKey="macd_signal" stroke={C.signal} strokeWidth={1.2} dot={false} name="Signal" connectNulls strokeDasharray="3 2" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* ── RSI ─────────────────────────────────── */}
      <div className="card">
        <p className="text-xs text-gray-400 mb-3 font-medium">RSI (14)</p>
        <ResponsiveContainer width="100%" height={110}>
          <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={C.grid} />
            <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fill: C.text, fontSize: 10 }} minTickGap={40} />
            <YAxis domain={[0, 100]} tick={{ fill: C.text, fontSize: 10 }} width={30} />
            <Tooltip
              {...TT}
              labelFormatter={fmtDate}
              formatter={(v) => [v != null ? v.toFixed(1) : "—", "RSI"]}
            />
            <ReferenceLine y={70} stroke={C.red}   strokeDasharray="3 3" label={{ value: "70", fill: C.red,   fontSize: 9, position: "insideTopRight" }} />
            <ReferenceLine y={30} stroke={C.green} strokeDasharray="3 3" label={{ value: "30", fill: C.green, fontSize: 9, position: "insideBottomRight" }} />
            <ReferenceLine y={50} stroke="#374151" strokeDasharray="2 4" />
            <Line dataKey="rsi" stroke={C.purple} strokeWidth={1.5} dot={false} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* ── MFI ─────────────────────────────────── */}
      <div className="card">
        <p className="text-xs text-gray-400 mb-3 font-medium">MFI — Money Flow Index (14)</p>
        <ResponsiveContainer width="100%" height={100}>
          <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={C.grid} />
            <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fill: C.text, fontSize: 10 }} minTickGap={40} />
            <YAxis domain={[0, 100]} tick={{ fill: C.text, fontSize: 10 }} width={30} />
            <Tooltip
              {...TT}
              labelFormatter={fmtDate}
              formatter={(v) => [v != null ? v.toFixed(1) : "—", "MFI"]}
            />
            <ReferenceLine y={80} stroke={C.red}   strokeDasharray="3 3" />
            <ReferenceLine y={20} stroke={C.green} strokeDasharray="3 3" />
            <Area dataKey="mfi" fill={C.cyan + "20"} stroke={C.cyan} strokeWidth={1.5} dot={false} connectNulls />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ── ONGLET SCREENER ───────────────────────────────────────────
function ScreenerTab({ days }) {
  const [results, setResults]   = useState([]);
  const [loading, setLoading]   = useState(false);
  const [loaded,  setLoaded]    = useState(false);
  const [sortKey, setSortKey]   = useState("score");
  const [sortDir, setSortDir]   = useState(-1);

  const run = useCallback(() => {
    setLoading(true);
    setLoaded(false);

    const promises = ASSETS.map((a) =>
      apiGet(`/intel/international/${encodeURIComponent(a.ticker)}?days=${days}`)
        .then((r) => ({
          ...a,
          cours:   r.last?.cours,
          score:   r.last?.score ?? 0,
          label:   r.last?.label ?? "—",
          color:   r.last?.color ?? "#94a3b8",
          rsi:     r.last?.rsi,
          mfi:     r.last?.mfi,
          reasons: r.last?.reasons ?? [],
          chg1d:   r.data?.length >= 2
            ? ((r.data.at(-1).cours - r.data.at(-2).cours) / r.data.at(-2).cours) * 100
            : null,
          chg7d:   r.data?.length >= 7
            ? ((r.data.at(-1).cours - r.data.at(-7).cours) / r.data.at(-7).cours) * 100
            : null,
        }))
        .catch(() => ({ ...a, cours: null, score: 0, label: "N/D", color: "#6b7280" }))
    );

    Promise.allSettled(promises).then((res) => {
      const data = res.map((r) => (r.status === "fulfilled" ? r.value : null)).filter(Boolean);
      setResults(data);
      setLoading(false);
      setLoaded(true);
    });
  }, [days]);

  useEffect(() => { run(); }, [run]);

  const sorted = [...results].sort((a, b) => {
    const va = a[sortKey] ?? (sortDir === 1 ? Infinity : -Infinity);
    const vb = b[sortKey] ?? (sortDir === 1 ? Infinity : -Infinity);
    return (va - vb) * sortDir;
  });

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir((d) => -d);
    else { setSortKey(key); setSortDir(-1); }
  };

  const Th = ({ k, label }) => (
    <th
      className="px-3 py-2 text-xs text-gray-400 text-right cursor-pointer hover:text-white select-none"
      onClick={() => toggleSort(k)}
    >
      {label} {sortKey === k ? (sortDir === -1 ? "↓" : "↑") : ""}
    </th>
  );

  return (
    <div className="space-y-4">
      <div className="card bg-gradient-to-r from-violet-950/60 to-purple-950/60 border border-violet-900/30">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h2 className="text-base font-bold text-white">🔍 Screener Crypto — {ASSETS.length} actifs</h2>
            <p className="text-xs text-gray-400">
              Signaux combinés : MA · RSI · MFI · MACD calculé · Score composite
            </p>
          </div>
          <button onClick={run} className="btn-secondary text-xs py-1.5 px-3">
            {loading ? "Chargement…" : "Actualiser"}
          </button>
        </div>
      </div>

      {loading && !loaded ? (
        <div className="space-y-2">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="card h-10 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-800">
              <tr>
                <th className="px-3 py-2 text-xs text-gray-400 text-left">Actif</th>
                <Th k="cours"  label="Prix $"  />
                <Th k="chg1d"  label="1J"      />
                <Th k="chg7d"  label="7J"      />
                <Th k="rsi"    label="RSI"     />
                <Th k="mfi"    label="MFI"     />
                <Th k="score"  label="Score"   />
                <th className="px-3 py-2 text-xs text-gray-400 text-center">Signal</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr
                  key={row.ticker}
                  className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors"
                >
                  <td className="px-3 py-2.5">
                    <div className="flex items-center gap-2">
                      <span style={{ color: row.color }} className="text-lg">{row.icon}</span>
                      <div>
                        <p className="text-white font-medium text-xs">{row.label}</p>
                        <p className="text-gray-500 text-xs">{row.ticker}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono text-white text-xs">
                    {row.cours != null ? fmtPrice(row.cours) : "—"}
                  </td>
                  <td className={`px-3 py-2.5 text-right text-xs font-medium ${row.chg1d >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {row.chg1d != null ? fmtPct(row.chg1d) : "—"}
                  </td>
                  <td className={`px-3 py-2.5 text-right text-xs font-medium ${row.chg7d >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {row.chg7d != null ? fmtPct(row.chg7d) : "—"}
                  </td>
                  <td className="px-3 py-2.5 text-right text-xs">
                    <span
                      className="font-bold"
                      style={{
                        color: row.rsi > 70 ? C.red : row.rsi < 30 ? C.green : C.yellow,
                      }}
                    >
                      {row.rsi != null ? row.rsi.toFixed(1) : "—"}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-right text-xs">
                    <span
                      className="font-bold"
                      style={{
                        color: row.mfi > 80 ? C.red : row.mfi < 20 ? C.green : C.yellow,
                      }}
                    >
                      {row.mfi != null ? row.mfi.toFixed(1) : "—"}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-right text-xs">
                    <span
                      className="font-bold"
                      style={{ color: row.score >= 2 ? C.green : row.score <= -2 ? C.red : C.text }}
                    >
                      {row.score > 0 ? "+" : ""}{row.score}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    <SignalBadge label={row.label} color={row.color} score={row.score} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-gray-600 text-center">
        Cliquer sur les colonnes pour trier · Score max ±5 · RSI/MFI sur 14 périodes
      </p>
    </div>
  );
}

// ── ONGLET CORRÉLATIONS ───────────────────────────────────────
function CorrelationsTab({ days }) {
  const [matrix,  setMatrix]  = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setMatrix(null);

    const subset = ASSETS.slice(0, 7); // 7 actifs pour lisibilité
    Promise.allSettled(
      subset.map((a) =>
        apiGet(`/intel/international/${encodeURIComponent(a.ticker)}?days=${days}`)
          .then((r) => ({ ticker: a.label, returns: computeReturns(r.data || []) }))
          .catch(() => null)
      )
    ).then((res) => {
      const valid = res.map((r) => r.value).filter(Boolean);
      if (valid.length < 2) { setLoading(false); return; }
      const corr = computeCorrelationMatrix(valid);
      setMatrix({ labels: valid.map((v) => v.ticker), data: corr });
      setLoading(false);
    });
  }, [days]);

  function computeReturns(data) {
    return data.slice(1).map((r, i) => {
      const prev = data[i];
      if (!prev || !r.cours || !prev.cours) return 0;
      return (r.cours - prev.cours) / prev.cours;
    });
  }

  function pearson(a, b) {
    const n = Math.min(a.length, b.length);
    if (n < 2) return 0;
    const ax = a.slice(0, n);
    const bx = b.slice(0, n);
    const ma = ax.reduce((s, v) => s + v, 0) / n;
    const mb = bx.reduce((s, v) => s + v, 0) / n;
    const num = ax.reduce((s, v, i) => s + (v - ma) * (bx[i] - mb), 0);
    const da  = Math.sqrt(ax.reduce((s, v) => s + (v - ma) ** 2, 0));
    const db  = Math.sqrt(bx.reduce((s, v) => s + (v - mb) ** 2, 0));
    return da * db === 0 ? 0 : num / (da * db);
  }

  function computeCorrelationMatrix(assets) {
    return assets.map((a) =>
      assets.map((b) => pearson(a.returns, b.returns))
    );
  }

  const corrColor = (v) => {
    const abs = Math.abs(v);
    if (v >= 0.7)  return { bg: "#22c55e33", text: "#22c55e" };
    if (v >= 0.4)  return { bg: "#86efac22", text: "#86efac" };
    if (v >= 0.0)  return { bg: "#f59e0b11", text: "#f59e0b" };
    if (v >= -0.4) return { bg: "#f9731622", text: "#f97316" };
    return { bg: "#ef444433", text: "#ef4444" };
  };

  return (
    <div className="space-y-4">
      <div className="card bg-gradient-to-r from-cyan-950/60 to-teal-950/60 border border-cyan-900/30">
        <h2 className="text-base font-bold text-white mb-1">🔗 Matrice de Corrélation</h2>
        <p className="text-xs text-gray-400">
          Corrélation de Pearson sur {days} jours · Rendements journaliers · 7 actifs principaux
        </p>
      </div>

      {loading && <div className="card animate-pulse h-72" />}

      {matrix && (
        <div className="card overflow-x-auto">
          <table className="text-xs">
            <thead>
              <tr>
                <th className="px-2 py-1.5 text-gray-500 text-left w-20">—</th>
                {matrix.labels.map((l) => (
                  <th key={l} className="px-2 py-1.5 text-gray-400 text-center min-w-[70px]">
                    {l.split(" ")[0]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.data.map((row, i) => (
                <tr key={i} className="border-t border-gray-800/40">
                  <td className="px-2 py-2 text-gray-300 font-medium whitespace-nowrap">
                    {matrix.labels[i].split(" ")[0]}
                  </td>
                  {row.map((val, j) => {
                    const { bg, text } = corrColor(val);
                    return (
                      <td
                        key={j}
                        className="px-2 py-2 text-center font-bold rounded"
                        style={{ background: i === j ? "#374151" : bg, color: i === j ? "#f9fafb" : text }}
                      >
                        {i === j ? "1.00" : val.toFixed(2)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex gap-4 mt-4 flex-wrap text-xs text-gray-500">
            <span><span className="text-green-400 font-bold">≥ 0.7</span> Forte corrélation positive</span>
            <span><span className="text-orange-400 font-bold">0–0.4</span> Faible corrélation</span>
            <span><span className="text-red-400 font-bold">≤ -0.4</span> Corrélation négative</span>
          </div>
        </div>
      )}
      <p className="text-xs text-gray-600 text-center">
        Une corrélation proche de 1 = actifs qui évoluent ensemble · Utile pour la diversification de portefeuille
      </p>
    </div>
  );
}

// ── ONGLET SENTIMENT ──────────────────────────────────────────
function SentimentTab({ days }) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    // Tenter l'endpoint dédié, sinon construire depuis BTC
    apiGet("/intel/crypto/sentiment")
      .then(setData)
      .catch(() => {
        // Fallback : calcul depuis BTC
        apiGet(`/intel/international/BTC-USD?days=30`)
          .then((r) => {
            const prices = (r.data || []).map((d) => d.cours).filter(Boolean);
            const last   = prices.at(-1);
            const prev30 = prices[0];
            const chg30  = prev30 ? ((last - prev30) / prev30) * 100 : 0;
            const rsi    = r.last?.rsi ?? 50;
            // Score Fear & Greed estimé via RSI + momentum
            const fgRaw  = Math.round((rsi * 0.5 + Math.min(Math.max(chg30 + 50, 0), 100) * 0.5));
            const fg     = Math.min(Math.max(fgRaw, 0), 100);
            setData({
              fear_greed: {
                value: fg,
                label: fg >= 75 ? "Avidité Extrême" : fg >= 55 ? "Avidité" : fg >= 45 ? "Neutre" : fg >= 25 ? "Peur" : "Peur Extrême",
                color: fg >= 75 ? C.green : fg >= 45 ? C.yellow : C.red,
              },
              btc_dominance: null,
              btc_rsi: rsi,
              btc_chg30: chg30,
              source: "estimé (BTC RSI + momentum 30j)",
            });
          })
          .catch(() => {})
          .finally(() => setLoading(false));
        return;
      });
    setLoading(false);
  }, [days]);

  const fg = data?.fear_greed;
  const gaugeAngle = fg ? (fg.value / 100) * 180 - 90 : -90;

  return (
    <div className="space-y-4">
      <div className="card bg-gradient-to-r from-pink-950/60 to-rose-950/60 border border-pink-900/30">
        <h2 className="text-base font-bold text-white mb-1">🧠 Sentiment de Marché</h2>
        <p className="text-xs text-gray-400">
          Fear & Greed Index · Dominance BTC · Contexte macro crypto
        </p>
      </div>

      {loading && <LoadingSkeleton rows={2} />}

      {fg && (
        <div className="grid sm:grid-cols-2 gap-4">
          {/* Fear & Greed gauge */}
          <div className="card text-center">
            <p className="text-xs text-gray-400 mb-4">Fear & Greed Index</p>
            <div className="relative inline-flex flex-col items-center">
              {/* Semi-circle */}
              <svg width="180" height="100" viewBox="0 0 180 100">
                <path d="M 10 90 A 80 80 0 0 1 170 90" fill="none" stroke="#1f2937" strokeWidth="16" strokeLinecap="round" />
                <path
                  d={`M 10 90 A 80 80 0 0 1 170 90`}
                  fill="none"
                  stroke="url(#fearGreedGrad)"
                  strokeWidth="16"
                  strokeLinecap="round"
                  strokeDasharray={`${(fg.value / 100) * 251.3} 251.3`}
                />
                <defs>
                  <linearGradient id="fearGreedGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%"   stopColor="#ef4444" />
                    <stop offset="50%"  stopColor="#f59e0b" />
                    <stop offset="100%" stopColor="#22c55e" />
                  </linearGradient>
                </defs>
                {/* Needle */}
                <line
                  x1="90"
                  y1="90"
                  x2={90 + 65 * Math.cos((gaugeAngle * Math.PI) / 180)}
                  y2={90 - 65 * Math.sin(((gaugeAngle + 180) * Math.PI) / 180 - Math.PI)}
                  stroke="white"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
                <circle cx="90" cy="90" r="4" fill="white" />
              </svg>
              <p className="text-3xl font-bold mt-1" style={{ color: fg.color }}>{fg.value}</p>
              <p className="text-sm font-medium mt-0.5" style={{ color: fg.color }}>{fg.label}</p>
              {data.source && (
                <p className="text-xs text-gray-600 mt-1">{data.source}</p>
              )}
            </div>
            <div className="flex justify-between text-xs text-gray-600 mt-3 px-2">
              <span className="text-red-500">0 Peur extrême</span>
              <span className="text-green-500">100 Avidité extrême</span>
            </div>
          </div>

          {/* Contexte */}
          <div className="space-y-3">
            {data.btc_rsi != null && (
              <div className="card">
                <p className="text-xs text-gray-400 mb-1">BTC — RSI (14)</p>
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-gray-800 rounded-full h-2">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${data.btc_rsi}%`,
                        background: data.btc_rsi > 70 ? C.red : data.btc_rsi < 30 ? C.green : C.yellow,
                      }}
                    />
                  </div>
                  <span
                    className="text-sm font-bold w-12 text-right"
                    style={{ color: data.btc_rsi > 70 ? C.red : data.btc_rsi < 30 ? C.green : C.yellow }}
                  >
                    {data.btc_rsi.toFixed(1)}
                  </span>
                </div>
              </div>
            )}

            {data.btc_dominance != null && (
              <div className="card">
                <p className="text-xs text-gray-400 mb-1">Dominance BTC</p>
                <p className="text-xl font-bold text-orange-400">{data.btc_dominance.toFixed(1)}%</p>
                <p className="text-xs text-gray-500">
                  {data.btc_dominance > 55 ? "BTC dominant — altcoins sous pression" :
                   data.btc_dominance > 45 ? "Marché équilibré BTC/altcoins" :
                   "Altcoin season possible"}
                </p>
              </div>
            )}

            {data.btc_chg30 != null && (
              <div className="card">
                <p className="text-xs text-gray-400 mb-1">BTC — Performance 30j</p>
                <p
                  className="text-xl font-bold"
                  style={{ color: data.btc_chg30 >= 0 ? C.green : C.red }}
                >
                  {fmtPct(data.btc_chg30)}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Grille de lecture */}
      <div className="card">
        <h3 className="text-sm font-bold text-white mb-3">Grille d'interprétation</h3>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center text-xs">
          {[
            { range: "0–24",  label: "Peur extrême",   color: "#ef4444", tip: "Potentiel d'achat" },
            { range: "25–44", label: "Peur",           color: "#f97316", tip: "Précaution" },
            { range: "45–54", label: "Neutre",         color: "#94a3b8", tip: "Attente" },
            { range: "55–74", label: "Avidité",        color: "#84cc16", tip: "Prudence" },
            { range: "75–100",label: "Avidité extrême",color: "#22c55e", tip: "Potentiel top" },
          ].map(({ range, label, color, tip }) => (
            <div key={range} className="p-2 rounded-lg bg-gray-900/60">
              <p className="font-bold mb-0.5" style={{ color }}>{range}</p>
              <p className="text-gray-300">{label}</p>
              <p className="text-gray-500 text-xs mt-0.5">{tip}</p>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xs text-gray-600 text-center">
        Fear & Greed estimé via RSI BTC + momentum · Pour données temps réel : alternative.me/crypto/fear-and-greed-index
      </p>
    </div>
  );
}

// ── PAGE PRINCIPALE ───────────────────────────────────────────
export default function CryptoAnalyse() {
  const { plan } = useAuth();

  const [activeTab,    setActiveTab]    = useState("analyse");
  const [ticker,       setTicker]       = useState("BTC-USD");
  const [days,         setDays]         = useState(90);

  const hasAccess = plan === "expert";

  // ── Plan gate ────────────────────────────────────────────────
  if (!hasAccess) {
    return (
      <div className="py-20 px-4 text-center">
        <p className="text-5xl mb-4">₿</p>
        <h2 className="text-2xl font-bold text-white mb-2">Analyse Crypto Avancée — Plan Expert</h2>
        <p className="text-gray-400 mb-2">
          EMA · MACD · Bollinger · RSI · MFI · ATR · Screener · Corrélations · Sentiment
        </p>
        <p className="text-gray-500 text-sm mb-6">
          10 actifs crypto · Analyse technique professionnelle · Multi-timeframe
        </p>
        <Link to="/pricing" className="btn-primary">Voir les offres →</Link>
      </div>
    );
  }

  const activeAsset = ASSETS.find((a) => a.ticker === ticker);

  return (
    <div className="py-8 px-4">
      <div className="max-w-7xl mx-auto space-y-5">

        {/* ── Header ──────────────────────────────────────────── */}
        <div
          className="rounded-2xl px-6 py-5 border"
          style={{
            background: "linear-gradient(135deg, #0f0a1f, #1a0d36 50%, #0d1a2e 100%)",
            borderColor: "#3b1d6e55",
          }}
        >
          <div className="flex flex-wrap items-center gap-3">
            <div>
              <h1 className="text-2xl font-bold text-white">₿ Analyse Crypto Pro</h1>
              <p className="text-gray-300 text-sm mt-1">
                EMA · MACD · Bollinger · RSI · MFI · ATR · Screener · Corrélations · Sentiment
              </p>
            </div>
            <span className="ml-auto px-3 py-1 rounded-full text-xs font-bold bg-purple-900/60 text-purple-300 border border-purple-800/40">
              Expert
            </span>
          </div>
        </div>

        {/* ── Main tabs ───────────────────────────────────────── */}
        <div className="flex gap-1 border-b border-gray-800 overflow-x-auto pb-px">
          {MAIN_TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors -mb-px border-b-2 whitespace-nowrap ${
                activeTab === key
                  ? "border-purple-500 text-purple-400 bg-purple-500/5"
                  : "border-transparent text-gray-400 hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* ── Sélecteur actif + période (Analyse uniquement) ─── */}
        {(activeTab === "analyse") && (
          <>
            {/* Asset chips */}
            <div className="flex flex-wrap gap-2">
              {ASSETS.map((a) => (
                <button
                  key={a.ticker}
                  onClick={() => setTicker(a.ticker)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${
                    ticker === a.ticker
                      ? "text-white"
                      : "bg-gray-900 border-gray-700 text-gray-300 hover:border-gray-500"
                  }`}
                  style={
                    ticker === a.ticker
                      ? { background: a.color + "33", borderColor: a.color + "88", color: a.color }
                      : {}
                  }
                >
                  <span>{a.icon}</span>
                  <span>{a.label}</span>
                  <span className="text-xs opacity-50">{a.cap}</span>
                </button>
              ))}
            </div>

            {/* Period selector */}
            <div className="flex gap-1">
              {PERIODS.map(({ label, days: d }) => (
                <button
                  key={d}
                  onClick={() => setDays(d)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    days === d
                      ? "bg-gray-700 text-white"
                      : "text-gray-400 hover:text-white hover:bg-gray-800"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </>
        )}

        {/* Période pour screener/correlations */}
        {(activeTab === "screener" || activeTab === "correlations") && (
          <div className="flex gap-1">
            {PERIODS.map(({ label, days: d }) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  days === d
                    ? "bg-gray-700 text-white"
                    : "text-gray-400 hover:text-white hover:bg-gray-800"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        )}

        {/* ── Contenu des onglets ──────────────────────────────── */}

        {/* Analyse : layout Terminal Bloomberg 3/4 + sidebar 1/4 */}
        {activeTab === "analyse" && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
            <div className="lg:col-span-3">
              <AnalyseTab ticker={ticker} days={days} />
            </div>
            <div className="lg:col-span-1">
              <MacroSidebar
                context="crypto"
                currentSymbol={TV_CRYPTO[ticker]}
              />
            </div>
          </div>
        )}

        {activeTab === "screener"     && <ScreenerTab     days={days} />}
        {activeTab === "correlations" && <CorrelationsTab days={days} />}
        {activeTab === "sentiment"    && <SentimentTab    days={days} />}

        <p className="text-xs text-gray-600 text-center">
          Source : Yahoo Finance (yfinance) · Données différées 15–20 min ·
          Indicateurs calculés en local (EMA, MACD, Bollinger) · Pas un conseil en investissement
        </p>
        <ComplianceBanner variant="compact" />
      </div>
    </div>
  );
}
