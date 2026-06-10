/**
 * Titre Détail — Afrika Markets Intelligence
 * Remplace pages/03_TITRES.py
 * KPIs + historique prix (Recharts) + volume + signaux
 */
import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ResponsiveContainer, ComposedChart, AreaChart, Area,
  BarChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, Legend,
} from "recharts";
import { apiGet } from "../lib/api";
import TradingViewWidget, { BRVM_ON_TV } from "../components/TradingViewWidget";

const TOOLTIP_STYLE = {
  contentStyle: { background: "#111827", border: "1px solid #374151", borderRadius: 8 },
  labelStyle: { color: "#9ca3af", fontSize: 12 },
};

function KpiCard({ label, value, sub, positive }) {
  const color = positive === true ? "text-green-400" : positive === false ? "text-red-400" : "text-white";
  return (
    <div className="card py-3 text-center">
      <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      {sub && <p className={`text-xs mt-0.5 ${positive === true ? "text-green-400" : positive === false ? "text-red-400" : "text-gray-400"}`}>{sub}</p>}
    </div>
  );
}

function SignalBadge({ variation }) {
  if (variation > 3)  return <span className="badge bg-green-900/50 text-green-300 border border-green-700">🚀 Forte hausse</span>;
  if (variation > 0)  return <span className="badge bg-green-950/50 text-green-400 border border-green-900">↑ Légère hausse</span>;
  if (variation === 0) return <span className="badge bg-gray-800 text-gray-300 border border-gray-700">→ Stable</span>;
  if (variation > -3) return <span className="badge bg-red-950/50 text-red-400 border border-red-900">↓ Légère baisse</span>;
  return <span className="badge bg-red-900/50 text-red-300 border border-red-700">📉 Forte baisse</span>;
}

