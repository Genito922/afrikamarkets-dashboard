/**
 * Marchés Internationaux — Plan Expert
 * Remplace 09_MARCHES_INTERNATIONAUX.py
 * yfinance : Commodités · Indices · Forex/CFA · Crypto + Impact BRVM
 */
import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ResponsiveContainer, ComposedChart, AreaChart, LineChart,
  Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
} from "recharts";
import { apiGet } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import ComplianceBanner from "../components/ComplianceBanner";

// ── Asset catalogue ──────────────────────────────────────────

const CATEGORIES = {
  commodities: {
    label: "Matières Premières", icon: "🌾",
    assets: [
      { ticker: "CC=F",  label: "Cacao",      icon: "🍫", unit: "USD/t" },
      { ticker: "KC=F",  label: "Café",        icon: "☕", unit: "USD/lb" },
      { ticker: "GC=F",  label: "Or",          icon: "🥇", unit: "USD/oz" },
      { ticker: "CL=F",  label: "WTI Pétrole", icon: "🛢️", unit: "USD/bbl" },
    ],
  },
  indices: {
    label: "Indices & Taux", icon: "📊",
    assets: [
      { ticker: "^GSPC", label: "S&P 500",    icon: "🇺🇸", unit: "pts" },
      { ticker: "^FCHI", label: "CAC 40",     icon: "🇫🇷", unit: "pts" },
      { ticker: "GBL=F", label: "Bund 10Y",   icon: "🇩🇪", unit: "EUR" },
      { ticker: "ZN=F",  label: "T-Note 10Y", icon: "🇺🇸", unit: "pts" },
    ],
  },
  forex: {
    label: "Forex & CFA", icon: "💱", showXof: true,
    assets: [
      { ticker: "EURUSD=X", label: "EUR/USD", icon: "🇪🇺", unit: "" },
      { ticker: "USDCAD=X", label: "USD/CAD", icon: "🇨🇦", unit: "" },
      { ticker: "GBPUSD=X", label: "GBP/USD", icon: "🇬🇧", unit: "" },
      { ticker: "USDCHF=X", label: "USD/CHF", icon: "🇨🇭", unit: "" },
    ],
  },
  crypto: {
    label: "Crypto", icon: "₿",
    assets: [
      { ticker: "BTC-USD", label: "Bitcoin",  icon: "₿",  unit: "USD" },
      { ticker: "ETH-USD", label: "Ethereum", icon: "Ξ",  unit: "USD" },
      { ticker: "BNB-USD", label: "BNB",      icon: "🔶", unit: "USD" },
      { ticker: "XRP-USD", label: "XRP",      icon: "✦",  unit: "USD" },
    ],
  },
};

