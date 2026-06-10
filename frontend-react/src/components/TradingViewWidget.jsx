/**
 * TradingViewWidget — Graphique avancé TradingView
 * Intégration via le widget embed officiel (gratuit, attribution obligatoire).
 * Source : https://www.tradingview.com/widget/advanced-chart/
 *
 * Règles d'attribution : le lien "Powered by TradingView" doit rester visible
 * et l'accès au widget ne doit pas être bloqué derrière un paywall exclusif.
 */
import { useEffect, useRef, memo } from "react";

// ── Mapping intervalle jours → code TradingView ────────────────
export const TV_INTERVAL = {
  7:   "60",    // 1h
  30:  "D",     // Journalier
  90:  "D",
  180: "W",     // Hebdomadaire
  365: "W",
};

// ── Mapping tickers yfinance → symboles TradingView ────────────
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

// Tickers BRVM connus sur TradingView (préfixe BRVM:)
export const BRVM_ON_TV = new Set([
  "SNTS","SGBC","ETIT","BICC","ORAC","NTLC","SIVC","UNXC","BOAS","BOABF",
  "COBI","SAFC","SLBC","TTLS","PALM","SOGC","SPHC","CFAC","CABC","ECOC",
  "SEMC","STAC","FTSC","BMCI","NEIM","ORDI","SDCC","SDCI",
]);

/**
 * @param {string}   symbol    — Symbole TradingView (ex: "BINANCE:BTCUSDT", "BRVM:SNTS")
 * @param {string}   interval  — "1","5","15","30","60","240","D","W","M"
 * @param {"dark"|"light"} theme
 * @param {number}   height    — Hauteur totale en px (défaut 520)
 * @param {string[]} studies   — Indicateurs pré-chargés
 */
function TradingViewWidget({
  symbol   = "BINANCE:BTCUSDT",
  interval = "D",
  theme    = "dark",
  height   = 520,
  studies  = ["STD;RSI", "STD;MACD"],
}) {
  const container = useRef(null);

  useEffect(() => {
    if (!container.current) return;

    // Réinitialise le container
    container.current.innerHTML = `
      <div
        class="tradingview-widget-container__widget"
        style="height:${height - 24}px;width:100%"
      ></div>
    `;

    const script = document.createElement("script");
    script.src   = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type  = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize:        true,
      symbol,
      interval,
      timezone:        "Africa/Abidjan",
      theme,
      style:           "1",
      locale:          "fr",
      backgroundColor: theme === "dark" ? "#0f172a" : "#ffffff",
      gridColor:       theme === "dark" ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.06)",
      hide_top_toolbar: false,
      hide_legend:     false,
      save_image:      true,
      calendar:        false,
      hide_volume:     false,
      support_host:    "https://www.tradingview.com",
      studies,
    });

    container.current.appendChild(script);

    return () => {
      if (container.current) container.current.innerHTML = "";
    };
  }, [symbol, interval, theme, height]);

  return (
    <div style={{ width: "100%", height }}>
      {/* Container widget — TradingView détecte sa div sœur automatiquement */}
      <div
        className="tradingview-widget-container"
        ref={container}
        style={{ height: height - 24, width: "100%" }}
      />
      {/* Attribution obligatoire */}
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