export default function TitreDetail() {
  const { symbole } = useParams();
  const { t } = useTranslation();
  const sym = (symbole || "").toUpperCase();

  const [period,   setPeriod]   = useState(90);
  const [history,  setHistory]  = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(null);
  const [showTV,   setShowTV]   = useState(false);
  const tvCovered = BRVM_ON_TV.has(sym);

  useEffect(() => {
    if (!sym) return;
    setLoading(true);
    apiGet(`/market/actions/${sym}/history?days=${period}`)
      .then(setHistory)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sym, period]);

  if (!sym) {
    return (
      <div className="py-20 text-center text-gray-400">
        <p>Sélectionnez un titre depuis la <Link to="/marche" className="text-brand-400 underline">page Marché</Link></p>
      </div>
    );
  }

  const data = history?.data ?? [];
  const isPositive = data.length > 1 ? data[data.length - 1].cours >= data[0].cours : true;
  const lineColor  = isPositive ? "#22c55e" : "#ef4444";
  const fillColor  = isPositive ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)";

  // Calcul MA10 côté client
  const chartData = data.map((d, i) => {
    const window = data.slice(Math.max(0, i - 9), i + 1);
    const ma10   = window.reduce((s, x) => s + x.cours, 0) / window.length;
    return { ...d, ma10: parseFloat(ma10.toFixed(2)) };
  });

  const last = data[data.length - 1];
  const first = data[0];
  const delta = first && last ? ((last.cours / first.cours - 1) * 100) : 0;
  const high = data.length ? Math.max(...data.map((d) => d.cours)) : 0;
  const low  = data.length ? Math.min(...data.map((d) => d.cours)) : 0;
  const avgVol = data.length ? data.reduce((s, d) => s + (d.volume || 0), 0) / data.length : 0;

  return (
    <div className="py-8 px-4">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Link to="/marche" className="hover:text-white transition-colors">Marché</Link>
          <span>/</span>
          <span className="text-brand-400 font-mono font-bold">{sym}</span>
        </div>

        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white font-mono">{sym}</h1>
            {last && <p className="text-gray-400 text-sm mt-1">{last.cours?.toLocaleString()} FCFA</p>}
          </div>
          {last && <SignalBadge variation={last.variation ?? 0} />}
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-xl">
            {error} — Données insuffisantes ou ticker invalide
          </div>
        )}

        {/* KPIs */}
        {last && (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3">
            <KpiCard label="Clôture"    value={`${last.cours?.toLocaleString()} F`} />
            <KpiCard label="Veille"     value={`${last.cours_veille?.toLocaleString()} F`} />
            <KpiCard label="Ouverture"  value={`${last.cours_ouv?.toLocaleString()} F`} />
            <KpiCard
              label="Variation"
              value={`${last.variation >= 0 ? "+" : ""}${last.variation?.toFixed(2)}%`}
              positive={last.variation > 0 ? true : last.variation < 0 ? false : null}
            />
            <KpiCard label="Volume"     value={last.volume?.toLocaleString()} />
          </div>
        )}

        {/* Sélecteur période */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">{t("period", "Période")} :</span>
          {[30, 90, 180, 365].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                period === p
                  ? "bg-brand-500 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700"
              }`}
            >
              {p}j
            </button>
          ))}
        </div>

        {/* Graphique prix */}
        <div className="card">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <h2 className="text-base font-semibold text-white">{t("price_history", "Historique des prix")}</h2>
            <div className="flex items-center gap-3">
              {data.length > 1 && (
                <span className={`text-sm font-semibold ${delta >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {delta >= 0 ? "+" : ""}{delta.toFixed(2)}% sur {period}j
                </span>
              )}
              {/* Toggle TradingView */}
              <button
                onClick={() => setShowTV((v) => !v)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                  showTV
                    ? "bg-blue-950/60 border-blue-600 text-blue-300"
                    : "bg-gray-800 border-gray-600 text-gray-400 hover:text-white"
                }`}
                title={tvCovered ? "Graphique TradingView avancé" : "Ce titre peut ne pas être couvert par TradingView"}
              >
                <span>📈</span>
                <span>{showTV ? "Vue simple" : "TradingView"}</span>
                {!tvCovered && !showTV && <span className="text-yellow-500 text-xs">⚠️</span>}
              </button>
            </div>
          </div>

          {/* Avertissement couverture TradingView */}
          {showTV && !tvCovered && (
            <div className="mb-3 px-3 py-2 rounded-lg bg-yellow-950/40 border border-yellow-800/40 text-xs text-yellow-400 flex items-center gap-2">
              <span>⚠️</span>
              <span>
                <strong>{sym}</strong> n'est pas dans la liste des titres BRVM vérifiés sur TradingView.
                Le graphique peut être vide — utilisez la vue simple pour les données Afrika Markets.
              </span>
            </div>
          )}

          {showTV ? (
            <TradingViewWidget
              symbol={`BRVM:${sym}`}
              interval="D"
              theme="dark"
              height={480}
              studies={["STD;RSI", "STD;MACD", "STD;Volume"]}
            />
          ) : loading ? (
            <div className="h-64 animate-pulse bg-gray-800 rounded-xl" />
          ) : data.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-gray-500">
              Historique non disponible — données en cours d'accumulation
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: "#6b7280", fontSize: 11 }}
                  tickFormatter={(v) => v?.slice(5)}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fill: "#6b7280", fontSize: 11 }}
                  tickFormatter={(v) => v?.toLocaleString()}
                  width={70}
                />
                <Tooltip
                  {...TOOLTIP_STYLE}
                  formatter={(v, n) => [`${v?.toLocaleString()} F`, n === "cours" ? "Clôture" : "MA 10"]}
                  labelFormatter={(v) => `📅 ${v}`}
                />
                <Area dataKey="cours" name="cours" stroke={lineColor} fill={fillColor} strokeWidth={2} dot={false} />
                <Line dataKey="ma10" name="MA 10" stroke="#f59e0b" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* KPIs période */}
        {data.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <KpiCard label={`Plus haut ${period}j`} value={`${high?.toLocaleString()} F`} />
            <KpiCard label={`Plus bas ${period}j`}  value={`${low?.toLocaleString()} F`} />
            <KpiCard
              label="Perf. période"
              value={`${delta >= 0 ? "+" : ""}${delta.toFixed(2)}%`}
              positive={delta >= 0 ? true : false}
            />
            <KpiCard label="Vol. moyen" value={Math.round(avgVol)?.toLocaleString()} />
          </div>
        )}

        {/* Volume */}
        {data.length > 0 && (
          <div className="card">
            <h2 className="text-base font-semibold text-white mb-4">{t("volume", "Volume")} ({period}j)</h2>
            <ResponsiveContainer width="100%" height={120}>
              <BarChart data={chartData} margin={{ top: 0, right: 10, bottom: 0, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 10 }} tickFormatter={(v) => v?.slice(5)} interval="preserveStartEnd" />
                <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} tickFormatter={(v) => (v / 1000).toFixed(0) + "k"} width={50} />
                <Tooltip
                  {...TOOLTIP_STYLE}
                  formatter={(v) => [v?.toLocaleString(), "Volume"]}
                  labelFormatter={(v) => `📅 ${v}`}
                />
                <Bar dataKey="volume" fill="#006B3F" opacity={0.7} radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Lien analyse technique */}
        <div className="card border-brand-500/20 text-center py-6">
          <p className="text-gray-400 text-sm mb-3">Analyse technique complète (MA · RSI · MFI · Signaux)</p>
          <Link
            to={`/analyse?sym=${sym}`}
            className="btn-primary text-sm"
          >
            📈 Analyser {sym} →
          </Link>
        </div>

      </div>
    </div>
  );
}