const IMPACT_BRVM = {
  commodities: {
    title: "Matières Premières & BRVM",
    items: [
      {
        icon: "🍫", label: "Cacao (CC=F)",
        text: "La Côte d'Ivoire produit ~40% du cacao mondial. Un cours élevé soutient les revenus d'export, renforce le FCFA et bénéficie aux titres agro-industriels BRVM (PALC, SOGB). Corrélation positive directe avec la capitalisation BRVM CI.",
      },
      {
        icon: "☕", label: "Café (KC=F)",
        text: "Deuxième culture d'export ivoirienne après le cacao. Impact modéré mais réel sur les marges des filières transformatrices cotées. Un cours café élevé améliore les revenus paysans et la consommation domestique.",
      },
      {
        icon: "🥇", label: "Or (GC=F)",
        text: "Le Mali et le Burkina Faso sont producteurs d'or. Un cours Or en hausse améliore leurs recettes fiscales, réduisant la pression sur le FCFA. Impact indirect sur la stabilité régionale UEMOA.",
      },
      {
        icon: "🛢️", label: "WTI Pétrole (CL=F)",
        text: "Le Sénégal a démarré la production de pétrole (Sangomar, 2024). Un cours pétrolier élevé valorise les actifs sénégalais et pourrait attirer des cotations BRVM dans le secteur énergétique à horizon 2026.",
      },
    ],
  },
  indices: {
    title: "Indices Mondiaux & Sentiment UEMOA",
    items: [
      {
        icon: "🇺🇸", label: "S&P 500 (^GSPC)",
        text: "Baromètre mondial du risque. Une chute du S&P 500 déclenche un risk-off global : les flux vers les marchés émergents (dont UEMOA) se contractent. Impact sur les investisseurs institutionnels exposés à la BRVM.",
      },
      {
        icon: "🇫🇷", label: "CAC 40 (^FCHI)",
        text: "La France reste le premier partenaire commercial et investisseur en zone UEMOA. Un CAC 40 solide favorise les IDE français, les projets d'infrastructure et les cotations de filiales africaines (Total, Bolloré, etc.).",
      },
      {
        icon: "🇩🇪", label: "Bund 10Y (GBL=F)",
        text: "Taux de référence zone euro. Influence le coût des financements en EUR pour les États UEMOA (Eurobonds). Un Bund en hausse renchérit la dette souveraine de la région.",
      },
      {
        icon: "🇺🇸", label: "T-Note 10Y (ZN=F)",
        text: "Référence mondiale du coût du capital. Un taux US élevé renforce le dollar, affaiblit l'EURUSD et mécaniquement le pouvoir d'achat XOF en USD. Impact sur les importations UEMOA libellées en dollars.",
      },
    ],
  },
  forex: {
    title: "Forex & Parité CFA",
    items: [
      {
        icon: "🔒", label: "EUR/XOF — Parité fixe 655,957",
        text: "Le FCFA est ancré à l'euro depuis 1999 (parité fixe inchangée). Cette convertibilité garantie offre une stabilité monétaire rare en Afrique, mais supprime la flexibilité des changes. Les variations EUR/USD et EUR/GBP impactent indirectement le pouvoir d'achat des pays UEMOA.",
      },
      {
        icon: "🇨🇦", label: "USD/CAD — Diaspora canadienne",
        text: "La diaspora africaine au Canada (Montréal, Toronto) effectue d'importants transferts vers l'UEMOA. Un CAD fort augmente les remises en FCFA, soutenant la consommation et l'épargne domestique. Afrikamarkets cible précisément ce segment.",
      },
      {
        icon: "🇬🇧", label: "GBP/USD",
        text: "La livre sterling forte reflète une économie britannique solide, favorable aux investissements UK en Afrique de l'Ouest (notamment au Ghana et Nigéria, marchés voisins). Impact limité mais monitored sur la compétitivité des exportations UEMOA vers le Royaume-Uni.",
      },
      {
        icon: "🇨🇭", label: "USD/CHF — Safe haven",
        text: "Un CHF fort (refuge) signale une aversion globale au risque. Dans ce contexte, les flux sortent des marchés émergents. Indicateur de stress utile à surveiller pour anticiper une correction BRVM.",
      },
    ],
  },
  crypto: {
    title: "Cryptomonnaies & Afrique de l'Ouest",
    items: [
      {
        icon: "₿", label: "Bitcoin (BTC)",
        text: "L'Afrique de l'Ouest est l'une des régions avec le plus fort taux d'adoption crypto (Nigeria #3 mondial, Ghana #4). Un BTC en hausse attire les capitaux locaux vers les crypto au détriment des actifs traditionnels BRVM. Corrélation négative en période de rally crypto intense.",
      },
      {
        icon: "Ξ", label: "Ethereum (ETH)",
        text: "L'écosystème DeFi sur Ethereum offre des rendements alternatifs attractifs. En période de bull market ETH, les investisseurs sophistiqués de la diaspora peuvent arbitrer entre BRVM et DeFi. Phénomène émergent mais croissant.",
      },
      {
        icon: "🔶", label: "BNB / Binance",
        text: "Binance est la plateforme crypto dominante en Afrique. Le succès de BNB témoigne de l'adoption de la finance digitale dans la région. Des partenariats Binance Pay en FCFA sont en cours d'exploration avec plusieurs pays UEMOA.",
      },
      {
        icon: "✦", label: "XRP / Ripple",
        text: "XRP est utilisé pour les transferts internationaux rapides. Des corridors de remises XRP vers l'Afrique de l'Ouest (incluant zone FCFA) sont actifs via des partenaires comme Flutterwave. Impact potentiel sur les flux de transferts traditionnels Western Union / MoneyGram.",
      },
    ],
  },
};

// ── African exchanges sub-page ───────────────────────────────

