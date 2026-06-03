import { useTranslation } from "react-i18next";

const PLAN_COLORS = {
  free:    "border-gray-700",
  starter: "border-blue-600",
  pro:     "border-brand-500",
  expert:  "border-gold-500",
};

const PLAN_BADGES = {
  free:    { label: "Free",    bg: "bg-gray-700",    text: "text-gray-100" },
  starter: { label: "Starter", bg: "bg-blue-700",    text: "text-blue-100" },
  pro:     { label: "Pro",     bg: "bg-brand-700",   text: "text-green-100" },
  expert:  { label: "Expert",  bg: "bg-yellow-700",  text: "text-yellow-100" },
};

export default function PlanCard({ plan, price, features = [], popular = false, ctaHref, ctaLabel }) {
  const { t } = useTranslation();
  const badge  = PLAN_BADGES[plan] || PLAN_BADGES.free;
  const border = PLAN_COLORS[plan] || PLAN_COLORS.free;

  return (
    <div
      className={`relative bg-gray-900 border-2 ${border} rounded-2xl p-6 flex flex-col gap-5
                  transition-all duration-200 hover:-translate-y-1 hover:shadow-xl hover:shadow-black/30
                  ${popular ? "ring-2 ring-brand-500 ring-offset-2 ring-offset-gray-950" : ""}`}
    >
      {popular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="bg-brand-500 text-white text-xs font-bold px-4 py-1 rounded-full">
            {t("most_popular")}
          </span>
        </div>
      )}

      <div>
        <span className={`badge ${badge.bg} ${badge.text} mb-3`}>{badge.label}</span>
        <div className="flex items-end gap-1">
          <span className="text-3xl font-bold text-white">{price}</span>
          {price !== "$0" && <span className="text-gray-400 text-sm mb-1">/mo</span>}
        </div>
      </div>

      <ul className="flex flex-col gap-2 flex-1">
        {features.map((f, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
            <span className="text-brand-400 mt-0.5 flex-shrink-0">✓</span>
            {f}
          </li>
        ))}
      </ul>

      <a
        href={ctaHref || "#"}
        className={`btn-primary w-full text-center text-sm
          ${plan === "free" ? "!bg-gray-700 hover:!bg-gray-600" : ""}`}
      >
        {ctaLabel || t("free_trial_btn")}
      </a>
    </div>
  );
}
