/**
 * Analyse Graphique — Afrika Markets Intelligence · Bloomberg-style
 * MA 16/19/246/361 · RSI · MFI · Croisements · Signal global
 *
 * Gestion progressive des données incomplètes :
 *   • DataQualityBanner  — barre de progression + ETA par indicateur
 *   • IndicatorStatus    — badge prêt / en accumulation / insuffisant
 *   • Tous les graphiques s'affichent avec les données disponibles
 *   • Skeleton loading Bloomberg-style
 */
import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ResponsiveContainer, ComposedChart, AreaChart, Area, BarChart, Bar,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, Legend,
} from "recharts";
import { apiGet } from "../lib/api";
import { useAuth } from "../context/AuthContext";

// ── Constantes ───────────────────────────────────────────────

const COLORS = {
  price: "#e8e8e8", ma16: "#00BFFF", ma19: "#22c55e",
  ma246: "#FFD700", ma361: "#FF6B35", rsi: "#00BFFF",
  mfi: "#a855f7", volume: "#006B3F",
};

const TOOLTIP_STYLE = {
  contentStyle: { background: "#0f172a", border: "1px solid #374151", borderRadius: 8, fontSize: 12 },
  labelStyle: { color: "#6b7280" },
};

// Nombre de séances nécessaires par indicateur
const INDICATOR_REQ = {
  "MA 16":   { days: 16,  color: COLORS.ma16,  key: "ma16"  },
  "MA 19":   { days: 19,  color: COLORS.ma19,  key: "ma19"  },
  "RSI 14":  { days: 15,  color: COLORS.rsi,   key: "rsi"   },
  "MFI 14":  { days: 15,  color: COLORS.mfi,   key: "mfi"   },
  "MA 246":  { days: 246, color: COLORS.ma246, key: "ma246" },
  "MA 361":  { days: 361, color: COLORS.ma361, key: "ma361" },
};

// ── Data quality helpers ──────────────────────────────────────

function getDataQuality(data) {
  if (!data || data.length === 0) return { count: 0, level: "empty", readyKeys: new Set() };
  const count = data.length;
  const readyKeys = new Set(
    Object.entries(INDICATOR_REQ)
      .filter(([, r]) => count >= r.days)
      .map(([, r]) => r.key)
  );
  const level =
    count === 0 ? "empty" :
    count < 5   ? "minimal" :
    count < 19  ? "partial" :
    count < 246 ? "good" : "full";
  return { count, level, readyKeys };
}

// Estime le nombre de jours calendaires restants (2 séances/jour grâce au retro-persist)
function etaDays(required, available) {
  const missing = Math.max(0, required - available);
  return Math.ceil(missing / 2); // retro-persist double la vitesse
}

// ── Skeleton ──────────────────────────────────────────────────

function Skeleton({ className = "h-8" }) {
  return <div className={`animate-pulse bg-gray-800/70 rounded-xl ${className}`} />;
}

function SkeletonPage() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-28" />
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-36" />)}
      </div>
      <Skeleton className="h-72" />
      <Skeleton className="h-24" />
      <Skeleton className="h-40" />
      <Skeleton className="h-40" />
    </div>
  );
}

// ── Data Quality Banner ───────────────────────────────────────

