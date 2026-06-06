/**
 * Marché BRVM — Afrika Markets Intelligence
 * Remplace pages/01_MARCHE.py
 * Table complète des actions + filtres secteur/tri + KPIs
 */
import { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { apiGet } from "../lib/api";

const SORT_FIELDS = [
  { value: "variation", label: "Variation" },
  { value: "cours",     label: "Cours" },
  { value: "volume",    label: "Volume" },
  { value: "symbole",   label: "Symbole" },
];

function VariationBadge({ val }) {
  if (val > 0) return <span className="text-green-400 font-medium">+{val.toFixed(2)}%</span>;
  if (val < 0) return <span className="text-red-400 font-medium">{val.toFixed(2)}%</span>;
  return <span className="text-gray-400">0.00%</span>;
}

export default function Marche() {
  const { t } = useTranslation();

  const [actions,  setActions]  = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(null);
  const [date,     setDate]     = useState(null);

  const [search,   setSearch]   = useState("");
  const [secteur,  setSecteur]  = useState("all");
  const [sortBy,   setSortBy]   = useState("variation");
  const [sortAsc,  setSortAsc]  = useState(false);

  useEffect(() => {
    apiGet("/market/actions")
      .then((data) => {
        setActions(data.data || []);
        setDate(data.date);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const secteurs = useMemo(() => {
    const uniq = [...new Set(actions.map((a) => a.secteur).filter(Boolean))].sort();
    return ["all", ...uniq];
  }, [actions]);

  const filtered = useMemo(() => {
    let rows = actions;
    if (secteur !== "all") rows = rows.filter((a) => a.secteur === secteur);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter(
        (a) => a.symbole?.toLowerCase().includes(q) || a.nom?.toLowerCase().includes(q)
      );
    }
    rows = [...rows].sort((a, b) => {
      const va = a[sortBy] ?? 0;
      const vb = b[sortBy] ?? 0;
      if (typeof va === "string") return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
      return sortAsc ? va - vb : vb - va;
    });
    return rows;
  }, [actions, secteur, search, sortBy, sortAsc]);

  const up   = filtered.filter((a) => a.variation > 0).length;
  const down = filtered.filter((a) => a.variation < 0).length;
  const flat = filtered.filter((a) => a.variation === 0).length;

  function toggleSort(field) {
    if (sortBy === field) setSortAsc(!sortAsc);
    else { setSortBy(field); setSortAsc(false); }
  }

  function SortIcon({ field }) {
    if (sortBy !== field) return <span className="text-gray-600 ml-1">↕</span>;
    return <span className="text-brand-400 ml-1">{sortAsc ? "↑" : "↓"}</span>;
  }

  return (
    <div className="py-8 px-4">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white">{t("market_title", "Marché BRVM — Tous les titres")}</h1>
          {date && <p className="text-sm text-gray-400 mt-1">Données du {date}</p>}
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-xl">
            {error}
          </div>
        )}

        {/* Filtres */}
        <div className="flex flex-wrap gap-3 items-end">
          {/* Recherche */}
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs text-gray-400 mb-1">{t("search", "Recherche")}</label>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="SNTS, Sonatel…"
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm
                         focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>

          {/* Secteur */}
          <div className="min-w-[160px]">
            <label className="block text-xs text-gray-400 mb-1">{t("sector", "Secteur")}</label>
            <select
              value={secteur}
              onChange={(e) => setSecteur(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm
                         focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {secteurs.map((s) => (
                <option key={s} value={s}>{s === "all" ? t("all_filter", "Tous") : s}</option>
              ))}
            </select>
          </div>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: t("stocks", "Titres"),   value: filtered.length, cls: "text-white" },
            { label: t("up",     "Hausse"),   value: up,              cls: "text-green-400" },
            { label: t("down",   "Baisse"),   value: down,            cls: "text-red-400" },
            { label: t("stable", "Stable"),   value: flat,            cls: "text-gray-400" },
          ].map(({ label, value, cls }) => (
            <div key={label} className="card text-center py-3">
              <p className={`text-2xl font-bold ${cls}`}>{loading ? "—" : value}</p>
              <p className="text-xs text-gray-400 mt-1">{label}</p>
            </div>
          ))}
        </div>

        {/* Table */}
        <div className="card p-0 overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-gray-400 animate-pulse">Chargement…</div>
          ) : filtered.length === 0 ? (
            <div className="p-8 text-center text-gray-400">Aucun résultat</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-gray-800">
                  <tr className="text-gray-400 text-xs uppercase tracking-wide">
                    <th className="text-left px-4 py-3 cursor-pointer hover:text-white" onClick={() => toggleSort("symbole")}>
                      Symbole <SortIcon field="symbole" />
                    </th>
                    <th className="text-left px-4 py-3 hidden md:table-cell">
                      {t("company", "Société")}
                    </th>
                    <th className="text-left px-4 py-3 hidden lg:table-cell">
                      {t("sector", "Secteur")}
                    </th>
                    <th className="text-right px-4 py-3 cursor-pointer hover:text-white" onClick={() => toggleSort("cours")}>
                      {t("close_col", "Clôture")} <SortIcon field="cours" />
                    </th>
                    <th className="text-right px-4 py-3 hidden sm:table-cell">
                      {t("prev_col", "Veille")}
                    </th>
                    <th className="text-right px-4 py-3 cursor-pointer hover:text-white" onClick={() => toggleSort("variation")}>
                      Var. <SortIcon field="variation" />
                    </th>
                    <th className="text-right px-4 py-3 cursor-pointer hover:text-white hidden sm:table-cell" onClick={() => toggleSort("volume")}>
                      {t("volume", "Volume")} <SortIcon field="volume" />
                    </th>
                    <th className="text-right px-4 py-3 hidden lg:table-cell">
                      Détail
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((a) => (
                    <tr key={a.symbole} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                      <td className="px-4 py-3 font-mono font-bold text-brand-400">{a.symbole}</td>
                      <td className="px-4 py-3 text-white hidden md:table-cell max-w-[180px] truncate">{a.nom}</td>
                      <td className="px-4 py-3 text-gray-400 text-xs hidden lg:table-cell">{a.secteur}</td>
                      <td className="px-4 py-3 text-right text-white font-medium">
                        {a.cours?.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-400 hidden sm:table-cell">
                        {a.cours_veille?.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <VariationBadge val={a.variation ?? 0} />
                      </td>
                      <td className="px-4 py-3 text-right text-gray-400 hidden sm:table-cell">
                        {a.volume?.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right hidden lg:table-cell">
                        <Link
                          to={`/titres/${a.symbole}`}
                          className="text-xs text-brand-400 hover:underline"
                        >
                          Voir →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <p className="text-xs text-gray-600 text-center">
          {t("source_caption", "Source : BRVM.org")} · {date ?? ""}
        </p>
      </div>
    </div>
  );
}
