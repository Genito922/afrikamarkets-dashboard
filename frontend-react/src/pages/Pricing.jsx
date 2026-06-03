import { useTranslation } from "react-i18next";
import PlanCard from "../components/PlanCard";

const LS = {
  starter:        "https://afrika-markets-stock.lemonsqueezy.com/checkout/buy/737c9823-4248-488a-a736-e22820f23e18",
  pro:            "https://afrika-markets-stock.lemonsqueezy.com/checkout/buy/ae008a73-cf01-41e6-b602-270c9a943409",
  expert:         "https://afrika-markets-stock.lemonsqueezy.com/checkout/buy/12ca2955-7928-4a10-8266-59cfbcf13078",
  expert_premium: "https://afrika-markets-stock.lemonsqueezy.com/checkout/buy/d7672acb-6acb-40f0-b5eb-a4022f7fc7c0",
};

const PLANS = [
  {
    key: "starter",
    price: "$29.99",
    ctaHref: LS.starter,
    features: {
      fr: ["Dashboard BRVM complet", "Tous les indices & secteurs", "Top 10 mouvements journaliers", "War Room géopolitique (basique)", "Support par email"],
      en: ["Full BRVM dashboard", "All indices & sectors", "Daily top 10 movers", "War Room (basic)", "Email support"],
      es: ["Dashboard BRVM completo", "Todos los índices y sectores", "Top 10 movimientos diarios", "War Room (básico)", "Soporte por email"],
      pt: ["Dashboard BRVM completo", "Todos os índices e setores", "Top 10 movimentos diários", "War Room (básico)", "Suporte por email"],
      zh: ["完整BRVM仪表板", "所有指数和行业", "每日前10大变动", "地缘政治战情室（基础）", "邮件支持"],
      ar: ["لوحة BRVM الكاملة", "جميع المؤشرات والقطاعات", "أفضل 10 تحركات يومية", "غرفة الحرب (أساسي)", "دعم البريد الإلكتروني"],
    },
  },
  {
    key: "pro",
    price: "$74.99",
    popular: true,
    ctaHref: LS.pro,
    features: {
      fr: ["Tout Starter +", "Scoring & classement IA", "War Room complet", "Simulateur de portefeuille", "Alertes prix & risques", "SGI & OPCVM Intelligence Center", "Brief intelligence hebdomadaire"],
      en: ["All Starter +", "AI Scoring & ranking", "Full War Room access", "Portfolio Simulator", "Price & risk alerts", "SGI & OPCVM Intelligence Center", "Weekly intelligence brief"],
      es: ["Todo Starter +", "Scoring IA & ranking", "War Room completo", "Simulador de cartera", "Alertas precio & riesgo", "SGI & OPCVM Intelligence Center", "Brief semanal de inteligencia"],
      pt: ["Tudo Starter +", "Scoring IA & ranking", "War Room completo", "Simulador de carteira", "Alertas preço & risco", "SGI & OPCVM Intelligence Center", "Brief semanal de inteligência"],
      zh: ["Starter所有功能 +", "AI评分与排名", "完整战情室", "投资组合模拟器", "价格与风险提醒", "SGI & OPCVM情报中心", "每周情报简报"],
      ar: ["كل مزايا Starter +", "تسجيل وترتيب AI", "غرفة الحرب الكاملة", "محاكي المحفظة", "تنبيهات السعر والمخاطر", "مركز ذكاء SGI & OPCVM", "نشرة استخباراتية أسبوعية"],
    },
  },
  {
    key: "expert",
    price: "$199.99",
    ctaHref: LS.expert,
    features: {
      fr: ["Tout Pro +", "Briefing 1-on-1 mensuel", "Watchlists personnalisées", "Export données CSV/PDF", "Support prioritaire", "Rapports PDF clients", "Accès anticipé aux nouvelles fonctionnalités"],
      en: ["All Pro +", "Monthly 1-on-1 briefing", "Custom watchlists", "CSV/PDF data export", "Priority support", "Client PDF reports", "Early access to new features"],
      es: ["Todo Pro +", "Briefing 1-on-1 mensual", "Watchlists personalizadas", "Export datos CSV/PDF", "Soporte prioritario", "Informes PDF clientes", "Acceso anticipado a nuevas funciones"],
      pt: ["Tudo Pro +", "Briefing 1-on-1 mensal", "Watchlists personalizadas", "Export dados CSV/PDF", "Suporte prioritário", "Relatórios PDF clientes", "Acesso antecipado a novas funcionalidades"],
      zh: ["Pro所有功能 +", "每月1对1简报", "自定义关注列表", "CSV/PDF数据导出", "优先支持", "客户PDF报告", "新功能抢先体验"],
      ar: ["كل مزايا Pro +", "إحاطة شهرية 1-على-1", "قوائم مراقبة مخصصة", "تصدير بيانات CSV/PDF", "دعم ذو أولوية", "تقارير PDF للعملاء", "وصول مبكر للميزات الجديدة"],
    },
  },
  {
    key: "expert_premium",
    price: "$299.99",
    ctaHref: LS.expert_premium,
    features: {
      fr: ["Tout Expert +", "Accès API données brutes", "Modèles de valorisation exclusifs", "Briefings illimités", "Onboarding dédié", "SLA prioritaire 24/7", "Co-branding rapports clients"],
      en: ["All Expert +", "Raw data API access", "Exclusive valuation models", "Unlimited briefings", "Dedicated onboarding", "Priority SLA 24/7", "Client report co-branding"],
      es: ["Todo Expert +", "API datos brutos", "Modelos de valoración exclusivos", "Briefings ilimitados", "Onboarding dedicado", "SLA prioritario 24/7", "Co-branding informes clientes"],
      pt: ["Tudo Expert +", "API dados brutos", "Modelos de avaliação exclusivos", "Briefings ilimitados", "Onboarding dedicado", "SLA prioritário 24/7", "Co-branding relatórios clientes"],
      zh: ["Expert所有功能 +", "原始数据API访问", "独家估值模型", "无限简报", "专属入门指导", "24/7优先SLA", "客户报告联合品牌"],
      ar: ["كل مزايا Expert +", "واجهة API للبيانات الخام", "نماذج تقييم حصرية", "إحاطات غير محدودة", "إعداد مخصص", "SLA ذو أولوية 24/7", "تقارير عملاء مشتركة العلامة"],
    },
  },
];

