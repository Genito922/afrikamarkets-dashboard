/**
 * TradingViewMiniChart — Widget Mini Symbol Overview (embed léger)
 * Chaque instance est autonome : pas de global TradingView,
 * pas de déduplication requise. Cleanup strict sur symbol/height change.
 */
import { useEffect, useRef, memo } from "react";

/**
 * @param {string} symbol   — ex: "OANDA:XAUUSD", "INDEX:DXY", "FX:EURUSD"
 * @param {string} title    — Titre affiché au-dessus du widget
 * @param {string} dateRange — "1D"|"1M"|"3M"|"12M" (défaut 12M)
 * @param {number} height   — hauteur px du widget (défaut 138)
 */
function TradingViewMiniChart({ symbol, title, dateRange = "12M", height = 138 }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Réinitialisation propre (destroy iframe précédente si hot-reload)
    container.innerHTML = "";

    // Structure standard TradingView embed-widget
    const widgetDiv = document.createElement("div");
    widgetDiv.className = "tradingview-widget-container__widget";
    container.appendChild(widgetDiv);

    const script = document.createElement("script");
    script.type  = "text/javascript";
    script.src   = "https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js";
    script.async = true;
    // Config injectée en tant que contenu du script — pattern officiel TradingView
    script.innerHTML = JSON.stringify({
      symbol,
      width:       "100%",
      height,
      locale:      "fr",
      dateRange,
      colorTheme:  "dark",
      isTransparent: true,
      autosize:    false,
      largeChartUrl: "",
    });
    container.appendChild(script);

    return () => {
      if (container) container.innerHTML = "";
    };
  }, [symbol, height, dateRange]);

  return (
    <div className="rounded-xl bg-slate-900/40 border border-slate-800/70 p-2.5 mb-3 last:mb-0">
      {title && (
        <p className="text-xs font-semibold text-slate-400 mb-1.5 px-0.5 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-500 inline-block" />
          {title}
        </p>
      )}
      <div ref={containerRef} style={{ minHeight: height }} />
    </div>
  );
}

export default memo(TradingViewMiniChart);
