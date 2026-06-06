/**
 * War Room — Risques géopolitiques UEMOA
 * Remplace pages/05_RISQUES.py
 * ACLED security + IMF macro + carte risques statique
 */
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from "recharts";
import { apiGet } from "../lib/api";
import { useAuth } from "../context/AuthContext";

const TOOLTIP_STYLE = {
  contentStyle: { background: "#0f172a", border: "1px solid #374151", borderRadius: 8, fontSize: 12 },
  labelStyle: { color: "#6b7280" },
};

function RiskBadge({ score }) {
  if (score <= 3) return <span className="badge bg-green-900/40 text-green-300 border border-green-800">Stable</span>;
  if (score <= 5) return <span className="badge bg-yellow-900/40 text-yellow-300 border border-yellow-800">Fragile</span>;
  if (score <= 7) return <span className="badge bg-orange-900/40 text-orange-300 border border-orange-800">Instable</span>;
  return <span className="badge bg-red-900/40 text-red-300 border border-red-800">Critique</span>;
}

function ImpactBadge({ impact }) {
  if (impact === "fort")   return <span className="text-xs font-medium text-red-400">Impact fort</span>;
  if (impact === "moyen")  return <span className="text-xs font-medium text-yellow-400">Impact moyen</span>;
  return <span className="text-xs font-medium text-gray-400">Impact faible</span>;
}

