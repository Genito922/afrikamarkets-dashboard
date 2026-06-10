/**
 * TradingViewWidget — Graphique avancé TradingView
 * API : tv.js + new window.TradingView.widget() — instance explicite,
 * nettoyage propre au démontage, script chargé une seule fois (data-tvjs).
 *
 * Attribution obligatoire (widget gratuit) : lien "Powered by TradingView" visible.
 */
import { useEffect, useRef, memo } from "react";

// ── Mapping noms d'études ──────────────────────────────────────
// embed-widget → tv.js widget API
const STUDY_MAP = {
  "STD;RSI":             "RSI@tv-basicstudies",
  "STD;MACD":            "MACD@tv-basicstudies",
  "STD;Bollinger_Bands": "BB@tv-basicstudies",
  "STD;Volume":          "Volume@tv-basicstudies",
};
const toTvStudy = (s) => STUDY_MAP[s] ?? s;

// ── Exports utilisés dans TitreDetail.jsx + CryptoAnalyse.jsx ─

export const TV_INTERVAL = {
  7:   "60",   // 1h
  30:  "D",    // Journalier
  90:  "D",
  180: "W",    // Hebdomadaire
  365: "W",
};

export const TV_CRYPTO = {
  "BTC-USD":  "BINANCE:BTCUSDT",
  "ETH-USD":  "BINANCE:ETHUSDT",
  "BNB-USD":  "BINANCE:BNBUSDT",
  "SOL-USD":  "BINANCE:SOLUSDT",
  "XRP-USD":  "BINANCE:XRPUSDT",
  "ADA-USD":  "BINANCE:ADAUSDT",
  "AVAX-USD": "BINANCE:AVAXUSDT",
  "DOGE-USD": "BINANCE:DOGEUSDT",
  "LINK-USD": "BINANCE:LINKUSDT",
  "DOT-USD":  "BINANCE:DOTUSDT",
};

export const BRVM_ON_TV = new Set([
  "SNTS","SGBC","ETIT","BICC","ORAC","NTLC","SIVC","UNXC","BOAS","BOABF",
  "COBI","SAFC","SLBC","TTLS","PALM","SOGC","SPHC","CFAC","CABC","ECOC",
  "SEMC","STAC","FTSC","BMCI","NEIM","ORDI","SDCC","SDCI",
]);

// ── Composant ─────────────────────────────────────────────────

/**
 * @param {string}           symbol    — "BINANCE:BTCUSDT" | "BRVM:SNTS"
 * @param {string}           interval  — "1"|"5"|"15"|"60"|"240"|"D"|"W"
 * @param {"dark"|"light"}   theme
 * @param {number}           height    — hauteur totale px (défaut 520)
 * @param {string[]}         studies   — clés STD; ou identifiants tv-basicstudies
 */
function TradingViewWidget({
  symbol   = "BINANCE:BTCUSDT",
  interval = "D",
  theme    = "dark",
  height   = 520,
  studies  = ["STD;RSI", "STD;MACD"],
}) {
  const containerRef = useRef(null);
  // ID stable pour toute la durée de vie du composant
  const idRef = useRef(`tv_${Math.random().toString(36).slice(2, 9)}`);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Réinitialise le container (détruit l'iframe précédente si elle existe)
    container.innerHTML = "";

    // Div cible identifiée par ID stable
    const divId = idRef.current;
    const chartDiv = document.createElement("div");
    chartDiv.id    = divId;
    chartDiv.style.cssText = `height:${height - 24}px;width:100%`;
    container.appendChild(chartDiv);

    let pollId = null;

    function createWidget() {
      // Double-check : div encore dans le DOM + library disponible
      if (!document.getElementById(divId)) return;
      if (typeof window.TradingView === "undefined") return;

      new window.TradingView.widget({
        autosize:            true,
        symbol,
        interval,
        timezone:            "Africa/Abidjan",
        theme,
        style:               "1",
        locale:              "fr",
        toolbar_bg:          theme === "dark" ? "#0f172a" : "#f8fafc",
        enable_publishing:   false,
        hide_side_toolbar:   false,
        allow_symbol_change: true,
        studies:             studies.map(toTvStudy),
        container_id:        divId,
      });
    }

    if (typeof window.TradingView !== "undefined") {
      // Library déjà chargée (rendu suivant)
      createWidget();
    } else if (document.querySelector("script[data-tvjs]")) {
      // Script en cours de chargement — attente par polling
      pollId = setInterval(() => {
        if (typeof window.TradingView !== "undefined") {
          clearInterval(pollId);
          pollId = null;
          createWidget();
        }
      }, 50);
    } else {
      // Premier rendu — chargement unique du script
      const script = document.createElement("script");
      script.src   = "https://s3.tradingview.com/tv.js";
      script.async = true;
      script.setAttribute("data-tvjs", "1");   // marqueur déduplication
      script.onload = createWidget;
      document.head.appendChild(script);
    }

    return () => {
      // Nettoyage strict : interval + iframe TradingView
      if (pollId) clearInterval(pollId);
      if (container) container.innerHTML = "";
    };
  }, [symbol, interval, theme, height]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{ width: "100%", height }}>
      <div ref={containerRef} style={{ height: height - 24, width: "100%" }} />
      {/* Attribution obligatoire — ne pas supprimer */}
      <div style={{
        height: 24,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 11,
        color: "#475569",
        gap: 4,
      }}>
        Graphiques propulsés par{" "}
        <a
          href="https://www.tradingview.com/"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: "#2962ff", textDecoration: "none", fontWeight: 600 }}
        >
          TradingView
        </a>
      </div>
    </div>
  );
}

export default memo(TradingViewWidget);
