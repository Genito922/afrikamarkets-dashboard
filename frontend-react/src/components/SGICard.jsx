import { useTranslation } from "react-i18next";

const SCORE_COLOR = (score) => {
  if (score >= 8.5) return "text-brand-400";
  if (score >= 7.0) return "text-yellow-400";
  return "text-red-400";
};

function ScoreBar({ value }) {
  return (
    <div className="w-full bg-gray-800 rounded-full h-1.5">
      <div
        className="h-1.5 rounded-full bg-brand-500 transition-all"
        style={{ width: `${value * 10}%` }}
      />
    </div>
  );
}

export default function SGICard({ sgi, rank, profileScore }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;

  const strengths  = lang === "fr" ? sgi.strengths_fr : sgi.strengths_en;
  const weaknesses = lang === "fr" ? sgi.weaknesses_fr : sgi.weaknesses_en;

  const medals = ["🥇", "🥈", "🥉"];
  const medal  = medals[rank - 1] || `#${rank}`;

  return (
    <div className="card flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">{medal}</span>
            <h3 className="font-semibold text-white text-lg">{sgi.nom}</h3>
          </div>
          <p className="text-sm text-gray-400 mt-0.5">{sgi.pays} · {t("sgi_filled")} {sgi.founded}</p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className={`text-2xl font-bold ${SCORE_COLOR(profileScore ?? sgi.score_global)}`}>
            {(profileScore ?? sgi.score_global).toFixed(1)}
          </p>
          <p className="text-xs text-gray-500">/10</p>
        </div>
      </div>

      {/* Score bar */}
      <ScoreBar value={profileScore ?? sgi.score_global} />

      {/* Chips */}
      <div className="flex flex-wrap gap-2">
        {sgi.ouverture_en_ligne && (
          <span className="badge bg-green-900/50 text-green-300 text-xs">
            ✅ {t("sgi_ouverture_ligne")}
          </span>
        )}
        {sgi.app_mobile && (
          <span className="badge bg-blue-900/50 text-blue-300 text-xs">
            📱 {t("sgi_app_mobile")}
          </span>
        )}
        {sgi.presence_diaspora && (
          <span className="badge bg-purple-900/50 text-purple-300 text-xs">
            ✈️ {t("sgi_diaspora")}
          </span>
        )}
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="bg-gray-800/50 rounded-lg p-2">
          <p className="text-gray-400 text-xs">{t("sgi_courtage")}</p>
          <p className="font-semibold text-white">{sgi.courtage}</p>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-2">
          <p className="text-gray-400 text-xs">{t("sgi_depot_min")}</p>
          <p className="font-semibold text-white">{sgi.depot_min.toLocaleString()} FCFA</p>
        </div>
      </div>

      {/* Strengths / Weaknesses */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs font-medium text-gray-400 mb-1">{t("sgi_strengths")}</p>
          <ul className="space-y-0.5">
            {strengths.slice(0, 2).map((s, i) => (
              <li key={i} className="text-xs text-gray-300">✅ {s}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs font-medium text-gray-400 mb-1">{t("sgi_weaknesses")}</p>
          <ul className="space-y-0.5">
            {weaknesses.slice(0, 2).map((w, i) => (
              <li key={i} className="text-xs text-gray-300">⚠️ {w}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* CTA */}
      <a
        href={sgi.url}
        target="_blank"
        rel="noopener noreferrer"
        className="btn-secondary text-center text-sm mt-auto"
      >
        {t("sgi_open_account")} →
      </a>
    </div>
  );
}
