/**
 * MacroSidebar — Barre latérale "Terminal Bloomberg"
 * Empile des MiniCharts TradingView pour les corrélations macro globales.
 * Utilisée dans TitreDetail (BRVM) et CryptoAnalyse.
 */
import TradingViewMiniChart from "./TradingViewMiniChart";

// ── Widgets communs (crypto + BRVM) ──────────────────────────
const MACRO_WIDGETS = [
  {
    symbol:    "OANDA:XAUUSD",
    title:     "Or / USD — Hedge Macro",
    dateRange: "3M",
  },
  {
    symbol:    "INDEX:DXY",
    title:     "US Dollar Index (DXY)",
    dateRange: "3M",
  },
  {
    symbol:    "FX:EURUSD",
    title:     "EUR / USD — Parité XOF",
    dateRange: "3M",
  },
];

// Widget additionnel pour les actifs BRVM (XOF arrimé à l'EUR)
const BRVM_WIDGET = {
  symbol:    "FX_IDC:USDXOF",
  title:     "USD / XOF — Taux de change",
  dateRange: "3M",
};

// Widget additionnel pour le contexte crypto
const CRYPTO_WIDGET = {
  symbol:    "BINANCE:BTCUSDT",
  title:     "BTC — Référence marché",
  dateRange: "1M",
};

/**
 * @param {"brvm"|"crypto"|"default"} context  — adapte les widgets contextuels
 * @param {string}                   currentSymbol — pour exclure le doublon BTC en mode crypto
 */
export default function MacroSidebar({ context = "default", currentSymbol = null }) {
  const extra =
    context === "brvm"   ? BRVM_WIDGET :
    context === "crypto" ? (currentSymbol !== "BINANCE:BTCUSDT" ? CRYPTO_WIDGET : null) :
    null;

  return (
    <div className="sticky top-4">
      {/* En-tête sidebar */}
      <div className="flex items-center gap-2 mb-4 px-0.5">
        <div className="w-0.5 h-4 bg-gradient-to-b from-blue-500 to-purple-500 rounded-full" />
        <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">
          Corrélations Macro
        </p>
      </div>

      {/* Widgets communs */}
      {MACRO_WIDGETS.map((w) => (
        <TradingViewMiniChart
          key={w.symbol}
          symbol={w.symbol}
          title={w.title}
          dateRange={w.dateRange}
          height={130}
        />
      ))}

      {/* Widget contextuel */}
      {extra && (
        <TradingViewMiniChart
          symbol={extra.symbol}
          title={extra.title}
          dateRange={extra.dateRange}
          height={130}
        />
      )}

      {/* Note pédagogique */}
      <div className="mt-4 p-3 rounded-xl bg-gray-900/40 border border-gray-800/50">
        <p className="text-xs text-gray-500 leading-relaxed">
          {context === "brvm"
            ? "Le XOF est arrimé à l'EUR — la parité EUR/USD et le DXY influencent directement la compétitivité des exportations BRVM."
            : "Surveillez DXY et Or pour détecter les phases Risk-On / Risk-Off affectant les cryptos."}
        </p>
      </div>
    </div>
  );
}