const EXCHANGE_FLAGS = {
  brvm: "🌍", jse: "🇿🇦", ngx: "🇳🇬", gse: "🇬🇭",
  nse: "🇰🇪", egx: "🇪🇬", bvc: "🇲🇦", bvmt: "🇹🇳", dse: "🇹🇿",
};

function RisqueBar({ niveau }) {
  const pct = (niveau / 10) * 100;
  const color = niveau <= 3 ? "#22c55e" : niveau <= 5 ? "#f59e0b" : "#ef4444";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-800 rounded-full h-1.5 overflow-hidden">
        <div style={{ width: `${pct}%`, background: color }} className="h-full rounded-full" />
      </div>
      <span className="text-xs font-medium" style={{ color }}>{niveau}/10</span>
    </div>
  );
}

function AiSignalBadge({ label, color, score }) {
  if (!label) return null;
  return (
    <span
      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold"
      style={{ background: color + "22", color, border: `1px solid ${color}55` }}
    >
      {score > 0 ? "▲" : score < 0 ? "▼" : "–"} {label}
    </span>
  );
}

function SgiRow({ sgi }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2.5 border-b border-gray-800/60 last:border-0">
      <div className="min-w-0">
        <a
          href={sgi.url} target="_blank" rel="noopener noreferrer"
          className="text-sm font-medium text-blue-300 hover:underline truncate block"
        >
          {sgi.nom}
        </a>
        <p className="text-xs text-gray-500">{sgi.pays}</p>
      </div>
      <div className="flex items-center gap-3 shrink-0 text-xs">
        <span className="text-gray-300 font-mono">{sgi.courtage}</span>
        {sgi.app    && <span title="App mobile" className="text-green-400">📱</span>}
        {sgi.en_ligne && <span title="Ouverture en ligne" className="text-blue-400">🌐</span>}
        {sgi.diaspora && <span title="Accès diaspora" className="text-yellow-400">✈️</span>}
        <span className="px-1.5 py-0.5 rounded bg-gray-800 text-white font-semibold">
          {sgi.note}
        </span>
      </div>
    </div>
  );
}

