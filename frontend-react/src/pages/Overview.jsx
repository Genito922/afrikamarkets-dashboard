/**
 * Overview — Afrika Markets Intelligence
 * Page d'accueil pédagogique + wizard profil investisseur
 *
 * Structure :
 *   Étape 0 — Landing : hero + guide pédagogique + navigation plateforme
 *   Étape 1 — Profil investisseur
 *   Étape 2 — Quiz risque
 *   Étape 3 — Connaissances trading (MiFID II)
 *   Étape 4 — Résultat profil + plan
 *   Étape 5 — Accès / inscription
 *
 * Conformité : langue neutre "signal" vs "recommandation d'achat",
 *              disclaimer non-affiliation BRVM visible sur toute la page.
 */
import { useState, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import ComplianceBanner from "../components/ComplianceBanner";
import MarketMoodWidget from "../components/MarketMoodWidget";

// ── Logo inline ───────────────────────────────────────────────

function Logo({ size = "md" }) {
  const s = size === "lg"
    ? { wrap: "gap-3", icon: "w-12 h-12 text-2xl", text: "text-2xl", sub: "text-sm" }
    : { wrap: "gap-2", icon: "w-8 h-8 text-base",  text: "text-base", sub: "text-xs" };
  return (
    <div className={`flex items-center ${s.wrap}`}>
      <div className={`${s.icon} rounded-xl bg-gradient-to-br from-green-600 to-emerald-800
                       flex items-center justify-center font-black text-white shadow-lg`}>
        Af
      </div>
      <div>
        <p className={`${s.text} font-black text-white leading-none tracking-tight`}>
          Afrika<span className="text-emerald-400">Markets</span>
        </p>
        <p className={`${s.sub} text-gray-500 leading-none`}>Intelligence</p>
      </div>
    </div>
  );
}

// ── Guide pédagogique — données ───────────────────────────────

const GUIDE_SECTIONS = [
  {
    icon: "📊",
    title: "Les bases de la bourse",
    color: "from-blue-900/40 to-blue-950/40 border-blue-800/40",
    accent: "#3b82f6",
    items: [
      {
        term: "Action",
        def: "Part de propriété dans une entreprise. En achetant une action SONATEL, vous devenez copropriétaire à hauteur de votre investissement et pouvez percevoir des dividendes.",
      },
      {
        term: "Obligation",
        def: "Titre de dette. Vous prêtez de l'argent à un État ou une entreprise, qui vous rembourse avec des intérêts à échéance fixe. Moins risqué qu'une action, mais rendement plus faible.",
      },
      {
        term: "Indice boursier",
        def: "Baromètre d'un marché. Le BRVM Composite regroupe toutes les actions cotées et reflète la santé globale du marché UEMOA. Sa hausse signifie que les entreprises progressent en moyenne.",
      },
      {
        term: "Capitalisation boursière",
        def: "Valeur totale d'une entreprise en bourse = cours × nombre d'actions. SGBC, première capitalisation BRVM, représente ~15% du marché.",
      },
    ],
  },
  {
    icon: "🏛️",
    title: "Les acteurs clés du marché UEMOA",
    color: "from-violet-900/40 to-violet-950/40 border-violet-800/40",
    accent: "#8b5cf6",
    items: [
      {
        term: "BRVM — Bourse Régionale des Valeurs Mobilières",
        def: "Marché central commun à 8 pays UEMOA (Bénin, Burkina Faso, Côte d'Ivoire, Guinée-Bissau, Mali, Niger, Sénégal, Togo). Siège à Abidjan. ~47 sociétés cotées, 1 500 Mds XOF de capitalisation.",
      },
      {
        term: "SGI — Société de Gestion et d'Intermédiation",
        def: "Votre courtier en bourse. Vous ne pouvez pas acheter des actions directement sur la BRVM : vous devez passer par un SGI agréé (NSIA Finance, CGF Bourse, Africabourse…). Il exécute vos ordres et conserve vos titres.",
      },
      {
        term: "AMF-UMOA — Autorité des Marchés Financiers",
        def: "Le régulateur. Surveille les acteurs (SGI, sociétés cotées), protège les investisseurs, valide les introductions en bourse. Équivalent de l'AMF française.",
      },
      {
        term: "DC/BR — Dépositaire Central / Banque de Règlement",
        def: "L'infrastructure invisible mais essentielle. Enregistre la propriété de tous les titres et règle les transactions (livraison des titres contre paiement). Garantit la sécurité de vos avoirs.",
      },
    ],
  },
  {
    icon: "🚀",
    title: "Comment investir concrètement",
    color: "from-emerald-900/40 to-emerald-950/40 border-emerald-800/40",
    accent: "#10b981",
    items: [
      {
        term: "1. Choisir un SGI",
        def: "Comparez les frais (0,65%–0,90%), le dépôt minimum (50 000–500 000 XOF), l'accès en ligne et la présence diaspora. Pour la diaspora Canada/France : NSIA Finance et Africabourse sont les plus accessibles.",
      },
      {
        term: "2. Ouvrir un compte titres",
        def: "Pièce d'identité, justificatif de domicile, formulaire KYC/AML. De plus en plus de SGI acceptent l'ouverture 100% en ligne. Délai : 3 à 10 jours ouvrés.",
      },
      {
        term: "3. Passer un ordre de bourse",
        def: "Ordre à cours limité (vous fixez le prix maximum d'achat) ou au marché (exécution immédiate au prix disponible). La BRVM cote du lundi au vendredi, 9h–13h heure de Lomé (UTC+0).",
      },
      {
        term: "4. Suivre votre portefeuille",
        def: "Vos titres apparaissent dans votre relevé DC/BR sous 3 jours ouvrés (J+3). Dividendes versés généralement en mai-juin. Relevé de compte mensuel obligatoire de votre SGI.",
      },
    ],
  },
  {
    icon: "🛡️",
    title: "Stratégies pour débutants",
    color: "from-amber-900/40 to-amber-950/40 border-amber-800/40",
    accent: "#f59e0b",
    items: [
      {
        term: "Investissement long terme (Buy & Hold)",
        def: "Acheter des valeurs solides (SGBC, ONTBF, SNTS) et les conserver 5–10 ans. Stratégie la plus simple et historiquement la plus performante sur les marchés africains.",
      },
      {
        term: "Diversification",
        def: "Répartir sur plusieurs secteurs : Finance (SGBC, BICC), Télécoms (SNTS, ETIT), Agro-industrie (PALC, SIVC). Réduire le risque sans sacrifier le rendement moyen.",
      },
      {
        term: "Dollar-Cost Averaging (investissement régulier)",
        def: "Investir un montant fixe chaque mois (ex: 50 000 XOF). Vous achetez plus de titres quand le cours est bas, moins quand il est haut. Lisse le risque de timing.",
      },
      {
        term: "Surveiller le P/E Ratio",
        def: "Cours / Bénéfice par action. Un P/E de 10 signifie que vous payez 10× les bénéfices annuels. Sur la BRVM, un P/E < 8 est souvent considéré comme sous-évalué.",
      },
    ],
  },
  {
    icon: "🏦",
    title: "Alternative : Fonds Communs de Placement (FCP)",
    color: "from-cyan-900/40 to-cyan-950/40 border-cyan-800/40",
    accent: "#06b6d4",
    items: [
      {
        term: "Qu'est-ce qu'un FCP ?",
        def: "Un panier d'actions géré par un professionnel. Vous investissez dans le fonds, le gestionnaire choisit les titres BRVM pour vous. Idéal si vous n'avez pas le temps d'analyser le marché.",
      },
      {
        term: "Avantages vs actions en direct",
        def: "Diversification immédiate dès 25 000 XOF, gestion professionnelle, aucune décision à prendre. Inconvénient : frais de gestion annuels (0,5%–2%) et moins de contrôle.",
      },
      {
        term: "Principaux FCP BRVM",
        def: "SICAV Loko (CGF Bourse), FCP Hudson Patrimoine (Hudson & Cie), SICAV Coris Actions (Coris Bourse). Performance moyenne sur 5 ans : +6% à +12%/an selon les millésimes.",
      },
      {
        term: "Pour qui ?",
        def: "Parfait pour les débutants, la diaspora avec peu de temps disponible, ou les investisseurs recherchant un complément de revenus sans gérer activement un portefeuille.",
      },
    ],
  },
  {
    icon: "📐",
    title: "Analyser vos investissements",
    color: "from-rose-900/40 to-rose-950/40 border-rose-800/40",
    accent: "#f43f5e",
    items: [
      {
        term: "Analyse technique (AT)",
        def: "Étude des graphiques de prix et volumes. Les indicateurs MA (moyennes mobiles), RSI et MFI identifient les tendances et zones de retournement. Disponible dans l'onglet Analyse de cette plateforme.",
      },
      {
        term: "Analyse fondamentale",
        def: "Étude des bilans, résultats et dividendes. P/E Ratio, rendement du dividende, croissance du chiffre d'affaires. Consultez les rapports annuels dans l'onglet Titres → Profil Société.",
      },
      {
        term: "RSI — Relative Strength Index",
        def: "Oscille entre 0 et 100. < 30 = zone de survente (potentielle opportunité), > 70 = zone de surachat (prudence). Ne constitue pas une recommandation d'investissement.",
      },
      {
        term: "Signaux techniques",
        def: "Golden Cross (MA court terme croise MA long terme à la hausse) = signal positif. Death Cross (inverse) = signal négatif. Ces signaux sont indicatifs, pas prédictifs.",
      },
    ],
  },
  {
    icon: "⚖️",
    title: "Investissement responsable",
    color: "from-teal-900/40 to-teal-950/40 border-teal-800/40",
    accent: "#14b8a6",
    items: [
      {
        term: "Ne jamais investir ce que vous ne pouvez pas perdre",
        def: "Règle d'or. Investissez uniquement votre épargne disponible, jamais votre épargne de précaution (3–6 mois de charges) ni de l'argent emprunté.",
      },
      {
        term: "Éviter les décisions émotionnelles",
        def: "La panique lors d'une chute mène à vendre au plus bas. L'euphorie lors d'une hausse mène à acheter au plus haut. Définissez votre stratégie à l'avance et respectez-la.",
      },
      {
        term: "Vision long terme sur la BRVM",
        def: "La BRVM a progressé de ~+6%/an en moyenne sur 10 ans malgré les crises. Les investisseurs patient et diversifiés ont historiquement bien performé. Évitez le trading court terme sans expérience.",
      },
      {
        term: "Se former continuellement",
        def: "Lisez les rapports annuels des entreprises cotées, les publications AMF-UMOA, les analyses sectorielles. Cette plateforme propose des outils éducatifs et analytiques pour vous accompagner.",
      },
    ],
  },
];

// ── Features de la plateforme — 3 clusters ───────────────────

const PLATFORM_CLUSTERS = [
  {
    key: "marches",
    icon: "📊",
    title: "Marchés & Données",
    color: "from-blue-950/50 to-blue-950/20 border-blue-900/40",
    accent: "#3b82f6",
    features: [
      {
        to: "/marche",        icon: "📈", label: "Marché BRVM",
        desc: "Cours temps réel · 47 titres · Volumes · Top/Flop du jour",
      },
      {
        to: "/international", icon: "🌍", label: "Marchés Africains",
        desc: "JSE · NGX · GSE · NSE Kenya · EGX · BVC · BVMT",
      },
    ],
  },
  {
    key: "analyse",
    icon: "🧠",
    title: "Analyse & Signaux IA",
    color: "from-emerald-950/50 to-emerald-950/20 border-emerald-900/40",
    accent: "#10b981",
    features: [
      {
        to: "/analyse",  icon: "📐", label: "Analyse Technique",
        desc: "MA 16/19/246/361 · RSI · MFI · Croisements · Signaux",
      },
      {
        to: "/risques",  icon: "🛡️", label: "War Room UEMOA",
        desc: "Géopolitique · Macro · Risque pays · Contexte régional",
      },
    ],
  },
  {
    key: "gestion",
    icon: "💼",
    title: "Gestion & Courtiers",
    color: "from-violet-950/50 to-violet-950/20 border-violet-900/40",
    accent: "#8b5cf6",
    features: [
      {
        to: "/portefeuille", icon: "💼", label: "Portefeuille",
        desc: "Suivi de performance · Allocation sectorielle · Historique",
      },
      {
        to: "/sgi",          icon: "🏢", label: "SGI & OPCVM",
        desc: "Annuaire · Classement des 8 intermédiaires agréés BRVM",
      },
    ],
  },
];

// ── Données wizard (identiques à avant) ──────────────────────

const INVESTOR_TYPES = [
  { id: "diaspora", icon: "✈️",  label: "Diaspora",       desc: "Investisseur à l'étranger" },
  { id: "local",    icon: "🏠",  label: "Local UEMOA",    desc: "Résident Afrique de l'Ouest" },
  { id: "instit",   icon: "🏦",  label: "Institutionnel", desc: "Fonds, banque, assurance" },
  { id: "debutant", icon: "🌱",  label: "Débutant",       desc: "Premier investissement" },
];

const RISK_QUIZ = [
  {
    id: "risk", q: "Quelle est votre tolérance au risque ?",
    opts: [
      { label: "Faible — je préfère la sécurité", score: 1 },
      { label: "Modérée — équilibre rendement / risque", score: 2 },
      { label: "Élevée — je vise la performance maximale", score: 3 },
    ],
  },
  {
    id: "horizon", q: "Quel est votre horizon d'investissement ?",
    opts: [
      { label: "Court terme — moins d'1 an", score: 1 },
      { label: "Moyen terme — 1 à 5 ans", score: 2 },
      { label: "Long terme — plus de 5 ans", score: 3 },
    ],
  },
  {
    id: "goal", q: "Quel est votre objectif principal ?",
    opts: [
      { label: "Revenus réguliers (dividendes)", score: 1 },
      { label: "Croissance du capital", score: 2 },
      { label: "Les deux — stratégie mixte", score: 3 },
    ],
  },
  {
    id: "style", q: "Comment gérez-vous votre portefeuille ?",
    opts: [
      { label: "Passivement — je suis des analyses", score: 1 },
      { label: "En combinant analyses et décisions perso", score: 2 },
      { label: "Activement — j'analyse moi-même", score: 3 },
    ],
  },
];

const KNOWLEDGE_QUIZ = [
  {
    id: "q1", q: "La BRVM est :",
    opts: [
      { label: "Une banque centrale de l'UEMOA", correct: false },
      { label: "La bourse commune de 8 pays d'Afrique de l'Ouest", correct: true },
      { label: "Un organisme de crédit immobilier", correct: false },
      { label: "La monnaie officielle de la zone UEMOA", correct: false },
    ],
  },
  {
    id: "q2", q: "Vous investissez 500 000 FCFA. Le marché chute de 40 %. Capital restant ?",
    opts: [
      { label: "460 000 FCFA", correct: false },
      { label: "350 000 FCFA", correct: false },
      { label: "300 000 FCFA", correct: true },
      { label: "Je ne peux pas perdre en bourse", correct: false },
    ],
  },
  {
    id: "q3", q: "L'analyse technique consiste à :",
    opts: [
      { label: "Analyser les bilans comptables et états financiers", correct: false },
      { label: "Étudier l'historique des prix et volumes pour anticiper les mouvements", correct: true },
      { label: "Consulter uniquement des analystes financiers", correct: false },
      { label: "Suivre uniquement l'actualité politique", correct: false },
    ],
  },
  {
    id: "q4", q: "La diversification vise principalement à :",
    opts: [
      { label: "Maximiser les gains en concentrant les investissements", correct: false },
      { label: "Réduire le risque en répartissant sur plusieurs actifs", correct: true },
      { label: "Réduire les frais de courtage", correct: false },
      { label: "Éviter de payer des impôts sur les plus-values", correct: false },
    ],
  },
  {
    id: "q5", q: "La liquidité d'une action désigne :",
    opts: [
      { label: "Le montant des dividendes versés chaque année", correct: false },
      { label: "La valeur totale de l'entreprise en bourse", correct: false },
      { label: "La facilité à acheter ou vendre rapidement sans impacter le cours", correct: true },
      { label: "Le capital social de l'entreprise cotée", correct: false },
    ],
  },
  {
    id: "q6", q: "Un ordre Stop-Loss est :",
    opts: [
      { label: "Un ordre d'achat automatique en cas de hausse", correct: false },
      { label: "Un ordre de vente automatique si le cours descend sous un seuil fixé", correct: true },
      { label: "Un frais de transaction supplémentaire", correct: false },
      { label: "Une limitation imposée aux investisseurs étrangers", correct: false },
    ],
  },
  {
    id: "q7", q: "Un dividende représente :",
    opts: [
      { label: "Une taxe prélevée sur les plus-values boursières", correct: false },
      { label: "Le cours d'ouverture d'une action chaque matin", correct: false },
      { label: "Un frais de gestion annuel facturé par le SGI", correct: false },
      { label: "Une partie des bénéfices reversée aux actionnaires", correct: true },
    ],
  },
];

const PROFILES = [
  {
    range: [4, 8],   emoji: "🌿", label: "Profil Novice Prudent",
    desc: "Vous débutez. Commencez par les valeurs solides de la BRVM et construisez progressivement vos connaissances.",
    knowledge: "Novice", plan: "starter",
    alloc: { brvm: "80%", cash: "15%", intl: "5%" },
  },
  {
    range: [9, 12],  emoji: "⚖️", label: "Profil Débutant Équilibré",
    desc: "Vous avez les bases. L'analyse technique et les signaux vous aideront à optimiser vos points d'entrée.",
    knowledge: "Débutant", plan: "starter",
    alloc: { brvm: "70%", cash: "15%", intl: "15%" },
  },
  {
    range: [13, 16], emoji: "📊", label: "Profil Intermédiaire",
    desc: "Bonne maîtrise. Les outils avancés, la war room géopolitique et la gestion de portefeuille sont vos atouts.",
    knowledge: "Intermédiaire", plan: "pro",
    alloc: { brvm: "60%", cash: "10%", intl: "30%" },
  },
  {
    range: [17, 19], emoji: "🚀", label: "Profil Averti Dynamique",
    desc: "Vous maîtrisez les marchés. Les signaux multi-marchés et l'analyse avancée maximiseront votre performance.",
    knowledge: "Averti", plan: "expert",
    alloc: { brvm: "50%", cash: "5%", intl: "45%" },
  },
];

const PLAN_LABELS = { starter: "Starter", pro: "Pro", expert: "Expert" };
const PLAN_PRICES = { starter: "$29.99/mo", pro: "$74.99/mo", expert: "$199.99/mo" };
const PLAN_COLORS = { starter: "border-blue-600", pro: "border-brand-500", expert: "border-yellow-600" };
const PLAN_FEATS  = {
  starter: ["Dashboard BRVM complet", "Indices & secteurs", "Analyse technique MA/RSI", "Top 10 mouvements"],
  pro:     ["Tout Starter +", "War Room géopolitique", "Simulateur portefeuille", "Alertes prix", "SGI & OPCVM"],
  expert:  ["Tout Pro +", "Marchés africains internationaux", "Signaux IA multi-marchés", "Export CSV/PDF", "Support prioritaire"],
};

// ── Sous-composants wizard ────────────────────────────────────

function StepsBar({ step }) {
  const STEPS = ["Guide", "Profil", "Risque", "Connaissances", "Résultat", "Accès"];
  return (
    <div className="flex items-center justify-center mb-8 max-w-lg mx-auto">
      {STEPS.map((label, i) => {
        const n = i + 1, done = step > n, active = step === n;
        return (
          <div key={label} className="flex-1 text-center relative">
            {i < STEPS.length - 1 && (
              <div className={`absolute top-[17px] left-1/2 w-full h-0.5
                ${done ? "bg-brand-500" : "bg-gray-700"}`} />
            )}
            <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center
                             text-xs font-bold mx-auto mb-1 relative z-10 transition-all
                             ${done   ? "bg-brand-500 border-brand-500 text-white"
                                      : active
                                          ? "bg-brand-500/20 border-brand-500 text-brand-400"
                                          : "bg-gray-900 border-gray-700 text-gray-500"}`}>
              {done ? "✓" : n}
            </div>
            <p className={`text-[10px] tracking-wide hidden sm:block
                           ${active ? "text-brand-400" : "text-gray-600"}`}>
              {label}
            </p>
          </div>
        );
      })}
    </div>
  );
}

function QuizOption({ label, selected, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-3 px-4 py-3 rounded-xl border-2 text-left text-sm
                  transition-all w-full
                  ${selected
                    ? "border-brand-500 bg-brand-500/10 text-white"
                    : "border-gray-700 text-gray-400 hover:border-gray-500 hover:text-white"}`}
    >
      <span className={`w-4 h-4 rounded-full border-2 flex-shrink-0
                        ${selected ? "bg-brand-500 border-brand-500" : "border-gray-600"}`} />
      {label}
    </button>
  );
}


// ── Guide accordéon ───────────────────────────────────────────

function GuideSection({ section, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`rounded-2xl border bg-gradient-to-br ${section.color} overflow-hidden`}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">{section.icon}</span>
          <span className="text-base font-bold text-white">{section.title}</span>
        </div>
        <span className="text-gray-400 text-lg transition-transform duration-200"
              style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)" }}>
          ▾
        </span>
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-4 border-t border-white/5 pt-4">
          {section.items.map((item, i) => (
            <div key={i} className="flex gap-3">
              <div className="w-1 rounded-full shrink-0 mt-1" style={{ background: section.accent }} />
              <div>
                <p className="text-sm font-semibold text-white mb-0.5">{item.term}</p>
                <p className="text-xs text-gray-300 leading-relaxed">{item.def}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Page principale ───────────────────────────────────────────

export default function Overview() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const wizardRef = useRef(null);

  const [step,        setStep]        = useState(0);
  const [profil,      setProfil]      = useState({ name: "", type: "" });
  const [riskAnswers, setRiskAnswers] = useState({});
  const [knowAnswers, setKnowAnswers] = useState({});
  const [profile,     setProfile]     = useState(null);

  function computeProfile(risk, know) {
    const riskScore = Object.values(risk).reduce((a, b) => a + b, 0);
    const knowScore = Object.values(know).filter(Boolean).length;
    const total     = riskScore + knowScore;
    return PROFILES.find((p) => total >= p.range[0] && total <= p.range[1]) ?? PROFILES[1];
  }

  function startWizard() {
    setStep(1);
    setTimeout(() => wizardRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
  }

  function selectRisk(qid, score) {
    const next = { ...riskAnswers, [qid]: score };
    setRiskAnswers(next);
    if (Object.keys(next).length === RISK_QUIZ.length) setTimeout(() => setStep(3), 400);
  }

  function selectKnow(qid, correct) {
    const next = { ...knowAnswers, [qid]: correct };
    setKnowAnswers(next);
    if (Object.keys(next).length === KNOWLEDGE_QUIZ.length) {
      const p = computeProfile(riskAnswers, next);
      setProfile(p);
      setTimeout(() => setStep(5), 400);
    }
  }

  const knowScore    = Object.values(knowAnswers).filter(Boolean).length;
  const knowProgress = (Object.keys(knowAnswers).length / KNOWLEDGE_QUIZ.length) * 100;
  const riskProgress = (Object.keys(riskAnswers).length / RISK_QUIZ.length) * 100;

  return (
    <div className="min-h-screen bg-gray-950">

      {/* ══════════════════════════════════════════════════════════
          SECTION 0 — HERO
      ══════════════════════════════════════════════════════════ */}
      <section className="relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-gray-950 via-green-950/20 to-gray-950 pointer-events-none" />
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-900/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-blue-900/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-5xl mx-auto px-4 pt-16 pb-12">
          {/* Logo + badge non-affiliation */}
          <div className="flex flex-wrap items-center justify-between gap-4 mb-10">
            <Logo size="lg" />
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-900 border border-gray-700">
              <span className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
              <span className="text-xs text-gray-400">Outil indépendant · Non affilié à la BRVM</span>
            </div>
          </div>

          {/* Hero headline */}
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/60
                            border border-emerald-800/40 text-emerald-300 text-xs font-medium mb-4">
              🌍 Marchés Financiers Africains · UEMOA · BRVM · 8 Bourses
            </div>
            <h1 className="text-4xl sm:text-5xl font-black text-white leading-tight mb-4">
              Investir à la BRVM
              <span className="block text-emerald-400">avec méthode et confiance</span>
            </h1>
            <p className="text-lg text-gray-300 mb-3 max-w-2xl">
              Terminal d'analyse financière éducatif pour les marchés africains —
              Cours temps réel · Analyse technique · Signaux IA · Annuaire SGI
            </p>
            <p className="text-sm text-gray-500 mb-8">
              Langage simple · Aucun jargon inutile · Adapté à la diaspora et aux investisseurs UEMOA
            </p>

            {/* Stats ticker */}
            <div className="flex flex-wrap gap-6 mb-8">
              {[
                { label: "Titres cotés BRVM", value: "47" },
                { label: "Pays UEMOA", value: "8" },
                { label: "Capitalisation", value: "~1 500 Mds XOF" },
                { label: "Bourses africaines", value: "9" },
              ].map((s) => (
                <div key={s.label} className="text-center">
                  <p className="text-2xl font-black text-white">{s.value}</p>
                  <p className="text-xs text-gray-500">{s.label}</p>
                </div>
              ))}
            </div>

            {/* CTAs */}
            <div className="flex flex-wrap gap-3 mb-6">
              <button
                onClick={startWizard}
                className="btn-primary px-6 py-3 text-base"
              >
                Créer mon profil investisseur →
              </button>
              {isAuthenticated ? (
                <button
                  onClick={() => navigate("/dashboard")}
                  className="px-6 py-3 rounded-xl border border-gray-700 text-gray-300
                             hover:border-gray-500 hover:text-white transition-all text-base"
                >
                  Mon tableau de bord
                </button>
              ) : (
                <button
                  onClick={() => navigate("/pricing")}
                  className="px-6 py-3 rounded-xl border border-gray-700 text-gray-300
                             hover:border-gray-500 hover:text-white transition-all text-base"
                >
                  Voir les plans →
                </button>
              )}
            </div>

            {/* Market Mood live */}
            <MarketMoodWidget />
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════
          SECTION 1 — GUIDE PÉDAGOGIQUE
      ══════════════════════════════════════════════════════════ */}
      <section className="max-w-5xl mx-auto px-4 py-14">
        <div className="text-center mb-10">
          <p className="text-xs text-emerald-400 uppercase tracking-widest font-semibold mb-2">
            Guide pédagogique complet
          </p>
          <h2 className="text-3xl font-black text-white mb-3">
            Comprendre la bourse africaine
          </h2>
          <p className="text-gray-400 max-w-xl mx-auto text-sm">
            Tout ce qu'il faut savoir pour investir à la BRVM avec méthode —
            du vocabulaire de base aux stratégies avancées. Cliquez sur chaque section pour l'ouvrir.
          </p>
        </div>

        <div className="space-y-3">
          {GUIDE_SECTIONS.map((section, i) => (
            <GuideSection key={section.title} section={section} defaultOpen={i === 0} />
          ))}
        </div>

        <div className="mt-6 grid sm:grid-cols-3 gap-3 text-xs">
          {[
            { icon: "✔", text: "Langage simple — aucun jargon financier inutile" },
            { icon: "✔", text: "Adapté au contexte africain et à la BRVM" },
            { icon: "✔", text: "Approche orientée pratique et action" },
          ].map((t) => (
            <div key={t.text} className="flex items-start gap-2 p-3 rounded-xl bg-gray-900/60 border border-gray-800">
              <span className="text-emerald-400">{t.icon}</span>
              <span className="text-gray-400">{t.text}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════
          SECTION 2 — NAVIGATION PLATEFORME (3 clusters)
      ══════════════════════════════════════════════════════════ */}
      <section className="max-w-5xl mx-auto px-4 pb-14">
        <div className="text-center mb-8">
          <p className="text-xs text-blue-400 uppercase tracking-widest font-semibold mb-2">Plateforme</p>
          <h2 className="text-2xl font-black text-white mb-2">Comment utiliser la plateforme</h2>
          <p className="text-gray-500 text-sm">3 domaines · 6 modules · progressez à votre rythme</p>
        </div>

        <div className="grid sm:grid-cols-3 gap-4">
          {PLATFORM_CLUSTERS.map((cluster) => (
            <div
              key={cluster.key}
              className={`rounded-2xl border bg-gradient-to-br ${cluster.color} p-4 space-y-3`}
            >
              {/* Cluster header */}
              <div className="flex items-center gap-2 pb-2 border-b border-white/5">
                <span className="text-xl">{cluster.icon}</span>
                <p className="text-sm font-bold text-white">{cluster.title}</p>
              </div>
              {/* Feature links */}
              {cluster.features.map((f) => (
                <Link
                  key={f.to}
                  to={isAuthenticated ? f.to : "/register"}
                  className="flex items-start gap-2.5 group"
                >
                  <span className="text-lg mt-0.5">{f.icon}</span>
                  <div>
                    <p className="text-sm font-semibold text-white group-hover:underline
                                  decoration-dotted underline-offset-2 transition-colors"
                       style={{ textDecorationColor: cluster.accent }}>
                      {f.label}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5 leading-snug">{f.desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          ))}
        </div>

        <p className="text-xs text-gray-600 text-center mt-5">
          La bourse n'est pas un sprint — c'est un processus d'apprentissage continu. Prenez votre temps.
        </p>
      </section>

      {/* ══════════════════════════════════════════════════════════
          DISCLAIMER LÉGAL — composant unique
      ══════════════════════════════════════════════════════════ */}
      <div className="max-w-5xl mx-auto px-4 pb-8">
        <ComplianceBanner variant="full" />
      </div>

      {/* ══════════════════════════════════════════════════════════
          SECTION 3 — WIZARD PROFIL
      ══════════════════════════════════════════════════════════ */}
      <section ref={wizardRef} className="max-w-xl mx-auto px-4 pb-20">
        {step === 0 ? (
          <div className="card text-center py-10 border border-gray-800">
            <p className="text-4xl mb-3">🧭</p>
            <h2 className="text-xl font-bold text-white mb-2">Établissez votre profil investisseur</h2>
            <p className="text-gray-400 text-sm mb-6 max-w-sm mx-auto">
              Quiz de 5 minutes · Profil personnalisé · Plan recommandé adapté à vos objectifs
            </p>
            <button onClick={startWizard} className="btn-primary px-8 py-3">
              Commencer le quiz →
            </button>
          </div>
        ) : (
          <>
            <StepsBar step={step} />

            {/* ── ÉTAPE 1 — PROFIL ────────────────────────── */}
            {step === 1 && (
              <form
                onSubmit={(e) => { e.preventDefault(); if (profil.type) setStep(2); }}
                className="card flex flex-col gap-6"
              >
                <div>
                  <h2 className="text-2xl font-bold text-white mb-1">👤 Votre profil</h2>
                  <p className="text-gray-400 text-sm">Personnalisez votre expérience Afrika Markets.</p>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Prénom (optionnel)</label>
                  <input
                    type="text"
                    value={profil.name}
                    onChange={(e) => setProfil({ ...profil, name: e.target.value })}
                    placeholder="Marie"
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-4 py-2.5
                               focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-3">Quel type d'investisseur êtes-vous ?</label>
                  <div className="grid grid-cols-2 gap-3">
                    {INVESTOR_TYPES.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => setProfil({ ...profil, type: t.id })}
                        className={`p-4 rounded-xl border-2 text-center transition-all
                          ${profil.type === t.id
                            ? "border-brand-500 bg-brand-500/10"
                            : "border-gray-700 bg-gray-800/50 hover:border-gray-600"}`}
                      >
                        <span className="text-2xl block mb-1">{t.icon}</span>
                        <span className="text-white text-sm font-semibold block">{t.label}</span>
                        <span className="text-gray-500 text-xs">{t.desc}</span>
                      </button>
                    ))}
                  </div>
                </div>
                <button type="submit" disabled={!profil.type} className="btn-primary w-full disabled:opacity-40">
                  Continuer →
                </button>
              </form>
            )}

            {/* ── ÉTAPE 2 — QUIZ RISQUE ───────────────────── */}
            {step === 2 && (
              <div className="card flex flex-col gap-5">
                <div>
                  <h2 className="text-2xl font-bold text-white mb-1">📊 Profil de risque</h2>
                  <p className="text-gray-400 text-sm mb-3">
                    {Object.keys(riskAnswers).length}/{RISK_QUIZ.length} questions
                  </p>
                  <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-500 rounded-full transition-all duration-500"
                         style={{ width: `${riskProgress}%` }} />
                  </div>
                </div>
                {RISK_QUIZ.map((q) => (
                  <div key={q.id}>
                    <h3 className="text-sm font-semibold text-white mb-3">{q.q}</h3>
                    <div className="flex flex-col gap-2">
                      {q.opts.map((opt) => (
                        <QuizOption
                          key={opt.label}
                          label={opt.label}
                          selected={riskAnswers[q.id] === opt.score}
                          onClick={() => selectRisk(q.id, opt.score)}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* ── ÉTAPE 3 — AVERTISSEMENT RISQUE ─────────── */}
            {step === 3 && (
              <div className="flex flex-col gap-4">
                <div className="card border border-yellow-700/40 bg-yellow-900/10">
                  <div className="flex gap-3">
                    <span className="text-yellow-400 text-xl flex-shrink-0">⚠️</span>
                    <div>
                      <p className="text-yellow-300 text-sm font-semibold mb-1">
                        Avertissement sur les risques de perte en capital
                      </p>
                      <p className="text-yellow-200/70 text-xs leading-relaxed">
                        Les investissements en bourse comportent un risque de perte en capital,
                        pouvant aller jusqu'à la <strong className="text-yellow-300">perte totale</strong>.
                        Les performances passées ne préjugent pas des performances futures.
                        Assurez-vous de comprendre les risques avant d'investir.
                      </p>
                    </div>
                  </div>
                </div>
                <button onClick={() => setStep(4)} className="btn-primary w-full">
                  J'ai compris — Continuer →
                </button>
              </div>
            )}

            {/* ── ÉTAPE 4 — QUIZ CONNAISSANCES ────────────── */}
            {step === 4 && (
              <div className="card flex flex-col gap-5">
                <div>
                  <h2 className="text-2xl font-bold text-white mb-1">🎓 Connaissances en trading</h2>
                  <p className="text-gray-400 text-sm mb-3">
                    {Object.keys(knowAnswers).length}/{KNOWLEDGE_QUIZ.length} questions
                    {Object.keys(knowAnswers).length === KNOWLEDGE_QUIZ.length && (
                      <span className="text-brand-400 ml-2">
                        · Score : {knowScore}/7 ({
                          knowScore <= 2 ? "Novice" :
                          knowScore <= 4 ? "Débutant" :
                          knowScore <= 6 ? "Intermédiaire" : "Averti"
                        })
                      </span>
                    )}
                  </p>
                  <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full bg-brand-500 rounded-full transition-all duration-500"
                         style={{ width: `${knowProgress}%` }} />
                  </div>
                </div>
                {KNOWLEDGE_QUIZ.map((q) => (
                  <div key={q.id}>
                    <h3 className="text-sm font-semibold text-white mb-3">{q.q}</h3>
                    <div className="flex flex-col gap-2">
                      {q.opts.map((opt, i) => {
                        const answered = q.id in knowAnswers;
                        return (
                          <button
                            key={i}
                            disabled={answered}
                            onClick={() => selectKnow(q.id, opt.correct)}
                            className={`flex items-center gap-3 px-4 py-3 rounded-xl border-2 text-left
                                        text-sm transition-all w-full
                                        ${!answered
                                          ? "border-gray-700 text-gray-400 hover:border-gray-500 hover:text-white"
                                          : opt.correct
                                              ? "border-green-500 bg-green-900/20 text-green-300"
                                              : "border-gray-700 text-gray-600 opacity-50"}`}
                          >
                            <span className={`w-4 h-4 rounded-full border-2 flex-shrink-0
                                              ${!answered ? "border-gray-600"
                                                : opt.correct ? "bg-green-500 border-green-500"
                                                             : "border-gray-600"}`} />
                            {opt.label}
                            {answered && opt.correct && (
                              <span className="ml-auto text-green-400 text-xs shrink-0">✓ Bonne réponse</span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* ── ÉTAPE 5 — RÉSULTAT ──────────────────────── */}
            {step === 5 && profile && (
              <div className="flex flex-col gap-5">
                <div className="card text-center border border-gray-800">
                  <span className="text-6xl block mb-3">{profile.emoji}</span>
                  <h2 className="text-2xl font-bold text-white mb-1">{profile.label}</h2>
                  <span className="inline-block text-xs text-brand-400 bg-brand-500/10 border
                                   border-brand-500/20 px-3 py-1 rounded-full mb-3">
                    Connaissances : {profile.knowledge}
                  </span>
                  <p className="text-gray-400 text-sm max-w-sm mx-auto">{profile.desc}</p>
                </div>

                <div className="card border border-gray-800">
                  <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">
                    Allocation indicative suggérée
                  </h3>
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { label: "BRVM",  value: profile.alloc.brvm, color: "text-brand-400" },
                      { label: "Cash",  value: profile.alloc.cash, color: "text-yellow-400" },
                      { label: "Intl",  value: profile.alloc.intl, color: "text-purple-400" },
                    ].map((a) => (
                      <div key={a.label} className="bg-gray-800 rounded-xl p-3 text-center">
                        <span className={`text-2xl font-bold block ${a.color}`}>{a.value}</span>
                        <span className="text-xs text-gray-500 uppercase">{a.label}</span>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-gray-600 mt-2 text-center">
                    À titre indicatif uniquement · Non constitutif d'un conseil en investissement
                  </p>
                </div>

                <div className={`card border-2 ${PLAN_COLORS[profile.plan]}`}>
                  <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Plan suggéré</p>
                  <div className="flex items-baseline gap-2 mb-1">
                    <h3 className="text-xl font-bold text-white">{PLAN_LABELS[profile.plan]}</h3>
                    <span className="text-brand-400 font-semibold text-sm">{PLAN_PRICES[profile.plan]}</span>
                  </div>
                  <ul className="mt-2 space-y-1">
                    {PLAN_FEATS[profile.plan].map((f) => (
                      <li key={f} className="text-xs text-gray-400 flex gap-2">
                        <span className="text-brand-400">✓</span>{f}
                      </li>
                    ))}
                  </ul>
                </div>

                {isAuthenticated ? (
                  <button
                    onClick={() => navigate("/dashboard")}
                    className="btn-primary w-full py-4 text-base"
                  >
                    Accéder à mon tableau de bord →
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => navigate(
                        `/register?plan=${profile.plan}${profil.name ? `&name=${encodeURIComponent(profil.name)}` : ""}`
                      )}
                      className="btn-primary w-full py-4 text-base"
                    >
                      Créer mon compte {PLAN_LABELS[profile.plan]} — Essai 14 jours
                    </button>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-px bg-gray-700" />
                      <span className="text-xs text-gray-500">ou</span>
                      <div className="flex-1 h-px bg-gray-700" />
                    </div>
                    <div className="flex gap-3">
                      <button
                        onClick={() => navigate("/pricing")}
                        className="flex-1 py-3 rounded-xl border border-gray-700 text-gray-300
                                   hover:border-gray-500 hover:text-white transition-all text-sm"
                      >
                        Voir tous les plans →
                      </button>
                      <button
                        onClick={() => navigate("/login")}
                        className="flex-1 py-3 rounded-xl border border-gray-700 text-gray-300
                                   hover:border-gray-500 hover:text-white transition-all text-sm"
                      >
                        Se connecter
                      </button>
                    </div>
                  </>
                )}

                <ComplianceBanner variant="compact" />
              </div>
            )}
          </>
        )}
      </section>

    </div>
  );
}
