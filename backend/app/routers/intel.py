"""
Intel Router — Afrika Markets Intelligence
GET /intel/warroom                    → données géopolitiques UEMOA (ACLED + IMF + fallback)
GET /intel/sgi/ranking                → classement SGI pondéré
POST /intel/sgi/reco                  → recommandation SGI personnalisée
GET /intel/opcvm                      → liste OPCVM BRVM
GET /intel/plans                      → description des plans tarifaires
GET /intel/international/forex/xof    → taux EUR/XOF (fixe) + USD/XOF + CAD/XOF
GET /intel/international/{ticker}     → OHLCV + indicateurs techniques yfinance
"""
import json
import logging
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from backend.app.core.database import get_db
from backend.app.models.market_models import IntlMarketCache

logger = logging.getLogger(__name__)

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


# ── Marchés Internationaux (yfinance) ────────────────────────

def _ma(prices: list, period: int) -> list:
    result = []
    for i in range(len(prices)):
        window = prices[max(0, i - period + 1): i + 1]
        result.append(sum(window) / len(window))
    return result


def _rsi(prices: list, period: int = 14) -> list:
    if len(prices) < 2:
        return [None] * len(prices)
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains  = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    alpha  = 1.0 / period
    avg_g, avg_l = gains[0], losses[0]
    rsi_vals = [None]
    for i in range(1, len(gains)):
        avg_g = alpha * gains[i] + (1 - alpha) * avg_g
        avg_l = alpha * losses[i] + (1 - alpha) * avg_l
        if avg_l == 0:
            rsi_vals.append(100.0)
        else:
            rsi_vals.append(round(100 - 100 / (1 + avg_g / avg_l), 2))
    return rsi_vals


def _mfi(prices: list, opens: list, volumes: list, period: int = 14) -> list:
    n      = len(prices)
    highs  = [max(prices[i], opens[i]) for i in range(n)]
    lows   = [min(prices[i], opens[i]) for i in range(n)]
    tps    = [(highs[i] + lows[i] + prices[i]) / 3.0 for i in range(n)]
    raw_mf = [tps[i] * volumes[i] for i in range(n)]
    result = [None] * n
    for i in range(period, n):
        pos = sum(raw_mf[j] for j in range(i - period, i) if j > 0 and tps[j] > tps[j - 1])
        neg = sum(raw_mf[j] for j in range(i - period, i) if j > 0 and tps[j] < tps[j - 1])
        if neg == 0:
            result[i] = 100.0
        elif pos == 0:
            result[i] = 0.0
        else:
            result[i] = round(100 - 100 / (1 + pos / neg), 2)
    return result


class _TimeoutSession:
    """Wrapper requests.Session avec timeout fixe et User-Agent navigateur."""
    def __init__(self, timeout: int = 10):
        import requests as _req
        self._s = _req.Session()
        self._s.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
        self._timeout = timeout

    def get(self, url, **kwargs):
        kwargs.setdefault("timeout", self._timeout)
        return self._s.get(url, **kwargs)

    def post(self, url, **kwargs):
        kwargs.setdefault("timeout", self._timeout)
        return self._s.post(url, **kwargs)

    def __getattr__(self, name):
        return getattr(self._s, name)


def _yf_fetch(ticker: str, period: str):
    """Télécharge l'historique via yf.Ticker avec session navigateur + timeout 10s."""
    import yfinance as yf
    sess = _TimeoutSession(timeout=10)
    df = yf.Ticker(ticker, session=sess).history(period=period, auto_adjust=True)
    return df


@router.get("/international/forex/xof")
async def get_forex_xof(db: AsyncSession = Depends(get_db)):
    """Taux EUR/XOF (parité fixe BCEAO) + USD/XOF + CAD/XOF.
    Source principale : table intl_market_cache (pré-fetchée toutes les 6h).
    Fallback : yfinance live si cache manquant.
    """
    EUR_XOF = 655.957
    eurusd, usdcad = 1.08, 1.36  # valeurs par défaut conservatrices

    # 1. Lire depuis le cache DB
    eu_row = await db.get(IntlMarketCache, "EURUSD=X")
    uc_row = await db.get(IntlMarketCache, "USDCAD=X")

    if eu_row and uc_row:
        try:
            eu_data = json.loads(eu_row.data_json)
            uc_data = json.loads(uc_row.data_json)
            eurusd  = eu_data["last"]["cours"]
            usdcad  = uc_data["last"]["cours"]
        except Exception:
            pass
    else:
        # 2. Fallback live yfinance (uniquement si cache vide)
        try:
            eu_df = _yf_fetch("EURUSD=X", "5d")
            uc_df = _yf_fetch("USDCAD=X", "5d")
            if not eu_df.empty:
                eurusd = float(eu_df["Close"].dropna().iloc[-1])
            if not uc_df.empty:
                usdcad = float(uc_df["Close"].dropna().iloc[-1])
        except Exception as exc:
            logger.warning("[forex/xof] fallback yfinance échoué : %s", exc)

    return {
        "eur_xof": EUR_XOF,
        "usd_xof": round(EUR_XOF / eurusd, 2),
        "cad_xof": round(EUR_XOF / eurusd / usdcad, 2),
        "eurusd":  round(eurusd, 4),
        "usdcad":  round(usdcad, 4),
    }


