/**
 * Secteurs BRVM — Afrika Markets Intelligence
 * Remplace pages/02_SECTEURS.py
 * Performance YTD + variation jour + composition marché
 */
import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { apiGet } from "../lib/api";

function HBar({ label, value, max, unit = "%" }) {
  const pct = max > 0 ? Math.abs(value) / max * 100 : 0;
  const pos = value >= 0;
  return (
    <div className="flex items-center gap-3 py-1.5">
      <span className="text-xs text-gray-400 w-36 truncate flex-shrink-0">{label}</span>
      <div className="flex-1 relative h-5 flex items-center">
        <div className="absolute inset-y-0 left-0 right-0 bg-gray-800 rounded-full" />
        <div
          className={`absolute h-full rounded-full transition-all ${pos ? "bg-green-500/70" : "bg-red-500/70"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs font-semibold w-14 text-right ${pos ? "text-green-400" : "text-red-400"}`}>
        {pos ? "+" : ""}{value?.toFixed(1)}{unit}
      </span>
    </div>
  );
}

function SectorRow({ s }) {
  const pos = (s.variation_moy ?? 0) >= 0;
  return (
    <tr className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
      <td className="px-4 py-3 text-white font-medium text-sm">{s.secteur}</td>
      <td className="px-4 py-3 text-right text-gray-300">{s.nb_titres}</td>
      <td className="px-4 py-3 text-right text-gray-300">{(s.volume_total / 1e6).toFixed(1)}M</td>
      <td className="px-4 py-3 text-right">
        <span className={`text-sm font-medium ${pos ? "text-green-400" : "text-red-400"}`}>
          {pos ? "+" : ""}{s.variation_moy?.toFixed(2)}%
        </span>
      </td>
      <td className="px-4 py-3 text-right text-gray-400 text-xs">
        <span className="text-green-400">{s.nb_up}↑</span>
        {" / "}
        <span className="text-red-400">{s.nb_down}↓</span>
      </td>
    </tr>
  );
}

export default function Secteurs() {
  const { t } = useTranslation();
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  useEffect(() => {
    apiGet("/market/sectors")
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const indices = data?.sector_indices ?? [];
  const stats   = data?.sector_stats   ?? [];

  const maxYtd  = Math.max(...indices.map((s) => Math.abs(s.var_ytd ?? 0)), 1);
  const maxVar  = Math.max(...indices.map((s) => Math.abs(s.variation ?? 0)), 1);

  const statsSorted = [...stats].sort((a, b) => (b.variation_moy ?? 0) - (a.variation_moy ?? 0));

  return (
    <div className="py-8 px-4">
      <div className="max-w-7xl mx-auto space-y-8">

        <div>
          <h1 className="text-2xl font-bold text-white">{t("sectors_title", "Secteurs BRVM")}</h1>
          {data?.date && <p className="text-sm text-gray-400 mt-1">Données du {data.date}</p>}
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-xl">{error}</div>
        )}

        {loading ? (
          <div className="grid lg:grid-cols-2 gap-6">
            {[0, 1].map((i) => <div key={i} className="card h-64 animate-pulse" />)}
          </div>
        ) : (
          <>
            {/* Indices sectoriels : YTD + Variation jour */}
            {indices.length > 0 && (
              <div className="grid lg:grid-cols-2 gap-6">
                <div className="card">
                  <h2 className="text-base font-semibold text-white mb-4">
                    {t("ytd_performance", "Performance YTD")}
                  </h2>
                  <div className="space-y-0.5">
                    {[...indices].sort((a, b) => (b.var_ytd ?? 0) - (a.var_ytd ?? 0)).map((s) => (
                      <HBar key={s.nom} label={s.nom} value={s.var_ytd ?? 0} max={maxYtd} />
                    ))}
                  </div>
                </div>

                <div className="card">
                  <h2 className="text-base font-semibold text-white mb-4">
                    {t("daily_variation", "Variation du jour")}
                  </h2>
                  <div className="space-y-0.5">
                    {[...indices].sort((a, b) => (b.variation ?? 0) - (a.variation ?? 0)).map((s) => (
                      <HBar key={s.nom} label={s.nom} value={s.variation ?? 0} max={maxVar} />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Composition par secteur */}
            {stats.length > 0 && (
              <section>
                <h2 className="text-base font-semibold text-white mb-4">
                  {t("market_composition", "Composition du marché")}
                </h2>

                {/* Donut-like circles : nb titres par secteur */}
                <div className="grid sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
                  {statsSorted.map((s) => {
                    const pos = (s.variation_moy ?? 0) >= 0;
                    return (
                      <div key={s.secteur} className="card py-4 text-center">
                        <p className="text-2xl font-bold text-white">{s.nb_titres}</p>
                        <p className="text-xs text-gray-400 mt-1 leading-tight">{s.secteur}</p>
                        <p className={`text-xs font-semibold mt-2 ${pos ? "text-green-400" : "text-red-400"}`}>
                          {pos ? "+" : ""}{s.variation_moy?.toFixed(2)}%
                        </p>
                      </div>
                    );
                  })}
                </div>

                {/* Tableau synthèse */}
                <div className="card p-0 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="border-b border-gray-800">
                        <tr className="text-gray-400 text-xs uppercase tracking-wide">
                          <th className="text-left px-4 py-3">{t("sector", "Secteur")}</th>
                          <th className="text-right px-4 py-3">{t("nb_stocks", "Titres")}</th>
                          <th className="text-right px-4 py-3">{t("total_volume", "Volume")}</th>
                          <th className="text-right px-4 py-3">{t("avg_variation", "Var. moy.")}</th>
                          <th className="text-right px-4 py-3">Hausse/Baisse</th>
                        </tr>
                      </thead>
                      <tbody>
                        {statsSorted.map((s) => <SectorRow key={s.secteur} s={s} />)}
                      </tbody>
                    </table>
                  </div>
                </div>
              </section>
            )}

            {indices.length === 0 && stats.length === 0 && (
              <div className="card text-center py-12 text-gray-400">
                Données sectorielles non disponibles
              </div>
            )}
          </>
        )}

        <p className="text-xs text-gray-600 text-center">Source : BRVM.org · {data?.date ?? ""}</p>
      </div>
    </div>
  );
}
