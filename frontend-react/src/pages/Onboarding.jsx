import { useState, useEffect } from "react"

// ── Logo Afrika Markets ────────────────────────────────────────
function Logo({ size = 80 }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
      <svg width={size} height={size} viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Fond circulaire */}
        <circle cx="40" cy="40" r="40" fill="#0A0C0F"/>
        <circle cx="40" cy="40" r="38" stroke="#C9A84C" strokeWidth="1.5" strokeOpacity="0.4"/>
        {/* Contour Afrique simplifié */}
        <path d="M28 18 L32 14 L38 13 L44 14 L50 18 L54 24 L56 30 L55 36 L52 40 L54 46 L52 52 L48 58 L44 62 L40 64 L36 62 L32 58 L28 52 L26 46 L28 40 L25 34 L24 28 Z"
          fill="#C9A84C" fillOpacity="0.12" stroke="#C9A84C" strokeWidth="1.2" strokeOpacity="0.6"/>
        {/* Ligne de tendance haussière */}
        <polyline points="20,55 28,48 35,50 42,38 50,32 60,22"
          stroke="#C9A84C" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
        {/* Points sur la courbe */}
        <circle cx="28" cy="48" r="2" fill="#C9A84C"/>
        <circle cx="42" cy="38" r="2" fill="#C9A84C"/>
        <circle cx="60" cy="22" r="3" fill="#C9A84C"/>
        {/* Flèche montante */}
        <polyline points="57,18 60,22 63,18" stroke="#C9A84C" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
      </svg>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontFamily: "'DM Serif Display', serif", fontSize: size > 60 ? "1.6rem" : "1.1rem", color: "#C9A84C", letterSpacing: "0.02em" }}>
          Afrika <span style={{ color: "#F0EDE8" }}>Markets</span>
        </div>
        <div style={{ fontSize: "0.65rem", color: "#8A8580", letterSpacing: "0.15em", textTransform: "uppercase", marginTop: "2px" }}>
          Intelligence
        </div>
      </div>
    </div>
  )
}

