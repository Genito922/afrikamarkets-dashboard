import { useTranslation } from "react-i18next";
import PlanCard from "../components/PlanCard";

const PLANS = [
  {
    key: "free",
    price: "$0",
    ctaKey: "free_trial_btn",
    features: {
      fr: ["Cours BRVM en temps réel", "Analyse 3 titres/jour", "Indicateurs de base (MA, RSI)", "Communauté Discord"],
      en: ["Real-time BRVM quotes", "3 stocks/day analysis", "Basic indicators (MA, RSI)", "Discord community"],
      es: ["Cotizaciones BRVM en tiempo real", "Análisis 3 acciones/día", "Indicadores básicos", "Comunidad Discord"],
      pt: ["Cotações BRVM tempo real", "Análise 3 ações/dia", "Indicadores básicos", "Comunidade Discord"],
      zh: ["实时BRVM行情", "每日分析3只股票", "基础指标", "Discord社区"],
      ar: ["أسعار BRVM الفورية", "تحليل 3 أسهم/يوم", "مؤشرات أساسية", "مجتمع Discord"],
    },
  },
  {
    key: "starter",
    price: "$9",
    ctaKey: "free_trial_btn",
    features: {
      fr: ["Titres illimités", "Portefeuille simulateur", "Analyse de risque", "Alertes par email (5/j)"],
      en: ["Unlimited stocks", "Portfolio simulator", "Risk analysis", "Email alerts (5/day)"],
      es: ["Acciones ilimitadas", "Simulador de cartera", "Análisis de riesgo", "Alertas por email"],
      pt: ["Ações ilimitadas", "Simulador de carteira", "Análise de risco", "Alertas por e-mail"],
      zh: ["无限股票", "投资组合模拟器", "风险分析", "邮件提醒"],
      ar: ["أسهم غير محدودة", "محاكي المحفظة", "تحليل المخاطر", "تنبيهات البريد"],
    },
  },
  {
    key: "pro",
    price: "$29",
    popular: true,
    ctaKey: "free_trial_btn",
    features: {
      fr: ["Tout Starter +", "SGI & OPCVM Intelligence Center", "Recommandation IA personnalisée", "Matching investisseur complet", "Screener OPCVM avancé", "Alertes illimitées", "Support prioritaire"],
      en: ["Everything in Starter +", "SGI & OPCVM Intelligence Center", "Personalised AI recommendation", "Full investor matching", "Advanced OPCVM screener", "Unlimited alerts", "Priority support"],
      es: ["Todo Starter +", "SGI & OPCVM Intelligence Center", "Recomendación IA personalizada", "Matching inversor completo", "Screener OPCVM avanzado", "Alertas ilimitadas", "Soporte prioritario"],
      pt: ["Tudo do Starter +", "SGI & OPCVM Intelligence Center", "Recomendação IA personalizada", "Matching investidor completo", "Screener OPCVM avançado", "Alertas ilimitados", "Suporte prioritário"],
      zh: ["Starter所有功能 +", "SGI & OPCVM情报中心", "个性化AI推荐", "完整投资者匹配", "高级OPCVM筛选", "无限提醒", "优先支持"],
      ar: ["كل مزايا Starter +", "مركز ذكاء SGI & OPCVM", "توصية AI شخصية", "مطابقة المستثمر الكاملة", "فلتر OPCVM متقدم", "تنبيهات غير محدودة", "دعم ذو أولوية"],
    },
  },
  {
    key: "expert",
    price: "$79",
    ctaKey: "free_trial_btn",
    features: {
      fr: ["Tout Pro +", "API accès données brutes", "Rapports PDF mensuels", "Accès bêta fonctionnalités", "Account manager dédié", "Webinaires exclusifs"],
      en: ["Everything in Pro +", "Raw data API access", "Monthly PDF reports", "Beta feature access", "Dedicated account manager", "Exclusive webinars"],
      es: ["Todo Pro +", "API datos brutos", "Informes PDF mensuales", "Acceso beta", "Account manager dedicado", "Webinars exclusivos"],
      pt: ["Tudo do Pro +", "API dados brutos", "Relatórios PDF mensais", "Acesso beta", "Account manager dedicado", "Webinars exclusivos"],
      zh: ["Pro所有功能 +", "原始数据API", "每月PDF报告", "Beta功能访问", "专属客户经理", "独家网络研讨会"],
      ar: ["كل مزايا Pro +", "واجهة API للبيانات الخام", "تقارير PDF شهرية", "وصول إصدار تجريبي", "مدير حساب مخصص", "ندوات حصرية عبر الإنترنت"],
    },
  },
];

export default function Pricing() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;

  return (
    <div className="py-16 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">{t("sub_title")}</h1>
          <p className="text-gray-400 text-lg">{t("sub_subtitle")}</p>
          <p className="text-sm text-gray-500 mt-3">{t("legal_note")}</p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {PLANS.map((plan) => (
            <PlanCard
              key={plan.key}
              plan={plan.key}
              price={plan.price}
              popular={plan.popular}
              features={plan.features[lang] || plan.features.en}
              ctaLabel={t(plan.ctaKey)}
              ctaHref="/register"
            />
          ))}
        </div>
      </div>
    </div>
  );
}