function DataQualityBanner({ quality, sym }) {
  const { count, level, readyKeys } = quality;

  if (level === "full") {
    return (
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-green-950/40 border border-green-900/40">
        <span className="text-green-400 text-lg">✓</span>
        <div>
          <p className="text-sm font-semibold text-green-300">Analyse complète — {count} séances</p>
          <p className="text-xs text-green-700">Tous les indicateurs disponibles (MA16/19/246/361 · RSI · MFI)</p>
        </div>
      </div>
    );
  }

  if (level === "empty" || level === "minimal") {
    return (
      <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-red-950/40 border border-red-900/40">
        <span className="text-red-400 text-xl mt-0.5">⚠</span>
        <div>
          <p className="text-sm font-bold text-red-300">Données insuffisantes — {count} séance{count > 1 ? "s" : ""} disponible{count > 1 ? "s" : ""}</p>
          <p className="text-xs text-red-700 mt-0.5">
            Le pipeline accumule les données en temps réel via scraping BRVM + retro-persist cours_veille.
            Minimum 16 séances pour MA16. Revenez demain.
          </p>
        </div>
      </div>
    );
  }

  // partial | good
  const fullDays = 246;
  const pct = Math.min(100, Math.round((count / fullDays) * 100));
  const barColor = level === "partial" ? "#f59e0b" : "#3b82f6";

  return (
    <div className="px-4 py-3 rounded-xl border border-gray-700/60 bg-gray-900/60">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-amber-400">◐</span>
          <p className="text-sm font-semibold text-white">
            Accumulation en cours — <span className="text-amber-300">{count} séances</span>
          </p>
        </div>
        <span className="text-xs text-gray-500">{pct}% vers analyse complète</span>
      </div>

      {/* Progress bar */}
      <div className="relative h-1.5 bg-gray-800 rounded-full overflow-hidden mb-3">
        <div
          className="absolute left-0 top-0 h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: barColor }}
        />
        {/* Milestones */}
        {[16, 19, 246].map((milestone) => (
          <div
            key={milestone}
            className="absolute top-0 h-full w-px bg-gray-600"
            style={{ left: `${(milestone / fullDays) * 100}%` }}
          />
        ))}
      </div>

      {/* Indicator readiness grid */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(INDICATOR_REQ).map(([name, req]) => {
          const ready = count >= req.days;
          const eta   = ready ? 0 : etaDays(req.days, count);
          return (
            <div
              key={name}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
                ready
                  ? "border-green-800/60 bg-green-950/30 text-green-300"
                  : "border-gray-700 bg-gray-900/60 text-gray-500"
              }`}
            >
              <span style={{ color: req.color }}>●</span>
              <span>{name}</span>
              {!ready && <span className="text-gray-600">~{eta}j</span>}
              {ready  && <span className="text-green-600">✓</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Signal card ───────────────────────────────────────────────

function SignalCard({ signal, quality }) {
  const { count, level } = quality;
  const notEnough = level === "empty" || level === "minimal";

  if (notEnough) {
    return (
      <div className="card border border-gray-700/60 flex flex-col gap-2 justify-center items-center py-6">
        <p className="text-3xl">⏳</p>
        <p className="text-xs text-gray-400 text-center">Signal disponible à partir de 16 séances</p>
        <p className="text-xs text-gray-600 text-center">{count}/16 séances</p>
      </div>
    );
  }

  if (!signal?.label) return null;

  const BORDER = {
    "#00CC66": "border-green-600 bg-green-950/30",
    "#FFD700": "border-yellow-600 bg-yellow-950/30",
    "#888888": "border-gray-600 bg-gray-900",
    "#FF6B35": "border-orange-600 bg-orange-950/30",
    "#FF4444": "border-red-600 bg-red-950/30",
  };
  const cls = BORDER[signal.color] || "border-gray-700 bg-gray-900";

  return (
    <div className={`card border ${cls} flex flex-col gap-2`}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400 uppercase tracking-wider">Signal global</span>
        <span className="text-xs text-gray-500">Score {signal.score > 0 ? "+" : ""}{signal.score}</span>
      </div>
      <p className="text-xl font-bold" style={{ color: signal.color }}>{signal.label}</p>
      {level !== "full" && (
        <p className="text-xs text-amber-600">
          ⚠ Partiel — {count} séances ({Object.values(INDICATOR_REQ).filter((r) => count >= r.days).length}/{Object.keys(INDICATOR_REQ).length} indicateurs actifs)
        </p>
      )}
      <div className="space-y-0.5">
        {(signal.reasons || []).map((r) => (
          <p key={r} className="text-xs text-gray-400">• {r}</p>
        ))}
      </div>
    </div>
  );
}

// ── MA card ───────────────────────────────────────────────────

function MaCard({ last, quality }) {
  const { count } = quality;
  return (
    <div className="card">
      <p className="text-xs text-gray-400 mb-2">Moyennes mobiles</p>
      {[
        { label: "MA 16",  val: last?.ma16,  color: COLORS.ma16,  req: 16  },
        { label: "MA 19",  val: last?.ma19,  color: COLORS.ma19,  req: 19  },
        { label: "MA 246", val: last?.ma246, color: COLORS.ma246, req: 246 },
        { label: "MA 361", val: last?.ma361, color: COLORS.ma361, req: 361 },
      ].map(({ label, val, color, req }) => {
        const ready = count >= req;
        const eta   = etaDays(req, count);
        return (
          <div key={label} className="flex justify-between items-center py-0.5">
            <span className="text-xs font-mono" style={{ color }}>{label}</span>
            {ready && val ? (
              <span className="text-xs text-white font-medium">{val.toLocaleString()} F</span>
            ) : (
              <span className="text-xs text-gray-600">~{eta}j</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Gauge circle (RSI / MFI) ──────────────────────────────────

function GaugeCard({ label, value, color, thresholdHigh, thresholdLow, quality, requiredDays }) {
  const { count, level } = quality;
  const ready = count >= requiredDays;

  if (!ready) {
    return (
      <div className="card flex flex-col items-center justify-center gap-2 py-4">
        <p className="text-xs text-gray-400">{label}</p>
        <div className="relative w-20 h-20">
          <svg viewBox="0 0 80 80" className="w-full h-full -rotate-90">
            <circle cx="40" cy="40" r="32" fill="none" stroke="#1f2937" strokeWidth="8" />
            <circle cx="40" cy="40" r="32" fill="none" stroke="#374151" strokeWidth="8"
              strokeDasharray={`${(count / requiredDays) * 201} 201`} strokeLinecap="round" />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xs font-bold text-gray-500">{Math.round((count / requiredDays) * 100)}%</span>
          </div>
        </div>
        <p className="text-xs text-gray-600">{count}/{requiredDays} séances</p>
      </div>
    );
  }

  const pct   = Math.min(100, value ?? 50);
  const radius = 32;
  const circ   = 2 * Math.PI * radius;
  const dash   = (pct / 100) * circ;
  const gaugeColor =
    value > thresholdHigh ? "#ef4444" :
    value < thresholdLow  ? "#22c55e" : color;
  const zone =
    value > thresholdHigh ? `🔴 Suracheté (>${thresholdHigh})` :
    value < thresholdLow  ? `🟢 Survendu (<${thresholdLow})` : "Zone neutre";

  return (
    <div className="card flex flex-col items-center gap-2 py-2">
      <p className="text-xs text-gray-400">{label}</p>
      <div className="relative w-20 h-20">
        <svg viewBox="0 0 80 80" className="w-full h-full -rotate-90">
          <circle cx="40" cy="40" r={radius} fill="none" stroke="#1f2937" strokeWidth="8" />
          <circle cx="40" cy="40" r={radius} fill="none" stroke={gaugeColor} strokeWidth="8"
            strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
            style={{ transition: "stroke-dasharray 0.8s ease" }} />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-base font-bold text-white">{value?.toFixed(0) ?? "—"}</span>
        </div>
      </div>
      <p className="text-xs text-center" style={{ color: gaugeColor }}>{zone}</p>
    </div>
  );
}

// ── Locked chart overlay ──────────────────────────────────────

function PartialOverlay({ label, count, required }) {
  const eta = etaDays(required, count);
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900/80 rounded-xl z-10 gap-2">
      <div className="flex items-center gap-2">
        <div className="w-24 h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-600 rounded-full"
            style={{ width: `${Math.min(100, (count / required) * 100)}%` }}
          />
        </div>
        <span className="text-xs text-gray-400">{count}/{required}</span>
      </div>
      <p className="text-xs text-gray-400 font-medium">{label} disponible dans ~{eta} jour{eta > 1 ? "s" : ""}</p>
      <p className="text-xs text-gray-600">Accumulation automatique toutes les 15 min</p>
    </div>
  );
}

// ── Crossings table ───────────────────────────────────────────

function CrossingTable({ crossings }) {
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

  if (rows.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-6 text-gray-600">
        <p className="text-2xl">↕</p>
        <p className="text-sm">Aucun croisement détecté sur la période disponible</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="border-b border-gray-800">
          <tr className="text-gray-400 text-xs uppercase">
            <th className="text-left px-3 py-2">Date</th>
            <th className="text-left px-3 py-2">Paire MA</th>
            <th className="text-left px-3 py-2">Signal</th>
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 20).map((r, i) => (
            <tr key={i} className="border-b border-gray-800/40 hover:bg-gray-800/20">
              <td className="px-3 py-2 text-gray-300 font-mono text-xs">{r.date}</td>
              <td className="px-3 py-2 text-gray-300 text-xs">{r.pair}</td>
              <td className="px-3 py-2 text-xs font-semibold" style={{ color: r.color }}>
                {r.type === "Golden Cross" ? "▲ " : "▼ "}{r.type}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Price interpretation ──────────────────────────────────────

function PriceInterpretation({ last, quality }) {
  const { count, level } = quality;
  if (!last?.cours || count < 2) return null;

  const cours = last.cours;
  const lines = [];

  if (last.ma16 && last.ma19) {
    if (cours > last.ma16 && cours > last.ma19)
      lines.push({ icon: "▲", color: "#22c55e", text: `Cours au-dessus des MA court terme (MA16/19) — momentum haussier` });
    else if (cours < last.ma16 && cours < last.ma19)
      lines.push({ icon: "▼", color: "#ef4444", text: `Cours sous MA16 et MA19 — pression vendeuse court terme` });
  }
  if (last.ma246) {
    if (cours > last.ma246)
      lines.push({ icon: "▲", color: "#22c55e", text: `Au-dessus de la MA246 — tendance de fond haussière` });
    else
      lines.push({ icon: "▼", color: "#ef4444", text: `Sous la MA246 — tendance de fond baissière ou neutre` });
  }
  if (last.rsi) {
    if (last.rsi < 30)  lines.push({ icon: "◉", color: "#22c55e", text: `RSI ${last.rsi.toFixed(0)} — zone de survente, rebond technique probable` });
    else if (last.rsi > 70) lines.push({ icon: "◉", color: "#ef4444", text: `RSI ${last.rsi.toFixed(0)} — zone de surachat, consolidation probable` });
  }

  if (lines.length === 0 && level !== "full") {
    lines.push({ icon: "◌", color: "#6b7280", text: `${count} séances disponibles — interprétation partielle en cours d'accumulation` });
  }

  return (
    <div className="space-y-1.5">
      {lines.map((l, i) => (
        <p key={i} className="flex items-start gap-2 text-xs text-gray-300">
          <span style={{ color: l.color }} className="mt-0.5 shrink-0">{l.icon}</span>
          <span>{l.text}</span>
        </p>
      ))}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────

export default function Analyse() {
  const { plan } = useAuth();
  const [searchParams] = useSearchParams();

  const [symbols,  setSymbols]  = useState([]);
  const [sym,      setSym]      = useState(searchParams.get("sym") || "");
  const [days,     setDays]     = useState(180);
  const [analysis, setAnalysis] = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState(null);

  useEffect(() => {
    apiGet("/market/actions").then((d) => {
      const syms = (d.data || []).map((a) => ({
        value: a.symbole,
        label: `${a.symbole} — ${a.nom?.substring(0, 32)}`,
        cours: a.cours,
        variation: a.variation,
      }));
      setSymbols(syms);
      if (!sym && syms.length > 0) setSym(syms[0].value);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!sym) return;
    setLoading(true);
    setError(null);
    apiGet(`/analysis/${sym}?days=${days}`)
      .then(setAnalysis)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sym, days]);

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
  const quality   = getDataQuality(data);

  const chartData = data.map((d) => ({
    date:   d.date?.slice(5),
    cours:  d.cours,
    ma16:   d.ma16,
    ma19:   d.ma19,
    ma246:  d.ma246,
    ma361:  d.ma361,
    rsi:    d.rsi,
    mfi:    d.mfi,
    volume: d.volume,
  }));

  // Symbole courant pour affichage
  const symInfo = symbols.find((s) => s.value === sym);

  return (
    <div className="py-8 px-4">
      <div className="max-w-7xl mx-auto space-y-5">

        {/* ── Header Bloomberg ─────────────────────────── */}
        <div className="bg-gradient-to-r from-gray-950 to-blue-950/50 border border-gray-800 rounded-2xl px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs text-gray-500 uppercase tracking-widest">ANALYSE TECHNIQUE</span>
                <span className="text-xs px-2 py-0.5 rounded bg-blue-950 border border-blue-900 text-blue-300">BRVM</span>
              </div>
              <h1 className="text-2xl font-bold text-white font-mono tracking-tight">
                {sym || "—"}
                {symInfo?.cours && (
                  <span className="ml-3 text-lg font-normal text-gray-300">
                    {symInfo.cours.toLocaleString()} F
                    <span className={`ml-2 text-sm ${(symInfo.variation ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {(symInfo.variation ?? 0) >= 0 ? "▲" : "▼"} {Math.abs(symInfo.variation ?? 0).toFixed(2)}%
                    </span>
                  </span>
                )}
              </h1>
              <p className="text-gray-500 text-xs mt-1">
                MA 16 · MA 19 · MA 246 · MA 361 · RSI · MFI · Croisements
              </p>
            </div>

            {/* Contrôles */}
            <div className="flex flex-wrap gap-2 items-end">
              <div className="min-w-[200px]">
                <label className="block text-xs text-gray-500 mb-1">Titre</label>
                <select
                  value={sym}
                  onChange={(e) => setSym(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm
                             focus:outline-none focus:ring-1 focus:ring-blue-600"
                >
                  {symbols.map(({ value, label }) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Période</label>
                <div className="flex gap-1">
                  {[90, 180, 365].map((d) => (
                    <button
                      key={d}
                      onClick={() => setDays(d)}
                      className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors border ${
                        days === d
                          ? "bg-blue-900/60 border-blue-700 text-blue-300"
                          : "bg-gray-900 border-gray-700 text-gray-400 hover:text-white"
                      }`}
                    >
                      {d}j
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── Erreur ───────────────────────────────────── */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-xl">
            ⚠ {error}
          </div>
        )}

        {/* ── Skeleton ─────────────────────────────────── */}
        {loading && <SkeletonPage />}

        {!loading && sym && (
          <>
            {/* ── Data quality banner ───────────────────── */}
            <DataQualityBanner quality={quality} sym={sym} />

            {/* ── KPI row ───────────────────────────────── */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <SignalCard signal={last} quality={quality} />
              <MaCard last={last} quality={quality} />
              <GaugeCard
                label="RSI (14)"
                value={last.rsi}
                color={COLORS.rsi}
                thresholdHigh={70}
                thresholdLow={30}
                quality={quality}
                requiredDays={15}
              />
              <GaugeCard
                label="MFI (14)"
                value={last.mfi}
                color={COLORS.mfi}
                thresholdHigh={80}
                thresholdLow={20}
                quality={quality}
                requiredDays={15}
              />
            </div>

            {/* ── Interprétation ───────────────────────── */}
            {quality.count >= 2 && (
              <div className="card border-l-4 border-blue-800/60">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Lecture des signaux</p>
                <PriceInterpretation last={last} quality={quality} />
              </div>
            )}

            {/* ── Prix + MAs ───────────────────────────── */}
            <div className="card relative">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-white">Prix & Moyennes Mobiles — {sym}</h2>
                <span className="text-xs text-gray-600">{quality.count} séances</span>
              </div>
              {quality.count === 0 ? (
                <div className="h-64 flex items-center justify-center">
                  <p className="text-gray-600 text-sm">Aucune donnée disponible</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <ComposedChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 10 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} tickFormatter={(v) => v?.toLocaleString()} width={72} />
                    <Tooltip {...TOOLTIP_STYLE} formatter={(v, name) => [v ? v.toLocaleString() + " F" : "—", name]} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Area dataKey="cours"  name="Prix"   stroke={COLORS.price} fill="rgba(232,232,232,0.04)" strokeWidth={1.8} dot={false} connectNulls />
                    {quality.count >= 16  && <Line dataKey="ma16"  name="MA 16"  stroke={COLORS.ma16}  strokeWidth={1.2} dot={false} strokeDasharray="4 2" connectNulls />}
                    {quality.count >= 19  && <Line dataKey="ma19"  name="MA 19"  stroke={COLORS.ma19}  strokeWidth={1.5} dot={false} connectNulls />}
                    {quality.count >= 246 && <Line dataKey="ma246" name="MA 246" stroke={COLORS.ma246} strokeWidth={1.5} dot={false} strokeDasharray="6 3" connectNulls />}
                    {quality.count >= 361 && <Line dataKey="ma361" name="MA 361" stroke={COLORS.ma361} strokeWidth={1.5} dot={false} strokeDasharray="3 3" connectNulls />}
                  </ComposedChart>
                </ResponsiveContainer>
              )}
              {quality.count < 16 && quality.count > 0 && (
                <p className="text-xs text-amber-700 mt-1 text-center">
                  Graphique prix disponible · MAs visibles à partir de 16 séances
                </p>
              )}
            </div>

            {/* ── Volume ───────────────────────────────── */}
            {quality.count >= 2 && (
              <div className="card">
                <h2 className="text-sm font-semibold text-white mb-3">Volume</h2>
                <ResponsiveContainer width="100%" height={90}>
                  <BarChart data={chartData} margin={{ top: 0, right: 10, bottom: 0, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 9 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fill: "#6b7280", fontSize: 9 }} tickFormatter={(v) => (v / 1000).toFixed(0) + "k"} width={40} />
                    <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v?.toLocaleString(), "Volume"]} />
                    <Bar dataKey="volume" fill={COLORS.volume} opacity={0.75} radius={[1, 1, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* ── RSI ──────────────────────────────────── */}
            <div className="card relative overflow-hidden">
              <h2 className="text-sm font-semibold mb-3" style={{ color: COLORS.rsi }}>RSI — 14 périodes</h2>
              <ResponsiveContainer width="100%" height={130}>
                <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 9 }} interval="preserveStartEnd" />
                  <YAxis domain={[0, 100]} ticks={[0, 30, 50, 70, 100]} tick={{ fill: "#6b7280", fontSize: 9 }} width={28} />
                  <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v?.toFixed(1), "RSI"]} />
                  <ReferenceLine y={70} stroke="#ef444450" strokeDasharray="4 2" label={{ value: "70", position: "right", fill: "#ef4444", fontSize: 9 }} />
                  <ReferenceLine y={30} stroke="#22c55e50" strokeDasharray="4 2" label={{ value: "30", position: "right", fill: "#22c55e", fontSize: 9 }} />
                  <ReferenceLine y={50} stroke="#55555540" strokeDasharray="2 4" />
                  <Line dataKey="rsi" name="RSI" stroke={COLORS.rsi} strokeWidth={1.8} dot={false} connectNulls />
                </LineChart>
              </ResponsiveContainer>
              {quality.count < 15 && (
                <PartialOverlay label="RSI (14 périodes)" count={quality.count} required={15} />
              )}
            </div>

            {/* ── MFI ──────────────────────────────────── */}
            <div className="card relative overflow-hidden">
              <h2 className="text-sm font-semibold mb-3" style={{ color: COLORS.mfi }}>MFI — 14 périodes</h2>
              <ResponsiveContainer width="100%" height={130}>
                <AreaChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 9 }} interval="preserveStartEnd" />
                  <YAxis domain={[0, 100]} ticks={[0, 20, 50, 80, 100]} tick={{ fill: "#6b7280", fontSize: 9 }} width={28} />
                  <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v?.toFixed(1), "MFI"]} />
                  <ReferenceLine y={80} stroke="#ef444450" strokeDasharray="4 2" label={{ value: "80", position: "right", fill: "#ef4444", fontSize: 9 }} />
                  <ReferenceLine y={20} stroke="#22c55e50" strokeDasharray="4 2" label={{ value: "20", position: "right", fill: "#22c55e", fontSize: 9 }} />
                  <Area dataKey="mfi" name="MFI" stroke={COLORS.mfi} fill="rgba(168,85,247,0.06)" strokeWidth={1.8} dot={false} connectNulls />
                </AreaChart>
              </ResponsiveContainer>
              {quality.count < 15 && (
                <PartialOverlay label="MFI (14 périodes)" count={quality.count} required={15} />
              )}
            </div>

            {/* ── Croisements ──────────────────────────── */}
            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-white">Historique des croisements</h2>
                {quality.count < 246 && (
                  <span className="text-xs text-amber-700 bg-amber-950/30 px-2 py-0.5 rounded-full border border-amber-900/30">
                    MA246/361 dans ~{etaDays(246, quality.count)}j
                  </span>
                )}
              </div>
              <CrossingTable crossings={crossings} />
            </div>

            {/* ── Footer info ───────────────────────────── */}
            <div className="flex items-center gap-2 text-xs text-gray-700 justify-center">
              <span>Source : BRVM (scraping toutes les 15 min)</span>
              <span>·</span>
              <span>Accumulation : {quality.count} séances disponibles</span>
              <span>·</span>
              <span>retro-persist cours_veille actif</span>
            </div>
          </>
        )}

      </div>
    </div>
  );
}
