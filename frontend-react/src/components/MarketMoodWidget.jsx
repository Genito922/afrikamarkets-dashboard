/**
 * MarketMoodWidget — Composant autonome humeur du marché BRVM
 *
 * Variantes :
 *   compact  — barre de statut (usage hero, overview)
 *   full     — panneau complet avec régime, secteurs, interprétation
 *
 * Source : GET /market/mood
 */
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { apiGet } from "../lib/api";

const MOOD_ICON = {
  bull: "▲▲", bull_mild: "▲", neutral: "—", bear_mild: "▼", bear: "▼▼",
};

function VolumeQualityBar({ ratio }) {
  if (ratio == null) return null;
  const pct  = Math.min(200, Math.round(ratio * 100));
  const norm = Math.min(100, pct);          // 0..100 for the bar
  const color = ratio < 0.5 ? "#6b7280" : ratio > 1.5 ? "#22c55e" : "#3b82f6";
  const label = ratio < 0.5 ? "Volume faible" : ratio > 1.5 ? "Volume élevé" : "Volume normal";
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500 w-24 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${norm}%`, background: color }}
        />
      </div>
      <span className="text-xs font-mono text-gray-500 w-10 text-right">
        {ratio.toFixed(2)}×
      </span>
    </div>
  );
}

function RegimeBadge({ regime }) {
  if (!regime) return null;
  return (
    <span
      className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full border"
      style={{
        color:       regime.color,
        borderColor: regime.color + "55",
        background:  regime.color + "18",
      }}
    >
      <span>{regime.icon}</span>
      <span>{regime.label}</span>
    </span>
  );
}

function SectorDrivers({ drivers }) {
  if (!drivers) return null;
  const { top = [], flop = [] } = drivers;
  if (!top.length && !flop.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {top.slice(0, 2).map((s) => (
        <span
          key={s.secteur}
          className="text-xs px-2 py-0.5 rounded bg-green-900/30 text-green-400 border border-green-800/40"
        >
          {s.secteur} <span className="font-mono">+{s.variation_moy}%</span>
        </span>
      ))}
      {flop.slice(0, 1).map((s) => (
        <span
          key={s.secteur}
          className="text-xs px-2 py-0.5 rounded bg-red-900/30 text-red-400 border border-red-800/40"
        >
          {s.secteur} <span className="font-mono">{s.variation_moy}%</span>
        </span>
      ))}
    </div>
  );
}

// ── Variante compacte (hero / navbar-like) ────────────────────

function CompactWidget({ mood }) {
  return (
    <div
      className="flex flex-wrap items-center gap-4 px-5 py-3 rounded-2xl border transition-all"
      style={{ background: mood.color + "0d", borderColor: mood.color + "33" }}
    >
      {/* Indicateur principal */}
      <div className="flex items-center gap-2.5">
        <div className="relative">
          <span
            className="w-3 h-3 rounded-full block"
            style={{ background: mood.color, boxShadow: `0 0 8px ${mood.color}80` }}
          />
          {(mood.mood === "bull" || mood.mood === "bear") && (
            <span
              className="absolute inset-0 rounded-full animate-ping"
              style={{ background: mood.color, opacity: 0.3 }}
            />
          )}
        </div>
        <span className="text-sm font-bold" style={{ color: mood.color }}>
          {MOOD_ICON[mood.mood]} {mood.label}
        </span>
      </div>

      {mood.regime && (
        <>
          <div className="w-px h-4 bg-gray-700 hidden sm:block" />
          <RegimeBadge regime={mood.regime} />
        </>
      )}

      <div className="w-px h-4 bg-gray-700 hidden sm:block" />

      {mood.composite_var != null && (
        <div className="text-xs text-gray-400">
          BRVM Composite{" "}
          <span className="font-mono font-semibold" style={{ color: mood.color }}>
            {mood.composite_var >= 0 ? "+" : ""}{mood.composite_var.toFixed(2)}%
          </span>
        </div>
      )}

      <div className="w-px h-4 bg-gray-700 hidden sm:block" />

      <div className="text-xs text-gray-400">
        <span className="text-green-400 font-semibold">{mood.breadth.nb_up}↑</span>
        {" · "}
        <span className="text-red-400 font-semibold">{mood.breadth.nb_down}↓</span>
        {" · "}
        <span className="text-gray-500">{mood.breadth.nb_stable}=</span>
        <span className="text-gray-600 ml-1">titres</span>
      </div>

      <div className="ml-auto flex items-center gap-3">
        <span className="text-xs text-gray-600 hidden sm:block">↻ 15 min</span>
        <Link
          to="/risques"
          className="text-xs text-gray-500 hover:text-brand-400 transition-colors hidden sm:block"
        >
          Analyse complète →
        </Link>
      </div>
    </div>
  );
}

// ── Variante complète ─────────────────────────────────────────

function FullWidget({ mood }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="rounded-2xl border overflow-hidden transition-all"
      style={{ background: mood.color + "08", borderColor: mood.color + "33" }}
    >
      {/* En-tête */}
      <div className="flex items-center justify-between px-5 py-4 gap-4">
        <div className="flex items-center gap-3 flex-wrap">
          {/* Dot animé */}
          <div className="relative shrink-0">
            <span
              className="w-3 h-3 rounded-full block"
              style={{ background: mood.color, boxShadow: `0 0 10px ${mood.color}80` }}
            />
            {(mood.mood === "bull" || mood.mood === "bear") && (
              <span
                className="absolute inset-0 rounded-full animate-ping"
                style={{ background: mood.color, opacity: 0.3 }}
              />
            )}
          </div>

          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-bold" style={{ color: mood.color }}>
                {MOOD_ICON[mood.mood]} {mood.label}
              </span>
              {mood.regime && <RegimeBadge regime={mood.regime} />}
            </div>
            {mood.composite_var != null && (
              <div className="text-xs text-gray-500 mt-0.5">
                BRVM Composite{" "}
                <span className="font-mono" style={{ color: mood.color }}>
                  {mood.composite_var >= 0 ? "+" : ""}{mood.composite_var.toFixed(2)}%
                </span>
                {mood.brvm30_var != null && (
                  <span className="ml-2 text-gray-600">
                    · BRVM 30{" "}
                    <span className="font-mono">
                      {mood.brvm30_var >= 0 ? "+" : ""}{mood.brvm30_var.toFixed(2)}%
                    </span>
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Score */}
        <div className="shrink-0 text-center">
          <div
            className="text-2xl font-black font-mono leading-none"
            style={{ color: mood.color }}
          >
            {mood.score >= 0 ? "+" : ""}{mood.score}
          </div>
          <div className="text-xs text-gray-600 mt-0.5">/ 4</div>
        </div>
      </div>

      {/* Breadth + secteurs */}
      <div className="px-5 pb-3 space-y-2.5 border-t border-gray-800/60 pt-3">
        <div className="flex flex-wrap gap-3 text-xs">
          <span className="text-gray-400">
            <span className="text-green-400 font-semibold">{mood.breadth.nb_up}↑</span>
            {" · "}
            <span className="text-red-400 font-semibold">{mood.breadth.nb_down}↓</span>
            {" · "}
            <span className="text-gray-500">{mood.breadth.nb_stable}=</span>
            <span className="text-gray-600 ml-1">
              ({mood.breadth.total} titres)
            </span>
          </span>
          {mood.macro && (
            <span className="text-gray-500">
              USD/XOF{" "}
              <span className="font-mono text-gray-300">{mood.macro.usd_xof}</span>
            </span>
          )}
        </div>

        {mood.volume_ratio != null && (
          <VolumeQualityBar ratio={mood.volume_ratio} />
        )}

        {mood.sector_drivers && (
          <SectorDrivers drivers={mood.sector_drivers} />
        )}
      </div>

      {/* Interprétation */}
      {mood.interpretation && (
        <div className="px-5 pb-4">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full text-left"
          >
            <div className="flex items-center justify-between text-xs text-gray-500 hover:text-gray-300 transition-colors py-1">
              <span>Interprétation du marché</span>
              <span className={`transition-transform ${expanded ? "rotate-180" : ""}`}>▾</span>
            </div>
          </button>
          {expanded && (
            <p className="text-xs text-gray-400 leading-relaxed mt-1 pb-1">
              {mood.interpretation}
            </p>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between px-5 py-2 border-t border-gray-800/60 bg-gray-900/30">
        <span className="text-xs text-gray-600">↻ mise à jour toutes les 15 min</span>
        <Link
          to="/risques"
          className="text-xs text-brand-400 hover:text-brand-300 transition-colors"
        >
          War Room →
        </Link>
      </div>
    </div>
  );
}

// ── Composant principal ───────────────────────────────────────

export default function MarketMoodWidget({ variant = "compact" }) {
  const [mood, setMood]       = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet("/market/mood")
      .then(setMood)
      .catch(() => setMood(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-3 px-4 py-3 rounded-2xl bg-gray-900/60 border border-gray-800 animate-pulse">
        <div className="w-3 h-3 rounded-full bg-gray-700" />
        <div className="h-4 w-32 bg-gray-800 rounded" />
        <div className="h-4 w-20 bg-gray-800 rounded ml-2" />
      </div>
    );
  }

  if (!mood || mood.no_data) {
    return (
      <div className="flex items-center gap-3 px-4 py-3 rounded-2xl bg-gray-900/60 border border-gray-800">
        <span className="w-3 h-3 rounded-full bg-gray-600" />
        <span className="text-sm text-gray-500">
          Données de marché en cours d'initialisation
        </span>
      </div>
    );
  }

  if (variant === "full") return <FullWidget mood={mood} />;
  return <CompactWidget mood={mood} />;
}