// ── Données des slides d'apprentissage ────────────────────────
const SLIDES = [
  {
    id: 1,
    icon: "🌍",
    category: "Pourquoi la BRVM ?",
    title: "La bourse la plus dynamique d'Afrique de l'Ouest",
    content: "La BRVM (Bourse Régionale des Valeurs Mobilières) regroupe 8 pays de l'UEMOA. En 2025, le BRVM Principal a progressé de +57% — une performance que peu de marchés mondiaux peuvent égaler.",
    stat: { value: "+57%", label: "Rendement BRVM Principal 2025" },
    color: "#2ECC71",
    tip: "La BRVM est accessible depuis le Canada, la France ou les USA via une SGI agréée.",
  },
  {
    id: 2,
    icon: "📈",
    category: "Les bases du trading",
    title: "Comprendre les cours boursiers",
    content: "Un cours boursier représente le prix d'une action à un instant T. Il fluctue selon l'offre et la demande. Quand plus d'investisseurs veulent acheter qu'il n'y a de vendeurs, le cours monte. L'inverse provoque une baisse.",
    stat: { value: "45+", label: "Entreprises cotées sur la BRVM" },
    color: "#3498DB",
    tip: "Conseil : regardez toujours le volume des échanges. Un mouvement de cours avec fort volume est plus fiable qu'un mouvement avec faible volume.",
  },
  {
    id: 3,
    icon: "📊",
    category: "Analyse technique",
    title: "Lire un graphique boursier",
    content: "Un graphique en bougies japonaises (candlestick) montre, pour chaque période : le prix d'ouverture, le plus haut, le plus bas et le prix de clôture. Une bougie verte = cours en hausse. Une bougie rouge = cours en baisse.",
    stat: { value: "RSI · MACD · SMA", label: "Indicateurs techniques clés" },
    color: "#E67E22",
    tip: "Sur Afrika Markets, TradingView vous donne accès à plus de 100 indicateurs techniques en un clic.",
    visual: "candle",
  },
  {
    id: 4,
    icon: "💼",
    category: "Analyse fondamentale",
    title: "Évaluer la valeur réelle d'une entreprise",
    content: "L'analyse fondamentale consiste à examiner les résultats financiers d'une entreprise : chiffre d'affaires, bénéfice net, dividendes, ratio P/E (Price-to-Earnings). Un titre sous-évalué par le marché peut représenter une opportunité d'achat.",
    stat: { value: "1325", label: "Rapports d'analystes dans notre Research Hub" },
    color: "#9B59B6",
    tip: "Exemple ONATEL BF : CA 2025 de 146,2 Md FCFA (+3,1%), Mobile Money +14,1% — des données disponibles dans notre Research Hub.",
  },
  {
    id: 5,
    icon: "⚖️",
    category: "Gestion du risque",
    title: "Ne jamais investir sans stratégie de sortie",
    content: "La règle d'or : ne jamais investir plus que ce que vous êtes prêt à perdre. Diversifiez votre portefeuille entre plusieurs secteurs et titres. Définissez avant d'investir votre objectif de gain ET votre seuil de perte acceptable.",
    stat: { value: "1 → 3%", label: "Risque recommandé par trade pour les débutants" },
    color: "#E74C3C",
    tip: "La War Room Afrika Markets vous alerte en temps réel sur les risques géopolitiques des 8 pays UEMOA avant qu'ils n'impactent vos positions.",
  },
  {
    id: 6,
    icon: "🌐",
    category: "Marchés africains",
    title: "Au-delà de la BRVM : 10 bourses africaines",
    content: "L'Afrique dispose de nombreuses places boursières : NGX au Nigeria, JSE en Afrique du Sud, GSE au Ghana, NSE au Kenya, EGX en Égypte... Chaque marché offre des opportunités différentes selon les secteurs et la conjoncture locale.",
    stat: { value: "10", label: "Bourses africaines sur Afrika Markets" },
    color: "#C9A84C",
    tip: "Le Nigeria (NGX) est la plus grande capitalisation africaine. L'Afrique du Sud (JSE) est la plus liquide. La BRVM offre les meilleurs rendements ajustés au risque.",
  },
  {
    id: 7,
    icon: "🎯",
    category: "Votre stratégie",
    title: "Construire votre profil d'investisseur",
    content: "Chaque investisseur est unique. Votre horizon de placement, votre tolérance au risque et vos objectifs financiers déterminent la stratégie optimale. Un profil Conservateur privilégie les obligations. Un profil Dynamique vise la croissance avec les actions.",
    stat: { value: "4 profils", label: "Conservateur · Prudent · Équilibré · Dynamique" },
    color: "#2ECC71",
    tip: "Notre quiz investisseur de 5 questions vous permettra d'identifier votre profil et de recevoir une allocation personnalisée.",
    cta: true,
  },
]

// ── Composant bougie japonaise animée ────────────────────────
function CandleVisual() {
  const candles = [
    { open: 65, close: 80, high: 85, low: 60, bull: true },
    { open: 80, close: 70, high: 83, low: 65, bull: false },
    { open: 70, close: 85, high: 90, low: 68, bull: true },
    { open: 85, close: 78, high: 88, low: 75, bull: false },
    { open: 78, close: 92, high: 95, low: 76, bull: true },
  ]
  const toY = (v) => 100 - v
  return (
    <div style={{ display: "flex", gap: "8px", alignItems: "flex-end", justifyContent: "center", height: "60px", padding: "4px 0" }}>
      {candles.map((c, i) => (
        <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0" }}>
          {/* Wick haut */}
          <div style={{ width: "1.5px", height: `${(c.high - Math.max(c.open, c.close)) * 0.4}px`, background: c.bull ? "#2ECC71" : "#E74C3C", opacity: 0.7 }}/>
          {/* Corps */}
          <div style={{ width: "14px", height: `${Math.abs(c.close - c.open) * 0.4 + 4}px`, background: c.bull ? "#2ECC71" : "#E74C3C", borderRadius: "2px", opacity: 0.85 }}/>
          {/* Wick bas */}
          <div style={{ width: "1.5px", height: `${(Math.min(c.open, c.close) - c.low) * 0.4}px`, background: c.bull ? "#2ECC71" : "#E74C3C", opacity: 0.7 }}/>
        </div>
      ))}
    </div>
  )
}