@router.get("/international/{ticker:path}")
async def get_international_ticker(
    ticker: str,
    days: int = Query(default=90, ge=30, le=365),
    db: AsyncSession = Depends(get_db),
):
    """OHLCV + MA/RSI/MFI pour un ticker.
    Source principale : table intl_market_cache (pré-fetchée toutes les 6h).
    Fallback : yfinance live si cache manquant.
    """
    # 1. Chercher dans le cache DB
    cached = await db.get(IntlMarketCache, ticker)
    if cached:
        try:
            payload = json.loads(cached.data_json)
            cutoff  = str(date.today() - timedelta(days=days))
            sliced  = [row for row in payload["data"] if row["date"] >= cutoff]
            if sliced:
                return {
                    "ticker":     ticker,
                    "days":       days,
                    "count":      len(sliced),
                    "data":       sliced,
                    "last":       payload["last"],
                    "cached_at":  cached.fetched_at.isoformat(),
                }
        except Exception as exc:
            logger.warning("[international] %s — erreur lecture cache DB : %s", ticker, exc)

    # 2. Fallback live yfinance
    try:
        df = _yf_fetch(ticker, f"{days}d")
        if df.empty:
            raise HTTPException(503, detail=f"Données indisponibles pour {ticker} — cache en cours de population (réessayez dans 2 min)")

        df      = df.dropna(subset=["Close"])
        prices  = [float(v) for v in df["Close"]]
        opens   = [float(v) for v in df["Open"]]
        volumes = [float(v) for v in df["Volume"]]
        dates   = [str(d.date()) for d in df.index]
        n       = len(prices)

        if n == 0:
            raise HTTPException(404, detail=f"Données vides pour {ticker}")

        ma16  = _ma(prices, min(16, n))
        ma19  = _ma(prices, min(19, n))
        ma246 = _ma(prices, min(246, n))
        ma361 = _ma(prices, min(361, n))
        rsi   = _rsi(prices)
        mfi   = _mfi(prices, opens, volumes)

        data = []
        for i in range(n):
            data.append({
                "date":   dates[i],
                "cours":  round(prices[i], 4),
                "volume": volumes[i],
                "ma16":   round(ma16[i], 4)  if ma16[i]  is not None else None,
                "ma19":   round(ma19[i], 4)  if ma19[i]  is not None else None,
                "ma246":  round(ma246[i], 4) if ma246[i] is not None else None,
                "ma361":  round(ma361[i], 4) if ma361[i] is not None else None,
                "rsi":    rsi[i],
                "mfi":    mfi[i],
            })

        last = data[-1]
        r, m = last["rsi"] or 50, last["mfi"] or 50
        score, reasons = 0, []
        if r < 30:   score += 2; reasons.append("RSI survendu (<30)")
        elif r < 45: score += 1; reasons.append("RSI zone basse (<45)")
        elif r > 70: score -= 2; reasons.append("RSI suracheté (>70)")
        elif r > 55: score -= 1; reasons.append("RSI zone haute (>55)")
        if m < 20:   score += 2; reasons.append("MFI survendu (<20)")
        elif m > 80: score -= 2; reasons.append("MFI suracheté (>80)")
        if all(v is not None for v in [last["ma16"], last["ma19"], last["ma246"], last["ma361"]]):
            if last["ma16"] > last["ma19"]:
                score += 1; reasons.append("MA16 > MA19 (haussier court terme)")
            else:
                score -= 1; reasons.append("MA16 < MA19 (baissier court terme)")
            score += 1 if last["ma19"] > last["ma246"] else -1

        if score >= 3:    sig_label, sig_color = "Achat fort",    "#00CC66"
        elif score >= 1:  sig_label, sig_color = "Achat modéré",  "#FFD700"
        elif score == 0:  sig_label, sig_color = "Neutre",         "#888888"
        elif score >= -2: sig_label, sig_color = "Vente modérée", "#FF6B35"
        else:             sig_label, sig_color = "Vente forte",   "#FF4444"

        return {
            "ticker": ticker,
            "days":   days,
            "count":  n,
            "data":   data,
            "last":   {**last, "label": sig_label, "color": sig_color,
                       "score": score, "reasons": reasons},
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[international] %s — %s: %s", ticker, type(exc).__name__, exc)
        raise HTTPException(503, detail="Données temporairement indisponibles — cache en cours de population. Réessayez dans 2 minutes.")
