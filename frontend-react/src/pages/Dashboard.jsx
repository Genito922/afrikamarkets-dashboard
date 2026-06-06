/**
 * Dashboard — Afrika Markets Intelligence
 * Remplace HOME.py : KPIs marché, indices BRVM, perf sectorielle, Top5/Flop5
 */
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { apiGet } from "../lib/api";

// ── Composants locaux ─────────────────────────────────────────

function KpiCard({ label, value, loading }) {
  return (
    <div className="card">
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      {loading
        ? <div className="h-6 w-3/4 bg-gray-800 rounded animate-pulse" />
        : <p className="text-lg font-bold text-white truncate">{value ?? "—"}</p>
      }
    </div>
  );
}

function IndexBadge({ idx }) {
  const pos = idx.variation >= 0;
  return (
    <div className="card flex flex-col items-center text-center py-4">
      <p className="text-xs text-gray-400 mb-1 truncate w-full">{idx.nom.replace("BRVM-", "")}</p>
      <p className="text-xl font-bold text-white">{idx.cloture?.toFixed(2)}</p>
      <span className={`text-sm font-semibold mt-1 ${pos ? "text-green-400" : "text-red-400"}`}>
        {pos ? "+" : ""}{idx.variation?.toFixed(2)}%
      </span>
      {idx.var_ytd != null && (
        <span className="text-xs text-gray-500 mt-0.5">YTD {idx.var_ytd >= 0 ? "+" : ""}{idx.var_ytd?.toFixed(1)}%</span>
      )}
    </div>
  );
}

function SectorBar({ nom, varYtd, max }) {
  const pct = max > 0 ? Math.abs(varYtd) / max * 100 : 0;
  const pos = varYtd >= 0;
  const shortName = nom.replace(/BRVM\s[-–]\s?/, "");
  return (
    <div className="flex items-center gap-3 py-1">
      <span className="text-xs text-gray-400 w-32 truncate flex-shrink-0">{shortName}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-2 overflow-hidden">
        <div
          className={`h-2 rounded-full ${pos ? "bg-green-500" : "bg-red-500"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs font-medium w-14 text-right ${pos ? "text-green-400" : "text-red-400"}`}>
        {pos ? "+" : ""}{varYtd?.toFixed(1)}%
      </span>
    </div>
  );
}

function StockCard({ stock, positive }) {
  return (
    <div className={`flex items-center justify-between px-4 py-3 rounded-xl border ${
      positive
        ? "bg-green-950/30 border-green-900/40"
        : "bg-red-950/30 border-red-900/40"
    }`}>
      <div>
        <span className="font-mono font-bold text-sm text-white">{stock.symbole}</span>
        <span className="text-gray-400 text-xs ml-2 hidden sm:inline">{stock.nom?.substring(0, 28)}</span>
      </div>
      <div className="text-right">
        <p className="text-white text-sm font-semibold">{stock.cours?.toLocaleString()} FCFA</p>
        <p className={`text-xs font-medium ${positive ? "text-green-400" : "text-red-400"}`}>
          {positive ? "+" : ""}{stock.variation?.toFixed(2)}%
        </p>
      </div>
    </div>
  );
}

// ── Page principale ───────────────────────────────────────────