function ExchangeCard({ ex, reco, onClick, active }) {
  const macro = reco?.macro;
  return (
    <button
      onClick={onClick}
      className={`card text-left w-full transition-all border-2 ${
        active ? "border-brand-500 bg-brand-500/5" : "border-transparent hover:border-gray-700"
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div>
          <span className="text-2xl">{ex.flag}</span>
          <p className="text-base font-bold text-white mt-0.5">{ex.nom}</p>
          <p className="text-xs text-gray-400">{ex.pays} · {ex.devise}</p>
        </div>
        {reco && <AiSignalBadge label={reco.label} color={reco.color} score={reco.score} />}
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mt-2">
        <div><span className="text-gray-500">Cap. </span><span className="text-white font-medium">{ex.cap_usd_b}B$</span></div>
        <div><span className="text-gray-500">Sociétés </span><span className="text-white font-medium">{ex.nb_societes}</span></div>
        {macro && (
          <>
            <div><span className="text-gray-500">PIB </span><span className="text-green-400 font-medium">+{macro.pib_growth}%</span></div>
            <div><span className="text-gray-500">Inflation </span><span className={`font-medium ${macro.inflation > 15 ? "text-red-400" : "text-yellow-300"}`}>{macro.inflation}%</span></div>
          </>
        )}
      </div>
      {macro && <RisqueBar niveau={macro.risque} />}
    </button>
  );
}

function AfricanMarketsTab() {
  const [subTab,      setSubTab]      = useState("overview");   // overview | sgis | ai-reco
  const [exchanges,   setExchanges]   = useState([]);
  const [recos,       setRecos]       = useState([]);
  const [sgis,        setSgis]        = useState([]);
  const [loadReco,    setLoadReco]    = useState(false);
  const [loadSgi,     setLoadSgi]     = useState(false);
  const [selSlug,     setSelSlug]     = useState("brvm");
  const [error,       setError]       = useState(null);

  // Catalogue exchanges
  useEffect(() => {
    apiGet("/african-markets/exchanges")
      .then((r) => setExchanges(r.exchanges || []))
      .catch(() => {});
  }, []);

  // AI recommendations
  useEffect(() => {
    if (subTab !== "ai-reco") return;
    setLoadReco(true);
    apiGet("/african-markets/ai-reco")
      .then((r) => setRecos(r.recommendations || []))
      .catch((e) => setError(e?.message || "Erreur"))
      .finally(() => setLoadReco(false));
  }, [subTab]);

  // SGI per exchange
  useEffect(() => {
    if (subTab !== "sgis") return;
    setLoadSgi(true);
    setSgis([]);
    apiGet(`/african-markets/exchanges/${selSlug}/sgis`)
      .then((r) => setSgis(r.sgis || []))
      .catch(() => setSgis([]))
      .finally(() => setLoadSgi(false));
  }, [subTab, selSlug]);

  const recoBySlug = Object.fromEntries(recos.map((r) => [r.slug, r]));

  const SUB_TABS = [
    { key: "overview",  label: "🌍 Aperçu marchés" },
    { key: "sgis",      label: "🏢 Annuaire SGI" },
    { key: "ai-reco",   label: "🤖 Recommandation IA" },
  ];

  return (
    <div className="space-y-5">
      {/* Sub-tabs */}
      <div className="flex gap-1 overflow-x-auto">
        {SUB_TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setSubTab(key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
              subTab === key ? "bg-gray-800 text-white" : "text-gray-400 hover:text-white hover:bg-gray-800/50"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── Overview ── */}
      {subTab === "overview" && (
        <div className="space-y-4">
          <div className="card bg-gradient-to-r from-emerald-950/60 to-teal-950/60 border border-emerald-900/30">
            <h2 className="text-base font-bold text-white mb-1">🌍 Panorama des bourses africaines</h2>
            <p className="text-xs text-gray-400">
              9 places boursières · De Casablanca à Johannesburg · 800+ sociétés cotées
            </p>
          </div>
          {exchanges.length === 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {[...Array(9)].map((_, i) => <div key={i} className="card h-36 animate-pulse" />)}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {exchanges.map((ex) => (
                <ExchangeCard
                  key={ex.slug}
                  ex={ex}
                  reco={recoBySlug[ex.slug]}
                  onClick={() => { setSelSlug(ex.slug); setSubTab("sgis"); }}
                  active={false}
                />
              ))}
            </div>
          )}
          <p className="text-xs text-gray-600 text-center">
            Cliquer sur une bourse → voir ses SGI · Capitalisations estimées en milliards USD
          </p>
        </div>
      )}

      {/* ── SGI directory ── */}
      {subTab === "sgis" && (
        <div className="space-y-4">
          {/* Exchange selector */}
          <div className="flex flex-wrap gap-2">
            {exchanges.map((ex) => (
              <button
                key={ex.slug}
                onClick={() => setSelSlug(ex.slug)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${
                  selSlug === ex.slug
                    ? "bg-brand-500 border-brand-500 text-white"
                    : "bg-gray-900 border-gray-700 text-gray-300 hover:border-gray-500"
                }`}
              >
                <span>{ex.flag}</span>
                <span>{ex.nom}</span>
              </button>
            ))}
          </div>

          {loadSgi ? (
            <div className="card animate-pulse h-48" />
          ) : (
            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-white">
                  {EXCHANGE_FLAGS[selSlug]} SGI / Courtiers — {selSlug.toUpperCase()}
                </h3>
                <span className="text-xs text-gray-500">{sgis.length} courtiers</span>
              </div>
              {sgis.length === 0 ? (
                <p className="text-sm text-gray-500 py-4 text-center">Aucun courtier répertorié</p>
              ) : (
                <div>
                  <div className="flex justify-between text-xs text-gray-500 mb-2 px-0.5">
                    <span>Nom · Pays</span>
                    <span>Courtage · 📱 🌐 ✈️ · Note</span>
                  </div>
                  {sgis.map((sgi, i) => <SgiRow key={i} sgi={sgi} />)}
                </div>
              )}
              <p className="text-xs text-gray-600 mt-3">
                📱 App mobile · 🌐 Ouverture en ligne · ✈️ Accès diaspora
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── AI Recommendations ── */}
      {subTab === "ai-reco" && (
        <div className="space-y-4">
          <div className="card bg-gradient-to-r from-violet-950/60 to-purple-950/60 border border-violet-900/30">
            <h2 className="text-base font-bold text-white mb-1">🤖 Recommandation IA — Marchés africains</h2>
            <p className="text-xs text-gray-400">
              Analyse combinée : signaux techniques (RSI · MA · MFI) + contexte macro (PIB · inflation · risque politique)
            </p>
          </div>

          {loadReco ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => <div key={i} className="card h-28 animate-pulse" />)}
            </div>
          ) : error ? (
            <div className="card text-center py-8">
              <p className="text-gray-400">{error}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {recos.map((reco) => (
                <div key={reco.slug} className="card border-l-4" style={{ borderColor: reco.color }}>
                  <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{reco.flag}</span>
                      <div>
                        <p className="text-sm font-bold text-white">{reco.nom} — {reco.pays}</p>
                        <p className="text-xs text-gray-400">{reco.devise} · Cap. {reco.cap_usd_b}B$</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <AiSignalBadge label={reco.label} color={reco.color} score={reco.score} />
                      {reco.has_cache && (
                        <span className="text-xs text-green-500 bg-green-950/40 px-2 py-0.5 rounded-full border border-green-900/40">
                          Données temps réel
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Macro KPIs */}
                  <div className="grid grid-cols-3 gap-3 mb-3">
                    <div className="text-center p-2 rounded-lg bg-gray-900/60">
                      <p className="text-xs text-gray-500">Croissance PIB</p>
                      <p className="text-sm font-bold text-green-400">+{reco.macro.pib_growth}%</p>
                    </div>
                    <div className="text-center p-2 rounded-lg bg-gray-900/60">
                      <p className="text-xs text-gray-500">Inflation</p>
                      <p className={`text-sm font-bold ${reco.macro.inflation > 15 ? "text-red-400" : "text-yellow-300"}`}>
                        {reco.macro.inflation}%
                      </p>
                    </div>
                    <div className="text-center p-2 rounded-lg bg-gray-900/60">
                      <p className="text-xs text-gray-500 mb-1">Risque</p>
                      <RisqueBar niveau={reco.macro.risque} />
                    </div>
                  </div>

                  {/* Technical reasons */}
                  {reco.reasons.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-3">
                      {reco.reasons.map((r, i) => (
                        <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-300">{r}</span>
                      ))}
                    </div>
                  )}

                  {/* AI text */}
                  <div className="text-xs text-gray-300 leading-relaxed bg-gray-900/40 rounded-lg p-3">
                    {reco.ai_text.split("\n\n").map((para, i) => (
                      <p key={i} className={i > 0 ? "mt-2" : ""}
                        dangerouslySetInnerHTML={{
                          __html: para.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\*(.+?)\*/g, "<em>$1</em>")
                        }}
                      />
                    ))}
                  </div>

                  {/* Action buttons */}
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => { setSelSlug(reco.slug); setSubTab("sgis"); }}
                      className="text-xs px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
                    >
                      Voir les SGI →
                    </button>
                    <button
                      onClick={() => { setSelSlug(reco.slug); setSubTab("overview"); }}
                      className="text-xs px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
                    >
                      Fiche bourse →
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <p className="text-xs text-gray-600 text-center">
            Données macro : estimations 2024–2025 · Signaux techniques : yfinance (EZA/NGX/GSE/NSE/EGX) ·
            Avertissement : ceci n'est pas un conseil en investissement
          </p>
        </div>
      )}
    </div>
  );
}

