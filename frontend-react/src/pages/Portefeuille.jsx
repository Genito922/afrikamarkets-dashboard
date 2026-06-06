/**
 * Portefeuille Simulateur — Afrika Markets Intelligence
 * Remplace pages/04_PORTEFEUILLE.py
 * Budget CAD → FCFA, sélection titres, allocation %, simulation P&L
 */
import { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from "recharts";
import { apiGet } from "../lib/api";
import { useAuth } from "../context/AuthContext";

const PIE_COLORS = ["#22c55e","#00BFFF","#FFD700","#f97316","#a855f7","#ec4899","#14b8a6","#f59e0b"];

const TOOLTIP_STYLE = {
  contentStyle: { background: "#0f172a", border: "1px solid #374151", borderRadius: 8, fontSize: 12 },
  labelStyle: { color: "#6b7280" },
};

export default function Portefeuille() {
  const { t } = useTranslation();
  const { plan } = useAuth();

  const [actions,  setActions]  = useState([]);
  const [loading,  setLoading]  = useState(true);

  const [budgetCad, setBudgetCad] = useState(10000);
  const [tauxXof,   setTauxXof]   = useState(445);
  const [selected,  setSelected]  = useState([]);
  const [allocs,    setAllocs]    = useState({});

  const hasAccess = ["starter", "pro", "expert"].includes(plan);

  useEffect(() => {
    apiGet("/market/actions")
      .then((d) => {
        const data = d.data || [];
        setActions(data);
        const defaults = data.slice(0, 3).map((a) => a.symbole);
        setSelected(defaults);
        const init = {};
        defaults.forEach((s, i) => { init[s] = Math.floor(100 / defaults.length); });
        setAllocs(init);
      })
      .finally(() => setLoading(false));
  }, []);

  const budgetFcfa = budgetCad * tauxXof;

  const selectedActions = useMemo(
    () => actions.filter((a) => selected.includes(a.symbole)),
    [actions, selected]
  );

  const totalPct = Object.values(allocs).reduce((s, v) => s + (v || 0), 0);

  const rows = useMemo(() => {
    return selectedActions.map((a) => {
      const pct = (allocs[a.symbole] || 0) / 100;
      const montantFcfa = budgetFcfa * pct;
      const montantCad  = budgetCad  * pct;
      const nbActions   = a.cours > 0 ? Math.floor(montantFcfa / a.cours) : 0;
      const coutReel    = nbActions * a.cours;
      const pnlJour     = nbActions * ((a.cours || 0) - (a.cours_veille || 0));
      return { ...a, pct: allocs[a.symbole] || 0, montantFcfa: coutReel, montantCad, nbActions, pnlJour };
    });
  }, [selectedActions, allocs, budgetFcfa, budgetCad]);

  const totalInvesti = rows.reduce((s, r) => s + r.montantFcfa, 0);
  const totalPnl     = rows.reduce((s, r) => s + r.pnlJour, 0);
  const totalPnlCad  = totalPnl / tauxXof;
  const cash         = budgetFcfa - totalInvesti;

  function toggleSym(sym) {
    setSelected((prev) => {
      if (prev.includes(sym)) {
        const next = prev.filter((s) => s !== sym);
        setAllocs((a) => { const n = { ...a }; delete n[sym]; return n; });
        return next;
      } else {
        setAllocs((a) => ({ ...a, [sym]: 0 }));
        return [...prev, sym];
      }
    });
  }

  function setAlloc(sym, val) {
    setAllocs((prev) => ({ ...prev, [sym]: Math.max(0, Math.min(100, Number(val))) }));
  }

  if (!hasAccess) {
    return (
      <div className="py-20 px-4 text-center">
        <p className="text-4xl mb-4">🔒</p>
        <h2 className="text-2xl font-bold text-white mb-2">Simulateur de portefeuille — Plan Starter+</h2>
        <p className="text-gray-400 mb-6">Simulez votre portefeuille BRVM avec conversion CAD → FCFA</p>
        <Link to="/pricing" className="btn-primary">Voir les offres →</Link>
      </div>
    );
  }

  return (
    <div className="py-8 px-4">
      <div className="max-w-7xl mx-auto space-y-6">

        <div>
          <h1 className="text-2xl font-bold text-white">{t("portfolio_title", "Simulateur de Portefeuille BRVM")}</h1>
          <p className="text-gray-400 text-sm mt-1">{t("portfolio_desc", "Estimez vos positions en FCFA depuis votre budget en CAD")}</p>
        </div>

        {/* Paramètres */}
        <div className="card">
          <h2 className="text-sm font-semibold text-white mb-4">{t("settings", "Paramètres")}</h2>
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Budget (CAD $)</label>
              <input
                type="number" min={1000} max={500000} step={1000}
                value={budgetCad}
                onChange={(e) => setBudgetCad(Number(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm
                           focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">1 CAD = X FCFA</label>
              <input
                type="number" min={400} max={500} step={0.5}
                value={tauxXof}
                onChange={(e) => setTauxXof(Number(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm
                           focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
            <div className="card bg-gray-800 flex flex-col justify-center">
              <p className="text-xs text-gray-400">Budget en FCFA</p>
              <p className="text-xl font-bold text-brand-400">{budgetFcfa.toLocaleString()} F</p>
            </div>
          </div>
        </div>

        {/* Sélection titres */}
        <div className="card">
          <h2 className="text-sm font-semibold text-white mb-3">{t("stock_selection", "Sélection des titres")}</h2>
          {loading ? (
            <div className="h-20 animate-pulse bg-gray-800 rounded-lg" />
          ) : (
            <div className="flex flex-wrap gap-2">
              {actions.slice(0, 40).map((a) => {
                const sel = selected.includes(a.symbole);
                return (
                  <button
                    key={a.symbole}
                    onClick={() => toggleSym(a.symbole)}
                    className={`px-2 py-1 rounded-lg text-xs font-mono font-medium transition-colors ${
                      sel ? "bg-brand-500 text-white" : "bg-gray-800 text-gray-400 hover:text-white"
                    }`}
                  >
                    {a.symbole}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Allocation */}
        {selected.length > 0 && (
          <div className="card space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">{t("portfolio_allocation", "Allocation (%)")}</h2>
              <span className={`text-xs font-medium ${totalPct === 100 ? "text-green-400" : "text-yellow-400"}`}>
                Total : {totalPct}%
              </span>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {selected.map((sym) => (
                <div key={sym} className="flex items-center gap-3">
                  <span className="font-mono font-bold text-brand-400 w-12">{sym}</span>
                  <input
                    type="range" min={0} max={100} step={5}
                    value={allocs[sym] || 0}
                    onChange={(e) => setAlloc(sym, e.target.value)}
                    className="flex-1 accent-brand-500"
                  />
                  <span className="text-white text-sm w-8 text-right">{allocs[sym] || 0}%</span>
                </div>
              ))}
            </div>
            {totalPct !== 100 && (
              <p className="text-xs text-yellow-400">⚠ L'allocation totale doit être égale à 100% (actuellement {totalPct}%)</p>
            )}
          </div>
        )}

        {/* KPIs résultats */}
        {rows.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="card text-center">
              <p className="text-xs text-gray-400 mb-1">Budget CAD</p>
              <p className="text-lg font-bold text-white">${budgetCad.toLocaleString()}</p>
            </div>
            <div className="card text-center">
              <p className="text-xs text-gray-400 mb-1">Investi FCFA</p>
              <p className="text-lg font-bold text-white">{totalInvesti.toLocaleString()} F</p>
            </div>
            <div className="card text-center">
              <p className="text-xs text-gray-400 mb-1">P&L journalier</p>
              <p className={`text-lg font-bold ${totalPnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                {totalPnl >= 0 ? "+" : ""}{totalPnl.toLocaleString(0)} F
              </p>
              <p className={`text-xs ${totalPnlCad >= 0 ? "text-green-400" : "text-red-400"}`}>
                ${totalPnlCad >= 0 ? "+" : ""}{totalPnlCad.toFixed(0)} CAD
              </p>
            </div>
            <div className="card text-center">
              <p className="text-xs text-gray-400 mb-1">Cash disponible</p>
              <p className="text-lg font-bold text-gray-300">{Math.max(0, cash).toLocaleString()} F</p>
            </div>
          </div>
        )}

        {/* Charts */}
        {rows.length > 0 && (
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Pie allocation */}
            <div className="card">
              <h2 className="text-sm font-semibold text-white mb-4">Répartition du portefeuille</h2>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={rows.map((r) => ({ name: r.symbole, value: r.montantFcfa || 1 }))}
                    cx="50%" cy="50%" outerRadius={80}
                    dataKey="value" nameKey="name" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {rows.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v.toLocaleString() + " F"]} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Bar P&L */}
            <div className="card">
              <h2 className="text-sm font-semibold text-white mb-4">P&L journalier par titre (FCFA)</h2>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={rows.map((r) => ({ name: r.symbole, pnl: Math.round(r.pnlJour) }))}
                  margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="name" tick={{ fill: "#6b7280", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} tickFormatter={(v) => v.toLocaleString()} />
                  <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [(v >= 0 ? "+" : "") + v.toLocaleString() + " F", "P&L"]} />
                  <Bar dataKey="pnl" radius={[3, 3, 0, 0]}>
                    {rows.map((r, i) => (
                      <Cell key={i} fill={r.pnlJour >= 0 ? "#22c55e" : "#ef4444"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Table détail */}
        {rows.length > 0 && (
          <div className="card p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-gray-800">
                  <tr className="text-gray-400 text-xs uppercase tracking-wide">
                    <th className="text-left px-4 py-3">Symbole</th>
                    <th className="text-right px-4 py-3">Alloc %</th>
                    <th className="text-right px-4 py-3">Montant FCFA</th>
                    <th className="text-right px-4 py-3">Actions</th>
                    <th className="text-right px-4 py-3">Cours</th>
                    <th className="text-right px-4 py-3">Var %</th>
                    <th className="text-right px-4 py-3">P&L FCFA</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.symbole} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                      <td className="px-4 py-3 font-mono font-bold text-brand-400">{r.symbole}</td>
                      <td className="px-4 py-3 text-right text-gray-300">{r.pct}%</td>
                      <td className="px-4 py-3 text-right text-gray-300">{r.montantFcfa.toLocaleString()}</td>
                      <td className="px-4 py-3 text-right text-white font-medium">{r.nbActions}</td>
                      <td className="px-4 py-3 text-right text-gray-300">{r.cours?.toLocaleString()}</td>
                      <td className={`px-4 py-3 text-right font-medium ${r.variation >= 0 ? "text-green-400" : "text-red-400"}`}>
                        {r.variation >= 0 ? "+" : ""}{r.variation?.toFixed(2)}%
                      </td>
                      <td className={`px-4 py-3 text-right font-medium ${r.pnlJour >= 0 ? "text-green-400" : "text-red-400"}`}>
                        {r.pnlJour >= 0 ? "+" : ""}{Math.round(r.pnlJour).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