const PLAN_COLORS = {
  starter:        "border-blue-600",
  pro:            "border-brand-500",
  expert:         "border-yellow-600",
  expert_premium: "border-purple-500",
};

const PLAN_BADGES = {
  starter:        { label: "Starter",        bg: "bg-blue-700",   text: "text-blue-100" },
  pro:            { label: "Pro",             bg: "bg-brand-700",  text: "text-green-100" },
  expert:         { label: "Expert",          bg: "bg-yellow-700", text: "text-yellow-100" },
  expert_premium: { label: "Expert Premium",  bg: "bg-purple-700", text: "text-purple-100" },
};

function PricingCard({ plan, popular = false }) {
  const { t } = useTranslation();
  const lang = useTranslation().i18n.language;
  const badge  = PLAN_BADGES[plan.key];
  const border = PLAN_COLORS[plan.key];
  const features = plan.features[lang] || plan.features.en;

  return (
    <div
      className={`relative bg-gray-900 border-2 ${border} rounded-2xl p-6 flex flex-col gap-5
                  transition-all duration-200 hover:-translate-y-1 hover:shadow-xl hover:shadow-black/30
                  ${popular ? "ring-2 ring-brand-500 ring-offset-2 ring-offset-gray-950" : ""}`}
    >
      {popular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="bg-brand-500 text-white text-xs font-bold px-4 py-1 rounded-full whitespace-nowrap">
            {t("most_popular")}
          </span>
        </div>
      )}

      <div>
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium mb-3 ${badge.bg} ${badge.text}`}>
          {badge.label}
        </span>
        <div className="flex items-end gap-1">
          <span className="text-3xl font-bold text-white">{plan.price}</span>
          <span className="text-gray-400 text-sm mb-1">/mo</span>
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
        href={plan.ctaHref}
        target="_blank"
        rel="noopener noreferrer"
        className={`inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold
                    text-white text-sm transition-all duration-200 w-full text-center
                    ${popular
                      ? "bg-brand-500 hover:bg-brand-400"
                      : plan.key === "expert_premium"
                        ? "bg-purple-600 hover:bg-purple-500"
                        : "bg-gray-700 hover:bg-gray-600"}`}
      >
        {t("free_trial_btn")} →
      </a>
    </div>
  );
}

export default function Pricing() {
  const { t } = useTranslation();

  return (
    <div className="py-16 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">{t("sub_title")}</h1>
          <p className="text-gray-400 text-lg">{t("sub_subtitle")}</p>
          <p className="text-sm text-gray-500 mt-3">{t("legal_note")}</p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {PLANS.map((plan) => (
            <PricingCard key={plan.key} plan={plan} popular={plan.popular} />
          ))}
        </div>
      </div>
    </div>
  );
}
