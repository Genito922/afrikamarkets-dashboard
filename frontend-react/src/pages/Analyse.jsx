/**
 * Analyse Graphique — Afrika Markets Intelligence
 * Remplace pages/06_ANALYSE_GRAPHIQUE.py
 * MA 16/19/246/361 · RSI · MFI · Croisements · Signal global
 */
import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ResponsiveContainer, ComposedChart, AreaChart, Area, BarChart, Bar,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, Legend,
} from "recharts";
import { apiGet } from "../lib/api";
import { useAuth } from "../context/AuthContext";

const COLORS = {
  price: "#e8e8e8", ma16: "#00BFFF", ma19: "#22c55e",
  ma246: "#FFD700", ma361: "#FF6B35", rsi: "#00BFFF",
  mfi: "#a855f7", volume: "#006B3F",
};

const TOOLTIP_STYLE = {
  contentStyle: { background: "#0f172a", border: "1px solid #374151", borderRadius: 8, fontSize: 12 },
  labelStyle: { color: "#6b7280" },
};

function SignalCard({ signal }) {
  if (!signal) return null;
  const colors = { "#00CC66": "border-green-600 bg-green-950/30", "#FFD700": "border-yellow-600 bg-yellow-950/30",
                   "#888888": "border-gray-600 bg-gray-900",      "#FF6B35": "border-orange-600 bg-orange-950/30",
                   "#FF4444": "border-red-600 bg-red-950/30" };
  const cls = colors[signal.color] || "border-gray-700 bg-gray-900";
  return (
    <div className={`card border ${cls} flex flex-col gap-2`}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400 uppercase tracking-wider">Signal global</span>
        <span className="text-xs text-gray-500">Score : {signal.score > 0 ? "+" : ""}{signal.score}</span>
      </div>
      <p className="text-xl font-bold" style={{ color: signal.color }}>{signal.label}</p>
      <div className="space-y-0.5">
        {(signal.reasons || []).map((r) => (
          <p key={r} className="text-xs text-gray-400">• {r}</p>
        ))}
      </div>
    </div>
  );
}

