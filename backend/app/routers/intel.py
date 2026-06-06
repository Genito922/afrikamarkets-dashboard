"""
Intel Router — Afrika Markets Intelligence
GET /intel/warroom       → données géopolitiques UEMOA (ACLED + IMF + fallback)
GET /intel/sgi/ranking   → classement SGI pondéré
POST /intel/sgi/reco     → recommandation SGI personnalisée
GET /intel/opcvm         → liste OPCVM BRVM
GET /plans               → description des plans tarifaires
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/intel", tags=["intel"])

# ── War Room — données UEMOA ─────────────────────────────────

UEMOA_DATA = [
    {
        "iso2": "CI", "nom": "Côte d'Ivoire", "flag": "🇨🇮",
        "impact_brvm": "fort", "risque": 2, "note": "Stable",
        "events_90d": 8,   "gdp_growth": 6.5, "inflation": 3.2,
        "situation": "Croissance soutenue par la filière cacao et les investissements publics. Stabilité politique post-2020.",
        "market_impact": "Impact direct fort sur la BRVM (60% de la capitalisation)",
    },
    {
        "iso2": "SN", "nom": "Sénégal", "flag": "🇸🇳",
        "impact_brvm": "fort", "risque": 2, "note": "Stable",
        "events_90d": 5,   "gdp_growth": 8.3, "inflation": 2.8,
        "situation": "Transition présidentielle réussie. Début d'exploitation pétrolière (Sangomar). Croissance élevée attendue.",
        "market_impact": "Fort impact — 2ème plus grande économie UEMOA",
    },
    {
        "iso2": "BF", "nom": "Burkina Faso", "flag": "🇧🇫",
        "impact_brvm": "moyen", "risque": 8, "note": "Transition militaire",
        "events_90d": 142, "gdp_growth": 2.1, "inflation": 5.4,
        "situation": "Transition militaire en cours. Instabilité sécuritaire au Nord. Retrait de l'espace CEDEAO.",
        "market_impact": "Impact indirect via sentiment régional",
    },
    {
        "iso2": "ML", "nom": "Mali", "flag": "🇲🇱",
        "impact_brvm": "moyen", "risque": 8, "note": "Transition militaire",
        "events_90d": 118, "gdp_growth": 3.2, "inflation": 6.1,
        "situation": "Transition militaire prolongée. Alliance avec la Russie (Wagner). Sanctions CEDEAO partiellement levées.",
        "market_impact": "Faible exposition BRVM directe",
    },
    {
        "iso2": "NE", "nom": "Niger", "flag": "🇳🇪",
        "impact_brvm": "faible", "risque": 9, "note": "Transition militaire",
        "events_90d": 87,  "gdp_growth": 6.9, "inflation": 4.2,
        "situation": "Coup d'État juillet 2023. Sanctions CEDEAO. Exportations pétrole en cours via pipeline Nigéria.",
        "market_impact": "Très faible exposition BRVM",
    },
    {
        "iso2": "BJ", "nom": "Bénin", "flag": "🇧🇯",
        "impact_brvm": "moyen", "risque": 3, "note": "Stable",
        "events_90d": 22,  "gdp_growth": 6.0, "inflation": 1.8,
        "situation": "Stabilité politique. Programmes d'investissement port de Cotonou. Légère tension sécurité nord.",
        "market_impact": "Impact modéré — hub régional",
    },
    {
        "iso2": "TG", "nom": "Togo", "flag": "🇹🇬",
        "impact_brvm": "moyen", "risque": 4, "note": "Stable",
        "events_90d": 12,  "gdp_growth": 5.5, "inflation": 4.1,
        "situation": "Stabilité relative. Hub logistique Lomé actif. Légère pression sociale.",
        "market_impact": "Impact modéré",
    },
    {
        "iso2": "GW", "nom": "Guinée-Bissau", "flag": "🇬🇼",
        "impact_brvm": "faible", "risque": 5, "note": "Fragile",
        "events_90d": 18,  "gdp_growth": 4.5, "inflation": 3.9,
        "situation": "Instabilité institutionnelle récurrente. Economie de subsistance dominée par la noix de cajou.",
        "market_impact": "Très faible exposition BRVM",
    },
]

RISK_COLOR = {1: "#00CC66", 2: "#22c55e", 3: "#84cc16", 4: "#eab308",
              5: "#f97316", 6: "#f97316", 7: "#ef4444", 8: "#dc2626", 9: "#b91c1c", 10: "#7f1d1d"}


@router.get("/warroom")
async def get_warroom():
    out = []
    for c in UEMOA_DATA:
        out.append({**c, "risk_color": RISK_COLOR.get(c["risque"], "#888888")})
    return {"source": "static+IMF_2025", "updated_at": "2025-06-01", "data": out}


# ── SGI — données statiques ──────────────────────────────────

SGI_DATA = [
    {
        "nom": "NSIA Finance", "pays": "Côte d'Ivoire", "founded": 2001,
        "courtage": "0.80%", "depot_min": 100_000, "presence_diaspora": True,
        "ouverture_en_ligne": True, "app_mobile": True,
        "url": "https://www.nsiafinance.com",
        "scores": {"frais": 8.0, "facilite_ouverture": 9.0, "app_mobile": 9.5,
                   "service_client": 8.5, "recherche": 8.0, "rapidite": 8.5, "reputation": 9.0},
        "strengths": ["Ouverture 100% en ligne", "App mobile bien notée", "Présence diaspora Canada/France"],
        "weaknesses": ["Frais légèrement supérieurs", "Support heures ouvrées uniquement"],
    },
    {
        "nom": "Hudson & Cie", "pays": "Côte d'Ivoire", "founded": 1998,
        "courtage": "0.70%", "depot_min": 500_000, "presence_diaspora": False,
        "ouverture_en_ligne": False, "app_mobile": False,
        "url": "https://www.hudsonetcie.com",
        "scores": {"frais": 9.0, "facilite_ouverture": 4.5, "app_mobile": 3.0,
                   "service_client": 9.0, "recherche": 9.5, "rapidite": 7.5, "reputation": 9.5},
        "strengths": ["Recherche de pointe", "Clientèle institutionnelle", "Réputation historique BRVM"],
        "weaknesses": ["Pas d'ouverture en ligne", "Dépôt minimum élevé", "Non adapté diaspora"],
    },
    {
        "nom": "CGF Bourse", "pays": "Côte d'Ivoire", "founded": 1994,
        "courtage": "0.65%", "depot_min": 50_000, "presence_diaspora": False,
        "ouverture_en_ligne": True, "app_mobile": False,
        "url": "https://www.cgfbourse.com",
        "scores": {"frais": 9.5, "facilite_ouverture": 7.0, "app_mobile": 2.0,
                   "service_client": 7.5, "recherche": 7.5, "rapidite": 8.0, "reputation": 8.5},
        "strengths": ["Frais parmi les plus bas BRVM", "Dépôt minimum accessible", "Ancienneté et fiabilité"],
        "weaknesses": ["Pas d'application mobile", "Interface web datée"],
    },
    {
        "nom": "BOA Capital Securities", "pays": "Mali", "founded": 2010,
        "courtage": "0.85%", "depot_min": 100_000, "presence_diaspora": True,
        "ouverture_en_ligne": True, "app_mobile": True,
        "url": "https://www.boacapitalsecurities.com",
        "scores": {"frais": 7.5, "facilite_ouverture": 8.5, "app_mobile": 8.0,
                   "service_client": 8.0, "recherche": 7.0, "rapidite": 8.5, "reputation": 8.0},
        "strengths": ["Réseau bancaire BOA (13 pays)", "Idéal débutants", "Accès diaspora Afrique Ouest"],
        "weaknesses": ["Frais légèrement élevés", "Recherche limitée"],
    },
    {
        "nom": "Coris Bourse", "pays": "Burkina Faso", "founded": 2008,
        "courtage": "0.75%", "depot_min": 75_000, "presence_diaspora": True,
        "ouverture_en_ligne": True, "app_mobile": False,
        "url": "https://www.corisbourse.com",
        "scores": {"frais": 8.5, "facilite_ouverture": 7.5, "app_mobile": 3.5,
                   "service_client": 7.5, "recherche": 6.5, "rapidite": 7.5, "reputation": 7.5},
        "strengths": ["Solide réseau Coris Bank", "Bon rapport qualité/prix"],
        "weaknesses": ["Pas d'app mobile", "Recherche macro limitée"],
    },
    {
        "nom": "Africabourse", "pays": "Côte d'Ivoire", "founded": 2015,
        "courtage": "0.72%", "depot_min": 50_000, "presence_diaspora": True,
        "ouverture_en_ligne": True, "app_mobile": True,
        "url": "https://www.africabourse.net",
        "scores": {"frais": 8.8, "facilite_ouverture": 9.0, "app_mobile": 8.5,
                   "service_client": 7.0, "recherche": 6.0, "rapidite": 9.0, "reputation": 7.0},
        "strengths": ["Plateforme digitale moderne", "Exécution rapide des ordres"],
        "weaknesses": ["Structure plus récente", "Recherche en développement"],
    },
    {
        "nom": "Sogebourse", "pays": "Côte d'Ivoire", "founded": 2000,
        "courtage": "0.90%", "depot_min": 200_000, "presence_diaspora": False,
        "ouverture_en_ligne": False, "app_mobile": False,
        "url": "https://www.sogebourse.sn",
        "scores": {"frais": 7.0, "facilite_ouverture": 5.0, "app_mobile": 2.0,
                   "service_client": 8.5, "recherche": 8.5, "rapidite": 7.0, "reputation": 9.0},
        "strengths": ["Appui Société Générale", "Service client premium"],
        "weaknesses": ["Frais élevés", "Pas d'ouverture en ligne"],
    },
    {
        "nom": "Impaxis Securities", "pays": "Sénégal", "founded": 2007,
        "courtage": "0.80%", "depot_min": 150_000, "presence_diaspora": True,
        "ouverture_en_ligne": True, "app_mobile": False,
        "url": "https://www.impaxis.com",
        "scores": {"frais": 8.0, "facilite_ouverture": 7.0, "app_mobile": 2.0,
                   "service_client": 8.0, "recherche": 9.0, "rapidite": 7.5, "reputation": 8.5},
        "strengths": ["Recherche macroéconomique reconnue", "Présence forte au Sénégal"],
        "weaknesses": ["Pas d'app mobile", "Dépôt minimum modéré"],
    },
]

WEIGHTS = {"frais": 0.25, "facilite_ouverture": 0.15, "app_mobile": 0.10,
           "service_client": 0.15, "recherche": 0.15, "rapidite": 0.10, "reputation": 0.10}


def _calc_score(sgi: dict) -> float:
    return round(sum(sgi["scores"][k] * w for k, w in WEIGHTS.items()), 2)


@router.get("/sgi/ranking")
async def get_sgi_ranking():
    ranked = sorted(
        [{"rank": 0, **s, "score_global": _calc_score(s)} for s in SGI_DATA],
        key=lambda x: x["score_global"], reverse=True
    )
    for i, s in enumerate(ranked):
        s["rank"] = i + 1
    return {"count": len(ranked), "data": ranked}


class RecoRequest(BaseModel):
    pays: str = "Canada"
    montant: float = 10000
    experience: str = "beginner"    # beginner, intermediate, expert
    style: str = "mixed"            # active, longterm, mixed
    advice: str = "yes"             # yes, no


@router.post("/sgi/reco")
async def get_sgi_reco(req: RecoRequest):
    diaspora_pays = ["Canada", "France", "Belgique", "Suisse"]
    diaspora = req.pays in diaspora_pays
    amount_fcfa = req.montant * 655.957

    def profile_score(sgi):
        s = _calc_score(sgi)
        if diaspora and sgi["presence_diaspora"]:          s += 0.5
        if amount_fcfa < 500_000 and sgi["depot_min"] <= 100_000: s += 0.3
        if req.experience == "beginner" and sgi["ouverture_en_ligne"]: s += 0.3
        if req.experience == "beginner" and sgi["app_mobile"]:         s += 0.2
        if req.advice == "yes" and sgi["scores"]["service_client"] >= 8: s += 0.4
        if req.style == "active"   and sgi["scores"]["rapidite"]  >= 8.5: s += 0.3
        if req.style == "longterm" and sgi["scores"]["recherche"] >= 8.5: s += 0.3
        if req.experience == "expert" and sgi["scores"]["recherche"] >= 9: s += 0.3
        return round(min(s, 10), 2)

    top3 = sorted(SGI_DATA, key=profile_score, reverse=True)[:3]
    return {"data": [{"rank": i + 1, **s, "profile_score": profile_score(s)} for i, s in enumerate(top3)]}


# ── OPCVM ─────────────────────────────────────────────────────

OPCVM_DATA = [
    {"nom": "SICAV Croissance BRVM", "gestionnaire": "NSIA Finance",     "type": "Actions",  "perf_ytd": 12.3,  "actif_net": "4.2 Mds FCFA", "risk": 3},
    {"nom": "FCP Équilibre Afrique",  "gestionnaire": "Hudson & Cie",     "type": "Mixte",    "perf_ytd": 8.7,   "actif_net": "2.8 Mds FCFA", "risk": 2},
    {"nom": "SICAV Monétaire UEMOA",  "gestionnaire": "CGF Bourse",       "type": "Monétaire","perf_ytd": 4.1,   "actif_net": "7.5 Mds FCFA", "risk": 1},
    {"nom": "FCP Dividendes BRVM",    "gestionnaire": "Africabourse",     "type": "Actions",  "perf_ytd": 9.8,   "actif_net": "1.6 Mds FCFA", "risk": 3},
    {"nom": "SICAV Obligataire CI",   "gestionnaire": "Impaxis Securities","type": "Obligations","perf_ytd": 6.2, "actif_net": "3.1 Mds FCFA","risk": 1},
    {"nom": "FCP Sénégal Opportunités","gestionnaire": "Impaxis Securities","type": "Actions", "perf_ytd": 15.4, "actif_net": "0.9 Mds FCFA", "risk": 4},
    {"nom": "SICAV Capital Garanti",  "gestionnaire": "Sogebourse",       "type": "Garanti",  "perf_ytd": 3.5,   "actif_net": "5.8 Mds FCFA", "risk": 1},
]


@router.get("/opcvm")
async def get_opcvm():
    return {"count": len(OPCVM_DATA), "data": OPCVM_DATA}


# ── Plans ────────────────────────────────────────────────────

@router.get("/plans")
async def get_plans():
    return {"data": [
        {"id": "free",    "name": "Free",    "price_cad": 0,      "price_usd": 0,
         "features": ["Cours BRVM live","Top 5 / Flop 5","Indices","Secteurs"]},
        {"id": "starter", "name": "Starter", "price_cad": 29.99,  "price_usd": 22,
         "features": ["Tout Free +","Historique 365j","Analyse technique MA/RSI/MFI","Portefeuille simulateur"]},
        {"id": "pro",     "name": "Pro",     "price_cad": 74.99,  "price_usd": 55,
         "features": ["Tout Starter +","War Room géopolitique","SGI & OPCVM Intelligence","Alertes personnalisées"]},
        {"id": "expert",  "name": "Expert",  "price_cad": 199.99, "price_usd": 148,
         "features": ["Tout Pro +","Marchés Internationaux","API accès direct","Support prioritaire"]},
    ]}