export default function Dashboard() {
  const { t } = useTranslation();

  const [summary,  setSummary]  = useState(null);
  const [indices,  setIndices]  = useState(null);
  const [actions,  setActions]  = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const [sum, idx, act] = await Promise.all([
          apiGet("/market/summary"),
          apiGet("/market/indices"),
          apiGet("/market/actions"),
        ]);
        setSummary(sum);
        setIndices(idx);
        setActions(act.data || []);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const marche    = indices?.marche    ?? [];
  const sectoriel = indices?.sectoriel ?? [];
  const summData  = summary?.data      ?? {};

  const maxAbsYtd = sectoriel.length
    ? Math.max(...sectoriel.map((s) => Math.abs(s.var_ytd ?? 0)))
    : 1;

  const sorted = [...actions].sort((a, b) => b.variation - a.variation);
  const top5   = sorted.slice(0, 5);
  const flop5  = [...actions].sort((a, b) => a.variation - b.variation).slice(0, 5);

  return (
    <div className="py-8 px-4">
      <div className="max-w-7xl mx-auto space-y-8">

        {/* Header */}
        <div className="bg-gradient-to-r from-green-950 to-yellow-950 border border-green-900/40 rounded-2xl px-6 py-5">
          <h1 className="text-2xl font-bold text-white">
            🌍 Afrika Markets Intelligence
          </h1>
          <p className="text-gray-300 mt-1 text-sm">
            {t("home_subtitle", "Tableau de bord des marchés africains — BRVM · UEMOA")}
          </p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-xl">
            {error} — <button onClick={() => window.location.reload()} className="underline">Réessayer</button>
          </div>
        )}

        {/* KPIs capitalisation */}
        <div className="grid sm:grid-cols-3 gap-4">
          <KpiCard label={t("home_cap_actions", "Capitalisation actions")}    value={summData["Capitalisation Actions"]}         loading={loading} />
          <KpiCard label={t("home_cap_oblig",   "Capitalisation obligations")} value={summData["Capitalisation des obligations"]} loading={loading} />
          <KpiCard label={t("home_transactions","Valeur des transactions")}    value={summData["Valeur des transactions"]}        loading={loading} />
        </div>

        {/* Indices marché */}
        {!loading && marche.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-white mb-3">{t("home_indices", "Indices BRVM")}</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {marche.map((idx) => <IndexBadge key={idx.nom} idx={idx} />)}
            </div>
          </section>
        )}
        {loading && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="card h-24 animate-pulse bg-gray-900" />
            ))}
          </div>
        )}

        {/* Performance sectorielle */}
        {!loading && sectoriel.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-white mb-3">
              {t("home_sector_perf", "Performance sectorielle YTD")}
            </h2>
            <div className="card space-y-2">
              {[...sectoriel]
                .sort((a, b) => (b.var_ytd ?? 0) - (a.var_ytd ?? 0))
                .map((s) => (
                  <SectorBar key={s.nom} nom={s.nom} varYtd={s.var_ytd ?? 0} max={maxAbsYtd} />
                ))
              }
            </div>
          </section>
        )}

        {/* Top 5 / Flop 5 */}
        {!loading && actions.length > 0 && (
          <div className="grid lg:grid-cols-2 gap-6">
            <section>
              <h2 className="text-lg font-semibold text-white mb-3">
                🚀 {t("home_top5", "Top 5 — Hausses du jour")}
              </h2>
              <div className="space-y-2">
                {top5.map((s) => <StockCard key={s.symbole} stock={s} positive={true} />)}
              </div>
            </section>
            <section>
              <h2 className="text-lg font-semibold text-white mb-3">
                📉 {t("home_flop5", "Flop 5 — Baisses du jour")}
              </h2>
              <div className="space-y-2">
                {flop5.map((s) => <StockCard key={s.symbole} stock={s} positive={false} />)}
              </div>
            </section>
          </div>
        )}

        {/* Accès rapide */}
        <section>
          <h2 className="text-lg font-semibold text-white mb-3">{t("quick_access", "Accès rapide")}</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { to: "/marche",   icon: "📊", label: t("nav_marche",   "Tous les titres"),       sub: "Cours & volumes" },
              { to: "/secteurs", icon: "🏭", label: t("nav_secteurs", "Secteurs"),              sub: "Performance sectorielle" },
              { to: "/analyse",  icon: "📈", label: t("nav_analyse",  "Analyse technique"),     sub: "MA · RSI · MFI" },
              { to: "/sgi",      icon: "🏦", label: t("sgi_module1",  "SGI & OPCVM"),           sub: "Classement & recommandations" },
            ].map(({ to, icon, label, sub }) => (
              <Link key={to} to={to} className="card hover:-translate-y-1 transition-transform">
                <div className="text-3xl mb-2">{icon}</div>
                <h3 className="font-semibold text-white text-sm">{label}</h3>
                <p className="text-xs text-gray-400 mt-1">{sub}</p>
              </Link>
            ))}
          </div>
        </section>

        <p className="text-xs text-gray-600 text-center">
          {t("source_caption", "Source : BRVM.org")} · {summary?.date ?? ""}
        </p>
      </div>
    </div>
  );
}