function CrossingTable({ crossings, dates }) {
  if (!crossings) return null;
  const rows = [];
  const pairs = [
    { key: "ma16_ma19",   label: "MA16 × MA19",   color_g: "#00BFFF", color_d: "#FF6B35" },
    { key: "ma19_ma246",  label: "MA19 × MA246",  color_g: "#22c55e", color_d: "#ef4444" },
    { key: "ma19_ma361",  label: "MA19 × MA361",  color_g: "#22c55e", color_d: "#ef4444" },
    { key: "ma246_ma361", label: "MA246 × MA361", color_g: "#22c55e", color_d: "#ef4444" },
  ];
  pairs.forEach(({ key, label, color_g, color_d }) => {
    const cross = crossings[key] || {};
    (cross.golden || []).forEach((d) => rows.push({ date: d, pair: label, type: "Golden Cross", color: color_g }));
    (cross.death  || []).forEach((d) => rows.push({ date: d, pair: label, type: "Death Cross",  color: color_d }));
  });
  rows.sort((a, b) => b.date.localeCompare(a.date));
  if (rows.length === 0) return <p className="text-gray-500 text-sm">Aucun croisement détecté sur la période</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b border-gray-800">
          <tr className="text-gray-400 text-xs uppercase">
            <th className="text-left px-3 py-2">Date</th>
            <th className="text-left px-3 py-2">Paire</th>
            <th className="text-left px-3 py-2">Type</th>
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 20).map((r, i) => (
            <tr key={i} className="border-b border-gray-800/50">
              <td className="px-3 py-2 text-gray-300 font-mono text-xs">{r.date}</td>
              <td className="px-3 py-2 text-gray-300">{r.pair}</td>
              <td className="px-3 py-2 font-semibold text-xs" style={{ color: r.color }}>{r.type}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Analyse() {
  const { t } = useTranslation();
  const { plan } = useAuth();
  const [searchParams] = useSearchParams();

  const [symbols,  setSymbols]  = useState([]);
  const [sym,      setSym]      = useState(searchParams.get("sym") || "");
  const [days,     setDays]     = useState(180);
  const [analysis, setAnalysis] = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState(null);

  // Charger la liste des symboles disponibles
  useEffect(() => {
    apiGet("/market/actions").then((d) => {
      const syms = (d.data || []).map((a) => ({ value: a.symbole, label: `${a.symbole} — ${a.nom?.substring(0, 35)}` }));
      setSymbols(syms);
      if (!sym && syms.length > 0) setSym(syms[0].value);
    }).catch(() => {});
  }, []);

  // Charger l'analyse quand sym ou days change
  useEffect(() => {
    if (!sym) return;
    setLoading(true);
    setError(null);
    apiGet(`/analysis/${sym}?days=${days}`)
      .then(setAnalysis)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sym, days]);

  // Gate plan starter
  const hasAccess = ["starter", "pro", "expert"].includes(plan);

  if (!hasAccess) {
    return (
      <div className="py-20 px-4 text-center">
        <p className="text-4xl mb-4">🔒</p>
        <h2 className="text-2xl font-bold text-white mb-2">Analyse technique — Plan Starter+</h2>
        <p className="text-gray-400 mb-6">MA 16/19/246/361 · RSI · MFI · Golden/Death Cross</p>
        <a href="/pricing" className="btn-primary">Voir les offres →</a>
      </div>
    );
  }

  const data      = analysis?.data     ?? [];
  const last      = analysis?.last     ?? {};
  const crossings = analysis?.crossings ?? {};

  // Recharts ne comprend pas les null — on garder tels quels, Recharts gère connectNulls
  const chartData = data.map((d) => ({
    date:   d.date?.slice(5),   // MM-DD
    cours:  d.cours,
    ma16:   d.ma16,
    ma19:   d.ma19,
    ma246:  d.ma246,
    ma361:  d.ma361,
    rsi:    d.rsi,
    mfi:    d.mfi,
    volume: d.volume,
  }));

  return (
    <div className="py-8 px-4">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <div className="bg-gradient-to-r from-blue-950 to-green-950 border border-blue-900/30 rounded-2xl px-6 py-5">
          <h1 className="text-2xl font-bold text-white">📐 Analyse Graphique Technique</h1>
          <p className="text-gray-300 text-sm mt-1">MA 16 · MA 19 · MA 246 · MA 361 · RSI · MFI · Croisements</p>
        </div>

        {/* Contrôles */}
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs text-gray-400 mb-1">📌 Titre</label>
            <select
              value={sym}
              onChange={(e) => setSym(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm
                         focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {symbols.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">📅 Période</label>
            <div className="flex gap-1">
              {[90, 180, 365].map((d) => (
                <button
                  key={d}
                  onClick={() => setDays(d)}
                  className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                    days === d ? "bg-brand-500 text-white" : "bg-gray-800 text-gray-400 hover:text-white"
                  }`}
                >
                  {d}j
                </button>
              ))}
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-xl">
            {error}
          </div>
        )}

        {/* Signal + KPIs */}
        {!loading && last.cours && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <SignalCard signal={last} />

            <div className="card">
              <p className="text-xs text-gray-400 mb-2">Moyennes mobiles</p>
              {[
                { label: "MA 16",  val: last.ma16,  color: COLORS.ma16  },
                { label: "MA 19",  val: last.ma19,  color: COLORS.ma19  },
                { label: "MA 246", val: last.ma246, color: COLORS.ma246 },
                { label: "MA 361", val: last.ma361, color: COLORS.ma361 },
              ].map(({ label, val, color }) => (
                <div key={label} className="flex justify-between items-center py-0.5">
                  <span className="text-xs font-mono" style={{ color }}>{label}</span>
                  <span className="text-xs text-white font-medium">{val ? val.toLocaleString() + " F" : "—"}</span>
                </div>
              ))}
            </div>

            <div className="card">
              <p className="text-xs text-gray-400 mb-3">RSI ({14})</p>
              <p className="text-3xl font-bold" style={{ color: COLORS.rsi }}>{last.rsi?.toFixed(1) ?? "—"}</p>
              <p className="text-xs text-gray-500 mt-2">
                {last.rsi > 70 ? "🔴 Suracheté (>70)" : last.rsi < 30 ? "🟢 Survendu (<30)" : "Zone neutre"}
              </p>
            </div>

            <div className="card">
              <p className="text-xs text-gray-400 mb-3">MFI ({14})</p>
              <p className="text-3xl font-bold" style={{ color: COLORS.mfi }}>{last.mfi?.toFixed(1) ?? "—"}</p>
              <p className="text-xs text-gray-500 mt-2">
                {last.mfi > 80 ? "🔴 Suracheté (>80)" : last.mfi < 20 ? "🟢 Survendu (<20)" : "Zone neutre"}
              </p>
            </div>
          </div>
        )}

        {/* Graphique prix + MAs */}
        <div className="card">
          <h2 className="text-sm font-semibold text-white mb-4">Prix & Moyennes Mobiles — {sym}</h2>
          {loading ? (
            <div className="h-64 animate-pulse bg-gray-800 rounded-xl" />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 10 }} interval="preserveStartEnd" />
                <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} tickFormatter={(v) => v?.toLocaleString()} width={72} />
                <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v?.toLocaleString() + " F"]} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area dataKey="cours" name="Prix" stroke={COLORS.price} fill="rgba(232,232,232,0.04)" strokeWidth={1.8} dot={false} connectNulls />
                <Line dataKey="ma16"  name="MA 16"  stroke={COLORS.ma16}  strokeWidth={1.2} dot={false} strokeDasharray="4 2" connectNulls />
                <Line dataKey="ma19"  name="MA 19"  stroke={COLORS.ma19}  strokeWidth={1.5} dot={false} connectNulls />
                <Line dataKey="ma246" name="MA 246" stroke={COLORS.ma246} strokeWidth={1.5} dot={false} strokeDasharray="6 3" connectNulls />
                <Line dataKey="ma361" name="MA 361" stroke={COLORS.ma361} strokeWidth={1.5} dot={false} strokeDasharray="3 3" connectNulls />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Volume */}
        <div className="card">
          <h2 className="text-sm font-semibold text-white mb-4">Volume</h2>
          <ResponsiveContainer width="100%" height={100}>
            <BarChart data={chartData} margin={{ top: 0, right: 10, bottom: 0, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 9 }} interval="preserveStartEnd" />
              <YAxis tick={{ fill: "#6b7280", fontSize: 9 }} tickFormatter={(v) => (v / 1000).toFixed(0) + "k"} width={45} />
              <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v?.toLocaleString(), "Volume"]} />
              <Bar dataKey="volume" fill={COLORS.volume} opacity={0.7} radius={[1, 1, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* RSI */}
        <div className="card">
          <h2 className="text-sm font-semibold text-white mb-4" style={{ color: COLORS.rsi }}>RSI — 14 périodes</h2>
          <ResponsiveContainer width="100%" height={140}>
            <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 9 }} interval="preserveStartEnd" />
              <YAxis domain={[0, 100]} ticks={[0, 30, 50, 70, 100]} tick={{ fill: "#6b7280", fontSize: 9 }} width={30} />
              <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v?.toFixed(1), "RSI"]} />
              <ReferenceLine y={70} stroke="#ef444450" strokeDasharray="4 2" />
              <ReferenceLine y={30} stroke="#22c55e50" strokeDasharray="4 2" />
              <ReferenceLine y={50} stroke="#55555550" strokeDasharray="2 4" />
              <Line dataKey="rsi" name="RSI" stroke={COLORS.rsi} strokeWidth={1.8} dot={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* MFI */}
        <div className="card">
          <h2 className="text-sm font-semibold text-white mb-4" style={{ color: COLORS.mfi }}>MFI — 14 périodes</h2>
          <ResponsiveContainer width="100%" height={140}>
            <AreaChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 9 }} interval="preserveStartEnd" />
              <YAxis domain={[0, 100]} ticks={[0, 20, 50, 80, 100]} tick={{ fill: "#6b7280", fontSize: 9 }} width={30} />
              <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v?.toFixed(1), "MFI"]} />
              <ReferenceLine y={80} stroke="#ef444450" strokeDasharray="4 2" />
              <ReferenceLine y={20} stroke="#22c55e50" strokeDasharray="4 2" />
              <Area dataKey="mfi" name="MFI" stroke={COLORS.mfi} fill="rgba(168,85,247,0.07)" strokeWidth={1.8} dot={false} connectNulls />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Tableau croisements */}
        {!loading && (
          <div className="card">
            <h2 className="text-base font-semibold text-white mb-4">Historique des croisements</h2>
            <CrossingTable crossings={crossings} />
          </div>
        )}

      </div>
    </div>
  );
}
