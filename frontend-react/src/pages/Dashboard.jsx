import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

const MOCK_STOCKS = [
  { ticker: "SNTS",  name: "SONATEL",       price: 15_200, change: +2.3,  mkt_cap: "1.2T" },
  { ticker: "ORAC",  name: "ORANGE CI",     price: 11_800, change: -0.8,  mkt_cap: "895B" },
  { ticker: "SGBC",  name: "SGB CI",        price: 5_450,  change: +1.1,  mkt_cap: "412B" },
  { ticker: "BICC",  name: "BICICI",        price: 6_100,  change: +0.4,  mkt_cap: "385B" },
  { ticker: "ETIT",  name: "Ecobank TG",    price: 22,     change: -1.2,  mkt_cap: "308B" },
  { ticker: "BOAB",  name: "BOA Bénin",     price: 3_950,  change: +3.1,  mkt_cap: "278B" },
];

export default function Dashboard() {
  const { t } = useTranslation();

  return (
    <div className="py-10 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Banner */}
        <div className="bg-brand-500/10 border border-brand-500/20 rounded-2xl px-6 py-4 mb-8 flex items-center justify-between">
          <div>
            <p className="font-semibold text-white">
              🔒 {t("plan_required_pro", "Accès complet réservé aux abonnés Pro")}
            </p>
            <p className="text-sm text-gray-400 mt-0.5">{t("sub_subtitle")}</p>
          </div>
          <Link to="/pricing" className="btn-primary text-sm flex-shrink-0">
            {t("free_trial_btn")} →
          </Link>
        </div>

        {/* Market overview */}
        <div className="mb-8">
          <h2 className="text-xl font-bold text-white mb-4">{t("market_title", "Marché BRVM")}</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400">
                  <th className="text-left py-3 px-4">Ticker</th>
                  <th className="text-left py-3 px-4">{t("stock_label", "Titre")}</th>
                  <th className="text-right py-3 px-4">{t("price_col", "Cours FCFA")}</th>
                  <th className="text-right py-3 px-4">Var.</th>
                  <th className="text-right py-3 px-4">Mkt Cap</th>
                </tr>
              </thead>
              <tbody>
                {MOCK_STOCKS.map((s) => (
                  <tr key={s.ticker} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                    <td className="py-3 px-4 font-mono font-semibold text-brand-400">{s.ticker}</td>
                    <td className="py-3 px-4 text-white">{s.name}</td>
                    <td className="py-3 px-4 text-right text-white">{s.price.toLocaleString()}</td>
                    <td className={`py-3 px-4 text-right font-medium ${s.change >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {s.change >= 0 ? "+" : ""}{s.change}%
                    </td>
                    <td className="py-3 px-4 text-right text-gray-400">{s.mkt_cap}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Quick links */}
        <div className="grid sm:grid-cols-3 gap-4">
          <Link to="/sgi" className="card hover:-translate-y-1 transition-transform">
            <div className="text-3xl mb-2">🏦</div>
            <h3 className="font-semibold text-white">{t("sgi_module1")}</h3>
            <p className="text-sm text-gray-400 mt-1">{t("sgi_subtitle")}</p>
          </Link>
          <Link to="/sgi" className="card hover:-translate-y-1 transition-transform">
            <div className="text-3xl mb-2">🤖</div>
            <h3 className="font-semibold text-white">{t("sgi_module2")}</h3>
            <p className="text-sm text-gray-400 mt-1">{t("sgi_get_reco")}</p>
          </Link>
          <Link to="/pricing" className="card hover:-translate-y-1 transition-transform border-gold-500/30">
            <div className="text-3xl mb-2">⭐</div>
            <h3 className="font-semibold text-white">{t("sub_title")}</h3>
            <p className="text-sm text-gray-400 mt-1">{t("most_popular")}</p>
          </Link>
        </div>
      </div>
    </div>
  );
}