// ── Page principale Onboarding ────────────────────────────────
export default function Onboarding({ onComplete }) {
  const [phase, setPhase]           = useState("splash")   // splash | learning | done
  const [slideIndex, setSlideIndex] = useState(0)
  const [animating, setAnimating]   = useState(false)
  const [splashStep, setSplashStep] = useState(0)

  // Splash sequence
  useEffect(() => {
    if (phase !== "splash") return
    const timers = [
      setTimeout(() => setSplashStep(1), 600),
      setTimeout(() => setSplashStep(2), 1400),
      setTimeout(() => setSplashStep(3), 2200),
    ]
    return () => timers.forEach(clearTimeout)
  }, [phase])

  const goNext = () => {
    if (animating) return
    setAnimating(true)
    setTimeout(() => {
      if (slideIndex < SLIDES.length - 1) {
        setSlideIndex(i => i + 1)
      } else {
        setPhase("done")
        if (onComplete) onComplete()
      }
      setAnimating(false)
    }, 300)
  }

  const goPrev = () => {
    if (animating || slideIndex === 0) return
    setAnimating(true)
    setTimeout(() => { setSlideIndex(i => i - 1); setAnimating(false) }, 300)
  }

  const skip = () => {
    setPhase("done")
    if (onComplete) onComplete()
  }

  const slide = SLIDES[slideIndex]
  const progress = ((slideIndex + 1) / SLIDES.length) * 100

  // ── PHASE SPLASH ─────────────────────────────────────────────
  if (phase === "splash") {
    return (
      <div style={{
        minHeight: "100vh", background: "#0A0C0F", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", gap: "2rem", position: "relative",
        overflow: "hidden",
      }}>
        {/* Grille de fond */}
        <div style={{
          position: "absolute", inset: 0,
          backgroundImage: "linear-gradient(rgba(201,168,76,0.04) 1px,transparent 1px), linear-gradient(90deg,rgba(201,168,76,0.04) 1px,transparent 1px)",
          backgroundSize: "50px 50px",
        }}/>
        {/* Glow */}
        <div style={{ position: "absolute", top: "20%", left: "50%", transform: "translateX(-50%)", width: "400px", height: "400px", background: "radial-gradient(ellipse,rgba(201,168,76,0.08),transparent 70%)", pointerEvents: "none" }}/>

        <div style={{ position: "relative", zIndex: 2, textAlign: "center", opacity: splashStep >= 1 ? 1 : 0, transition: "opacity 0.6s ease", transform: splashStep >= 1 ? "translateY(0)" : "translateY(20px)" }}>
          <Logo size={100}/>
        </div>

        <div style={{
          position: "relative", zIndex: 2, textAlign: "center", maxWidth: "480px", padding: "0 2rem",
          opacity: splashStep >= 2 ? 1 : 0, transition: "opacity 0.7s ease 0.2s",
          transform: splashStep >= 2 ? "translateY(0)" : "translateY(16px)",
        }}>
          <p style={{ color: "#8A8580", fontSize: "1rem", lineHeight: 1.7 }}>
            La plateforme d'intelligence boursière africaine pour la <strong style={{ color: "#C9A84C" }}>diaspora</strong> au Canada, France et USA.
          </p>
        </div>

        <div style={{
          position: "relative", zIndex: 2, display: "flex", flexDirection: "column", alignItems: "center", gap: "12px",
          opacity: splashStep >= 3 ? 1 : 0, transition: "opacity 0.7s ease 0.4s",
        }}>
          <button
            onClick={() => setPhase("learning")}
            style={{ background: "#C9A84C", color: "#0A0C0F", border: "none", borderRadius: "8px", padding: "14px 36px", fontSize: "0.95rem", fontWeight: 700, cursor: "pointer", letterSpacing: "0.02em" }}
          >
            Commencer la formation →
          </button>
          <button
            onClick={skip}
            style={{ background: "transparent", color: "#8A8580", border: "none", cursor: "pointer", fontSize: "0.82rem", textDecoration: "underline", textUnderlineOffset: "3px" }}
          >
            Passer directement à la création de profil
          </button>
        </div>

        {/* Indicateurs marchés */}
        <div style={{
          position: "absolute", bottom: "2rem", left: 0, right: 0, zIndex: 2,
          display: "flex", justifyContent: "center", gap: "1.5rem", flexWrap: "wrap",
          opacity: splashStep >= 3 ? 1 : 0, transition: "opacity 0.7s ease 0.6s",
          padding: "0 1rem",
        }}>
          {[
            { label: "BRVM +25%", color: "#2ECC71" },
            { label: "14 Mds FCFA cap.", color: "#C9A84C" },
            { label: "10 bourses", color: "#3498DB" },
            { label: "1325 rapports", color: "#9B59B6" },
          ].map((m, i) => (
            <div key={i} style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "20px", padding: "5px 14px", fontSize: "12px", color: m.color, fontWeight: 600 }}>
              {m.label}
            </div>
          ))}
        </div>
      </div>
    )
  }

  // ── PHASE LEARNING ────────────────────────────────────────────
  return (
    <div style={{ minHeight: "100vh", background: "#0A0C0F", display: "flex", flexDirection: "column", position: "relative" }}>
      {/* Grille */}
      <div style={{ position: "absolute", inset: 0, backgroundImage: "linear-gradient(rgba(201,168,76,0.03) 1px,transparent 1px), linear-gradient(90deg,rgba(201,168,76,0.03) 1px,transparent 1px)", backgroundSize: "50px 50px", pointerEvents: "none" }}/>

      {/* Header */}
      <div style={{ position: "relative", zIndex: 2, padding: "1.25rem 2rem", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "0.5px solid rgba(201,168,76,0.12)" }}>
        <Logo size={36}/>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <span style={{ fontSize: "12px", color: "#8A8580" }}>{slideIndex + 1} / {SLIDES.length}</span>
          <button onClick={skip} style={{ background: "transparent", color: "#8A8580", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", padding: "5px 14px", cursor: "pointer", fontSize: "12px" }}>
            Passer
          </button>
        </div>
      </div>

      {/* Barre de progression */}
      <div style={{ height: "2px", background: "rgba(201,168,76,0.12)", position: "relative", zIndex: 2 }}>
        <div style={{ height: "100%", width: `${progress}%`, background: "#C9A84C", transition: "width 0.4s ease", borderRadius: "0 2px 2px 0" }}/>
      </div>

      {/* Contenu slide */}
      <div style={{
        flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
        padding: "2rem", position: "relative", zIndex: 2,
      }}>
        <div style={{
          maxWidth: "600px", width: "100%",
          opacity: animating ? 0 : 1, transform: animating ? "translateX(20px)" : "translateX(0)",
          transition: "opacity 0.25s, transform 0.25s",
        }}>
          {/* Catégorie */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "1.5rem" }}>
            <span style={{ fontSize: "1.4rem" }}>{slide.icon}</span>
            <span style={{ fontSize: "11px", letterSpacing: "0.12em", textTransform: "uppercase", color: slide.color, fontWeight: 700, border: `1px solid ${slide.color}40`, borderRadius: "20px", padding: "3px 12px", background: `${slide.color}10` }}>
              {slide.category}
            </span>
          </div>

          {/* Titre */}
          <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(1.5rem, 4vw, 2rem)", color: "#F0EDE8", lineHeight: 1.2, marginBottom: "1.25rem" }}>
            {slide.title}
          </h2>

          {/* Contenu */}
          <p style={{ color: "#8A8580", fontSize: "1rem", lineHeight: 1.8, marginBottom: "1.5rem" }}>
            {slide.content}
          </p>

          {/* Visuel bougies si applicable */}
          {slide.visual === "candle" && (
            <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "10px", padding: "1rem", marginBottom: "1.25rem" }}>
              <div style={{ fontSize: "11px", color: "#8A8580", marginBottom: "8px", letterSpacing: "0.06em" }}>GRAPHIQUE EN BOUGIES JAPONAISES</div>
              <CandleVisual/>
              <div style={{ display: "flex", gap: "1rem", marginTop: "8px" }}>
                <span style={{ fontSize: "11px", color: "#2ECC71" }}>▲ Hausse</span>
                <span style={{ fontSize: "11px", color: "#E74C3C" }}>▼ Baisse</span>
                <span style={{ fontSize: "11px", color: "#8A8580" }}>— Mèche = extrêmes</span>
              </div>
            </div>
          )}

          {/* Statistique */}
          <div style={{ background: `${slide.color}08`, border: `1px solid ${slide.color}25`, borderRadius: "12px", padding: "1.25rem", marginBottom: "1.25rem", display: "flex", alignItems: "center", gap: "1rem" }}>
            <div style={{ textAlign: "center", minWidth: "80px" }}>
              <div style={{ fontFamily: "'DM Serif Display', serif", fontSize: "1.8rem", color: slide.color, lineHeight: 1 }}>{slide.stat.value}</div>
            </div>
            <div style={{ fontSize: "13px", color: "#8A8580", lineHeight: 1.5 }}>{slide.stat.label}</div>
          </div>

          {/* Tip */}
          <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderLeft: `3px solid ${slide.color}`, borderRadius: "0 8px 8px 0", padding: "0.875rem 1rem", marginBottom: "2rem" }}>
            <div style={{ fontSize: "10px", letterSpacing: "0.1em", color: slide.color, marginBottom: "4px", textTransform: "uppercase", fontWeight: 700 }}>💡 Le saviez-vous ?</div>
            <div style={{ fontSize: "13px", color: "#8A8580", lineHeight: 1.6 }}>{slide.tip}</div>
          </div>

          {/* Navigation */}
          <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
            {slideIndex > 0 && (
              <button onClick={goPrev} style={{ background: "transparent", color: "#8A8580", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "12px 24px", cursor: "pointer", fontSize: "14px", fontWeight: 600 }}>
                ← Précédent
              </button>
            )}
            <button
              onClick={goNext}
              style={{ flex: 1, background: slide.cta ? "#C9A84C" : "rgba(201,168,76,0.15)", color: slide.cta ? "#0A0C0F" : "#C9A84C", border: `1px solid ${slide.cta ? "#C9A84C" : "rgba(201,168,76,0.3)"}`, borderRadius: "8px", padding: "13px 24px", cursor: "pointer", fontSize: "14px", fontWeight: 700, letterSpacing: "0.02em" }}
            >
              {slideIndex === SLIDES.length - 1 ? "✨ Créer mon profil investisseur →" : "Suivant →"}
            </button>
          </div>

          {/* Points de navigation */}
          <div style={{ display: "flex", justifyContent: "center", gap: "6px", marginTop: "1.5rem" }}>
            {SLIDES.map((_, i) => (
              <button key={i} onClick={() => !animating && setSlideIndex(i)} style={{ width: i === slideIndex ? "24px" : "6px", height: "6px", borderRadius: "3px", background: i === slideIndex ? "#C9A84C" : "rgba(255,255,255,0.15)", border: "none", cursor: "pointer", transition: "all 0.3s", padding: 0 }}/>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