function CountryCard({ c, expanded, onToggle }) {
  return (
    <div
      className="card cursor-pointer hover:border-gray-600 transition-all"
      style={{ borderLeftColor: c.risk_color, borderLeftWidth: 4 }}
      onClick={onToggle}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{c.flag}</span>
          <div>
            <h3 className="font-semibold text-white">{c.nom}</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <RiskBadge score={c.risque} />
              <ImpactBadge impact={c.impact_brvm} />
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1 justify-end">
            {[...Array(10)].map((_, i) => (
              <div
                key={i}
                className={`w-2 h-4 rounded-sm ${i < c.risque ? "" : "opacity-20"}`}
                style={{ background: i < c.risque ? c.risk_color : "#374151" }}
              />
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-1">{c.risque}/10</p>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-gray-800 grid sm:grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-400 mb-1">Situation</p>
            <p className="text-gray-300">{c.situation}</p>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-400 text-xs">Événements 90j (ACLED)</span>
              <span className="text-white font-medium">{c.events_90d}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400 text-xs">Croissance PIB (IMF)</span>
              <span className={`font-medium text-xs ${c.gdp_growth >= 4 ? "text-green-400" : "text-yellow-400"}`}>
                +{c.gdp_growth}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400 text-xs">Inflation</span>
              <span className={`font-medium text-xs ${c.inflation <= 4 ? "text-green-400" : "text-yellow-400"}`}>
                {c.inflation}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400 text-xs">Impact BRVM</span>
              <ImpactBadge impact={c.impact_brvm} />
            </div>
          </div>
          {c.market_impact && (
            <div className="sm:col-span-2">
              <p className="text-xs text-gray-400 mb-1">Exposition marché</p>
              <p className="text-gray-300 text-xs">{c.market_impact}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Risques() {
  const { t } = useTranslation();
  const { plan } = useAuth();
  const [data,     setData]     = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [activeTab, setActiveTab] = useState("map");

  const hasAccess = ["pro", "expert"].includes(plan);

  useEffect(() => {
    if (!hasAccess) return;
    apiGet("/intel/warroom")
      .then(setData)
      .finally(() => setLoading(false));
  }, [hasAccess]);

  if (!hasAccess) {
    return (
      <div className="py-20 px-4 text-center">
        <p className="text-4xl mb-4">🔒</p>
        <h2 className="text-2xl font-bold text-white mb-2">War Room Géopolitique — Plan Pro+</h2>
        <p className="text-gray-400 mb-6">ACLED live · IMF Macro · Carte risques UEMOA</p>
        <Link to="/pricing" className="btn-primary">Voir les offres →</Link>
      </div>
    );
  }

  const countries = data?.data ?? [];
  const stables   = countries.filter((c) => c.risque <= 3).length;
  const fragiles  = countries.filter((c) => c.risque > 3 && c.risque <= 6).length;
  const critiques = countries.filter((c) => c.risque > 6).length;
  const avgEvents = countries.length
    ? Math.round(countries.reduce((s, c) => s + c.events_90d, 0) / countries.length)
    : 0;

  const TABS = [
    { key: "map",   label: "🗺 Carte risques" },
    { key: "macro", label: "📈 Macro IMF" },
    { key: "acled", label: "🔒 Sécurité ACLED" },
  ];

  return (
    <div className="py-8 px-4">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <div className="bg-gradient-to-r from-red-950 to-orange-950 border border-red-900/30 rounded-2xl px-6 py-5">
          <h1 className="text-2xl font-bold text-white">⚠️ War Room — Risques Géopolitiques UEMOA</h1>
          <p className="text-gray-300 text-sm mt-1">
            Données ACLED (sécurité 90j) + IMF (macro 2025) · {data?.updated_at ?? ""}
          </p>
        </div>

        {/* KPIs */}
        {!loading && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="card text-center py-3">
              <p className="text-2xl font-bold text-green-400">{stables}</p>
              <p className="text-xs text-gray-400 mt-1">Pays stables (≤3)</p>
            </div>
            <div className="card text-center py-3">
              <p className="text-2xl font-bold text-yellow-400">{fragiles}</p>
              <p className="text-xs text-gray-400 mt-1">Pays fragiles (4-6)</p>
            </div>
            <div className="card text-center py-3">
              <p className="text-2xl font-bold text-red-400">{critiques}</p>
              <p className="text-xs text-gray-400 mt-1">Pays critiques (&gt;6)</p>
            </div>
            <div className="card text-center py-3">
              <p className="text-2xl font-bold text-white">{avgEvents}</p>
              <p className="text-xs text-gray-400 mt-1">Événements moy. 90j</p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 border-b border-gray-800">
          {TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-5 py-2.5 text-sm font-medium rounded-t-lg transition-colors -mb-px border-b-2 ${
                activeTab === key
                  ? "border-brand-500 text-brand-400 bg-brand-500/5"
                  : "border-transparent text-gray-400 hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="grid sm:grid-cols-2 gap-4">
            {[...Array(4)].map((_, i) => <div key={i} className="card h-24 animate-pulse" />)}
          </div>
        ) : (
          <>
            {/* ── TAB : Carte risques ── */}
            {activeTab === "map" && (
              <div className="grid sm:grid-cols-2 gap-4">
                {[...countries].sort((a, b) => b.risque - a.risque).map((c) => (
                  <CountryCard
                    key={c.iso2}
                    c={c}
                    expanded={expanded === c.iso2}
                    onToggle={() => setExpanded(expanded === c.iso2 ? null : c.iso2)}
                  />
                ))}
              </div>
            )}

            {/* ── TAB : Macro IMF ── */}
            {activeTab === "macro" && (
              <div className="space-y-6">
                <div className="card">
                  <h2 className="text-sm font-semibold text-white mb-4">Croissance PIB 2025 (%)</h2>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart
                      data={[...countries].sort((a, b) => b.gdp_growth - a.gdp_growth)
                        .map((c) => ({ name: c.flag + " " + c.nom.split(" ")[0], gdp: c.gdp_growth, risque: c.risque }))}
                      margin={{ top: 5, right: 10, bottom: 20, left: 10 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis dataKey="name" tick={{ fill: "#6b7280", fontSize: 10 }} />
                      <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} tickFormatter={(v) => v + "%"} />
                      <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v + "%", "Croissance PIB"]} />
                      <Bar dataKey="gdp" radius={[3, 3, 0, 0]}>
                        {countries.map((c) => (
                          <Cell key={c.iso2} fill={c.gdp_growth >= 5 ? "#22c55e" : c.gdp_growth >= 3 ? "#f59e0b" : "#ef4444"} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div className="card">
                  <h2 className="text-sm font-semibold text-white mb-4">Inflation 2025 (%)</h2>
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart
                      data={[...countries].sort((a, b) => b.inflation - a.inflation)
                        .map((c) => ({ name: c.flag + " " + c.nom.split(" ")[0], infl: c.inflation }))}
                      margin={{ top: 5, right: 10, bottom: 20, left: 10 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis dataKey="name" tick={{ fill: "#6b7280", fontSize: 10 }} />
                      <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} tickFormatter={(v) => v + "%"} />
                      <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v + "%", "Inflation"]} />
                      <Bar dataKey="infl" radius={[3, 3, 0, 0]}>
                        {countries.map((c) => (
                          <Cell key={c.iso2} fill={c.inflation <= 3 ? "#22c55e" : c.inflation <= 5 ? "#f59e0b" : "#ef4444"} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* ── TAB : Sécurité ACLED ── */}
            {activeTab === "acled" && (
              <div className="space-y-6">
                <div className="card">
                  <h2 className="text-sm font-semibold text-white mb-4">Événements sécuritaires (90 derniers jours) — Source ACLED</h2>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart
                      data={[...countries].sort((a, b) => b.events_90d - a.events_90d)
                        .map((c) => ({ name: c.flag + " " + c.nom.split(" ")[0], events: c.events_90d, risque: c.risque }))}
                      margin={{ top: 5, right: 10, bottom: 20, left: 10 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis dataKey="name" tick={{ fill: "#6b7280", fontSize: 10 }} />
                      <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} />
                      <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v, "Événements ACLED"]} />
                      <Bar dataKey="events" radius={[3, 3, 0, 0]}>
                        {countries.map((c) => (
                          <Cell key={c.iso2} fill={c.risk_color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div className="card">
                  <h2 className="text-sm font-semibold text-white mb-4">Score de risque global (0-10)</h2>
                  <div className="space-y-3">
                    {[...countries].sort((a, b) => b.risque - a.risque).map((c) => (
                      <div key={c.iso2} className="flex items-center gap-3">
                        <span className="text-xl w-8">{c.flag}</span>
                        <span className="text-sm text-gray-300 w-28 truncate">{c.nom}</span>
                        <div className="flex-1 bg-gray-800 rounded-full h-3 overflow-hidden">
                          <div
                            className="h-3 rounded-full transition-all"
                            style={{ width: `${c.risque * 10}%`, background: c.risk_color }}
                          />
                        </div>
                        <span className="text-xs font-bold w-8 text-right" style={{ color: c.risk_color }}>
                          {c.risque}/10
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        <p className="text-xs text-gray-600 text-center">
          Sources : ACLED (Armed Conflict Location & Event Data) · IMF World Economic Outlook 2025
        </p>
      </div>
    </div>
  );
}