// ── Tooltip styles ───────────────────────────────────────────

const TT = {
  contentStyle: { background: "#0f172a", border: "1px solid #374151", borderRadius: 8, fontSize: 11 },
  labelStyle:   { color: "#6b7280" },
};

// ── Sub-components ───────────────────────────────────────────

function XofPanel({ rates }) {
  if (!rates) return (
    <div className="card animate-pulse h-20" />
  );
  return (
    <div className="card bg-gradient-to-r from-blue-950/60 to-indigo-950/60 border border-blue-900/30 mb-4">
      <div className="flex flex-wrap gap-6 items-center">
        <div>
          <p className="text-xs text-gray-400 mb-0.5">EUR / XOF</p>
          <p className="text-xl font-bold text-white">655,957</p>
          <p className="text-xs text-blue-300">Parité fixe BCEAO depuis 1999 🔒</p>
        </div>
        <div className="w-px h-10 bg-gray-700 hidden sm:block" />
        <div>
          <p className="text-xs text-gray-400 mb-0.5">USD / XOF</p>
          <p className="text-xl font-bold text-yellow-300">{rates.usd_xof.toLocaleString("fr-FR")}</p>
          <p className="text-xs text-gray-500">EURUSD = {rates.eurusd}</p>
        </div>
        <div className="w-px h-10 bg-gray-700 hidden sm:block" />
        <div>
          <p className="text-xs text-gray-400 mb-0.5">CAD / XOF</p>
          <p className="text-xl font-bold text-green-300">{rates.cad_xof.toLocaleString("fr-FR")}</p>
          <p className="text-xs text-gray-500">USDCAD = {rates.usdcad}</p>
        </div>
        <div className="ml-auto text-right hidden sm:block">
          <p className="text-xs text-gray-500">EUR/XOF = 655,957 / EURUSD</p>
          <p className="text-xs text-gray-500">CAD/XOF = USD/XOF / USDCAD</p>
        </div>
      </div>
    </div>
  );
}

function SignalBadge({ label, color, score }) {
  if (!label) return null;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold"
      style={{ background: color + "22", color, border: `1px solid ${color}55` }}
    >
      {score > 0 ? "▲" : score < 0 ? "▼" : "–"} {label}
    </span>
  );
}

function AssetChart({ result, unit }) {
  if (!result) return null;
  const { data, last } = result;

  const fmtDate = (d) => {
    if (!d) return "";
    const parts = d.split("-");
    return `${parts[2]}/${parts[1]}`;
  };

  const fmtPrice = (v) => {
    if (v == null) return "";
    if (v >= 1000) return v.toLocaleString("fr-FR", { maximumFractionDigits: 0 });
    return v.toLocaleString("fr-FR", { maximumFractionDigits: 4 });
  };

  return (
    <div className="space-y-4">
      {/* Signal card */}
      <div className="flex flex-wrap items-center gap-3 p-3 rounded-xl bg-gray-900/60 border border-gray-800">
        <div>
          <p className="text-xs text-gray-400">Dernier cours</p>
          <p className="text-lg font-bold text-white">
            {fmtPrice(last.cours)} <span className="text-xs text-gray-400">{unit}</span>
          </p>
        </div>
        <div className="flex flex-col gap-1">
          <SignalBadge label={last.label} color={last.color} score={last.score} />
          <p className="text-xs text-gray-500">Score : {last.score > 0 ? "+" : ""}{last.score}</p>
        </div>
        <div className="ml-auto flex flex-wrap gap-1">
          {last.reasons?.map((r, i) => (
            <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-300">{r}</span>
          ))}
        </div>
      </div>

      {/* Price + MAs */}
      <div className="card">
        <p className="text-xs text-gray-400 mb-2">Prix · MA16 · MA19 · MA246 · MA361</p>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fill: "#6b7280", fontSize: 10 }} minTickGap={30} />
            <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} tickFormatter={fmtPrice} width={55} />
            <Tooltip {...TT} formatter={(v, name) => [fmtPrice(v), name]} labelFormatter={fmtDate} />
            <Area dataKey="cours" fill="#3b82f620" stroke="#3b82f6" strokeWidth={1.5} dot={false} name="Prix" />
            <Line dataKey="ma16"  stroke="#fbbf24" strokeWidth={1.2} dot={false} name="MA16"  connectNulls />
            <Line dataKey="ma19"  stroke="#f97316" strokeWidth={1.2} dot={false} name="MA19"  connectNulls />
            <Line dataKey="ma246" stroke="#a78bfa" strokeWidth={1.5} dot={false} name="MA246" connectNulls strokeDasharray="4 2" />
            <Line dataKey="ma361" stroke="#34d399" strokeWidth={1.5} dot={false} name="MA361" connectNulls strokeDasharray="4 2" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* RSI */}
      <div className="card">
        <p className="text-xs text-gray-400 mb-2">RSI (14)</p>
        <ResponsiveContainer width="100%" height={110}>
          <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fill: "#6b7280", fontSize: 10 }} minTickGap={30} />
            <YAxis domain={[0, 100]} tick={{ fill: "#6b7280", fontSize: 10 }} width={30} />
            <Tooltip {...TT} formatter={(v) => [v != null ? v.toFixed(1) : "—", "RSI"]} labelFormatter={fmtDate} />
            <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" />
            <ReferenceLine y={30} stroke="#22c55e" strokeDasharray="3 3" />
            <Line dataKey="rsi" stroke="#818cf8" strokeWidth={1.5} dot={false} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* MFI */}
      <div className="card">
        <p className="text-xs text-gray-400 mb-2">MFI (14)</p>
        <ResponsiveContainer width="100%" height={100}>
          <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="date" tickFormatter={fmtDate} tick={{ fill: "#6b7280", fontSize: 10 }} minTickGap={30} />
            <YAxis domain={[0, 100]} tick={{ fill: "#6b7280", fontSize: 10 }} width={30} />
            <Tooltip {...TT} formatter={(v) => [v != null ? v.toFixed(1) : "—", "MFI"]} labelFormatter={fmtDate} />
            <ReferenceLine y={80} stroke="#ef4444" strokeDasharray="3 3" />
            <ReferenceLine y={20} stroke="#22c55e" strokeDasharray="3 3" />
            <Area dataKey="mfi" fill="#0891b220" stroke="#0891b2" strokeWidth={1.5} dot={false} connectNulls />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ImpactTab({ tabKey }) {
  const info = IMPACT_BRVM[tabKey];
  if (!info) return null;
  return (
    <div className="space-y-4">
      <div className="card bg-gradient-to-r from-emerald-950/60 to-teal-950/60 border border-emerald-900/30">
        <h2 className="text-base font-bold text-white mb-1">🌍 {info.title}</h2>
        <p className="text-xs text-gray-400">Analyse de l'impact sur la Bourse Régionale des Valeurs Mobilières (BRVM)</p>
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        {info.items.map((item, i) => (
          <div key={i} className="card border-l-4 border-brand-500/60">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">{item.icon}</span>
              <h3 className="text-sm font-semibold text-white">{item.label}</h3>
            </div>
            <p className="text-xs text-gray-300 leading-relaxed">{item.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────

const PERIOD_OPTIONS = [
  { label: "30j", days: 30 },
  { label: "90j", days: 90 },
  { label: "180j", days: 180 },
  { label: "1an", days: 365 },
];

export default function MarchesInternationaux() {
  const { t } = useTranslation();
  const { plan } = useAuth();

  const [activeTab,    setActiveTab]    = useState("commodities");
  const [activeSub,    setActiveSub]    = useState("chart"); // "chart" | "impact"
  const [ticker,       setTicker]       = useState(CATEGORIES.commodities.assets[0].ticker);
  const [days,         setDays]         = useState(90);
  const [chartResult,  setChartResult]  = useState(null);
  const [loadingChart, setLoadingChart] = useState(false);
  const [xofRates,     setXofRates]     = useState(null);
  const [error,        setError]        = useState(null);

  const hasAccess = plan === "expert";

  // Fetch XOF rates once
  useEffect(() => {
    if (!hasAccess) return;
    apiGet("/intel/international/forex/xof")
      .then(setXofRates)
      .catch(() => {});
  }, [hasAccess]);

  // When tab changes → reset ticker to first asset of that tab
  useEffect(() => {
    const first = CATEGORIES[activeTab]?.assets[0]?.ticker;
    if (first) setTicker(first);
    setChartResult(null);
    setError(null);
  }, [activeTab]);

  // Fetch chart data whenever ticker or days change
  const fetchChart = useCallback(() => {
    if (!ticker || !hasAccess) return;
    setLoadingChart(true);
    setError(null);
    setChartResult(null);
    apiGet(`/intel/international/${encodeURIComponent(ticker)}?days=${days}`)
      .then(setChartResult)
      .catch((e) => setError(e?.message || "Erreur de chargement"))
      .finally(() => setLoadingChart(false));
  }, [ticker, days, hasAccess]);

  useEffect(() => { fetchChart(); }, [fetchChart]);

  // ── Plan gate ────────────────────────────────────────────────
  if (!hasAccess) {
    return (
      <div className="py-20 px-4 text-center">
        <p className="text-5xl mb-4">🌐</p>
        <h2 className="text-2xl font-bold text-white mb-2">Marchés Internationaux — Plan Expert</h2>
        <p className="text-gray-400 mb-2">Commodités · Indices · Forex/CFA · Crypto</p>
        <p className="text-gray-500 text-sm mb-6">
          Analyse technique (MA/RSI/MFI) sur 200+ marchés mondiaux + impact BRVM
        </p>
        <Link to="/pricing" className="btn-primary">Voir les offres →</Link>
      </div>
    );
  }

  const catInfo    = CATEGORIES[activeTab];
  const activeAsset = catInfo?.assets.find((a) => a.ticker === ticker);

  const MAIN_TABS = [
    ...Object.entries(CATEGORIES).map(([key, cat]) => ({ key, label: `${cat.icon} ${cat.label}` })),
    { key: "african", label: "🌍 Marchés Africains" },
  ];

  return (
    <div className="py-8 px-4">
      <div className="max-w-7xl mx-auto space-y-5">

        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-950 to-blue-950 border border-indigo-900/30 rounded-2xl px-6 py-5">
          <h1 className="text-2xl font-bold text-white">🌐 Marchés Internationaux</h1>
          <p className="text-gray-300 text-sm mt-1">
            Commodités · Indices · Forex/CFA · Crypto · Analyse technique temps réel (yfinance)
          </p>
        </div>

        {/* Main category tabs */}
        <div className="flex gap-1 border-b border-gray-800 overflow-x-auto pb-px">
          {MAIN_TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors -mb-px border-b-2 whitespace-nowrap ${
                activeTab === key
                  ? "border-brand-500 text-brand-400 bg-brand-500/5"
                  : "border-transparent text-gray-400 hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* African markets tab — full replacement */}
        {activeTab === "african" ? (
          <AfricanMarketsTab />
        ) : (
          <>
            {/* XOF panel on Forex tab */}
            {activeTab === "forex" && (
              <XofPanel rates={xofRates} />
            )}

            {/* Sub-tabs : Chart | Impact BRVM */}
            <div className="flex gap-2">
              {[
                { key: "chart",  label: "📈 Analyse technique" },
                { key: "impact", label: "🔗 Impact BRVM" },
              ].map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => setActiveSub(key)}
                  className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    activeSub === key
                      ? "bg-gray-800 text-white"
                      : "text-gray-400 hover:text-white hover:bg-gray-800/50"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {activeSub === "impact" ? (
              <ImpactTab tabKey={activeTab} />
            ) : (
              <>
                {/* Asset chips */}
                <div className="flex flex-wrap gap-2">
                  {catInfo?.assets.map((a) => (
                    <button
                      key={a.ticker}
                      onClick={() => setTicker(a.ticker)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${
                        ticker === a.ticker
                          ? "bg-brand-500 border-brand-500 text-white"
                          : "bg-gray-900 border-gray-700 text-gray-300 hover:border-gray-500"
                      }`}
                    >
                      <span>{a.icon}</span>
                      <span>{a.label}</span>
                      {a.unit && <span className="text-xs opacity-60">{a.unit}</span>}
                    </button>
                  ))}

                  {/* Period selector */}
                  <div className="ml-auto flex gap-1">
                    {PERIOD_OPTIONS.map(({ label, days: d }) => (
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
                </div>

                {/* Chart area */}
                {loadingChart ? (
                  <div className="space-y-4">
                    <div className="card h-12 animate-pulse" />
                    <div className="card h-52 animate-pulse" />
                    <div className="card h-28 animate-pulse" />
                    <div className="card h-24 animate-pulse" />
                  </div>
                ) : error ? (
                  <div className="card text-center py-10">
                    <p className="text-4xl mb-3">⚠️</p>
                    <p className="text-white font-medium mb-1">Données indisponibles</p>
                    <p className="text-gray-400 text-sm mb-4">{error}</p>
                    <button onClick={fetchChart} className="btn-secondary text-sm">
                      Réessayer
                    </button>
                  </div>
                ) : chartResult ? (
                  <AssetChart
                    result={chartResult}
                    unit={activeAsset?.unit || ""}
                  />
                ) : null}
              </>
            )}

            <p className="text-xs text-gray-600 text-center">
              Source : Yahoo Finance (yfinance) · Données différées de 15–20 min · EUR/XOF parité fixe BCEAO 1999
            </p>
            <ComplianceBanner variant="compact" />
          </>
        )}
      </div>
    </div>
  );
}
