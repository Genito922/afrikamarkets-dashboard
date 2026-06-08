"""
African-Markets Router
  GET /african-markets/listed                    → 47 titres BRVM
  GET /african-markets/company/{code}            → profil société BRVM
  GET /african-markets/currencies                → devises africaines + XOF
  GET /african-markets/news                      → actualités BRVM

  GET /african-markets/exchanges                 → catalogue 9 bourses africaines
  GET /african-markets/exchanges/{slug}/stocks   → titres cotés (african-markets.com)
  GET /african-markets/exchanges/{slug}/sgis     → annuaire courtiers/SGI
  GET /african-markets/ai-reco                   → recommandation IA (technique + macro)

Cache 15 min en mémoire pour les scrapes.
"""
import asyncio
import json
import logging
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/african-markets", tags=["african-markets"])

# ── Cache léger ───────────────────────────────────────────────────────────────
_CACHE: dict[str, tuple[float, object]] = {}
_TTL = 900  # 15 min


def _cache_get(key: str):
    if key in _CACHE:
        ts, val = _CACHE[key]
        if time.time() - ts < _TTL:
            return val
    return None


def _cache_set(key: str, val):
    _CACHE[key] = (time.time(), val)


# ── BRVM endpoints (existants) ────────────────────────────────────────────────

@router.get("/listed")
async def get_listed():
    cached = _cache_get("listed")
    if cached is not None:
        return {"source": "cache", "data": cached}
    try:
        from backend.app.pipeline.african_markets import fetch_brvm_listed
        data = await asyncio.get_event_loop().run_in_executor(None, fetch_brvm_listed)
    except Exception as exc:
        logger.error("[AM router] /listed — %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
    _cache_set("listed", data)
    return {"source": "live", "count": len(data), "data": data}


@router.get("/company/{code}")
async def get_company_profile(code: str):
    code = code.upper()
    key  = f"company:{code}"
    cached = _cache_get(key)
    if cached is not None:
        return {"source": "cache", "data": cached}
    try:
        from backend.app.pipeline.african_markets import fetch_company_profile
        data = await asyncio.get_event_loop().run_in_executor(
            None, fetch_company_profile, code
        )
    except Exception as exc:
        logger.error("[AM router] /company/%s — %s", code, exc)
        raise HTTPException(status_code=502, detail=str(exc))
    _cache_set(key, data)
    return {"source": "live", "data": data}


@router.get("/currencies")
async def get_currencies():
    cached = _cache_get("currencies")
    if cached is not None:
        return {"source": "cache", "data": cached}
    try:
        from backend.app.pipeline.african_markets import fetch_currencies
        data = await asyncio.get_event_loop().run_in_executor(None, fetch_currencies)
    except Exception as exc:
        logger.error("[AM router] /currencies — %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
    _cache_set("currencies", data)
    return {"source": "live", "count": len(data), "data": data}


@router.get("/news")
async def get_news(limit: int = Query(20, ge=1, le=50)):
    key = f"news:{limit}"
    cached = _cache_get(key)
    if cached is not None:
        return {"source": "cache", "data": cached}
    try:
        from backend.app.pipeline.african_markets import fetch_brvm_news
        data = await asyncio.get_event_loop().run_in_executor(
            None, fetch_brvm_news, limit
        )
    except Exception as exc:
        logger.error("[AM router] /news — %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
    _cache_set(key, data)
    return {"source": "live", "count": len(data), "data": data}


# ── Catalogue bourses africaines ──────────────────────────────────────────────

@router.get("/exchanges")
async def get_exchanges():
    """Catalogue des 9 bourses africaines avec métadonnées."""
    from backend.app.pipeline.african_markets import AFRICAN_EXCHANGES
    return {"count": len(AFRICAN_EXCHANGES), "exchanges": AFRICAN_EXCHANGES}


@router.get("/exchanges/{slug}/stocks")
async def get_exchange_stocks(slug: str):
    """Titres cotés sur une bourse africaine (scrape african-markets.com)."""
    key = f"stocks:{slug}"
    cached = _cache_get(key)
    if cached is not None:
        return {"source": "cache", "slug": slug, "data": cached}
    try:
        from backend.app.pipeline.african_markets import fetch_exchange_listed
        data = await asyncio.get_event_loop().run_in_executor(
            None, fetch_exchange_listed, slug
        )
    except Exception as exc:
        logger.error("[AM router] /exchanges/%s/stocks — %s", slug, exc)
        raise HTTPException(status_code=502, detail=str(exc))
    _cache_set(key, data)
    return {"source": "live", "slug": slug, "count": len(data), "data": data}


@router.get("/exchanges/{slug}/sgis")
async def get_exchange_sgis(slug: str):
    """Annuaire des courtiers/SGI pour une bourse africaine."""
    from backend.app.pipeline.african_markets import AFRICAN_SGIS, EXCHANGE_BY_SLUG
    if slug not in EXCHANGE_BY_SLUG:
        raise HTTPException(status_code=404, detail=f"Bourse inconnue : {slug}")
    sgis = AFRICAN_SGIS.get(slug, [])
    return {
        "slug":     slug,
        "exchange": EXCHANGE_BY_SLUG[slug]["nom"],
        "count":    len(sgis),
        "sgis":     sgis,
    }


# ── Recommandation IA ─────────────────────────────────────────────────────────

# Contexte macro par marché (données statiques — mise à jour manuelle si nécessaire)
_MACRO_CONTEXT = {
    "jse":  {"pib_growth": 0.6,  "inflation": 5.2, "risque": 4, "note": "Marché développé, plus volatile récemment (rand faible)", "outlook": "Neutre"},
    "ngx":  {"pib_growth": 3.2,  "inflation": 33.0,"risque": 6, "note": "Pression NGN, mais rebond attendu post-réformes Tinubu", "outlook": "Risqué / Opportunité"},
    "gse":  {"pib_growth": 2.9,  "inflation": 23.0,"risque": 5, "note": "Stabilisation post-crise dette 2022, FMI programme actif", "outlook": "Neutre"},
    "nse":  {"pib_growth": 5.0,  "inflation": 6.5, "risque": 3, "note": "Économie stable, hub technologique est-africain en croissance", "outlook": "Positif"},
    "egx":  {"pib_growth": 4.2,  "inflation": 35.0,"risque": 5, "note": "Forte dévaluation EGP, mais réformes FMI en cours", "outlook": "Neutre/Risqué"},
    "bvc":  {"pib_growth": 3.5,  "inflation": 2.5, "risque": 2, "note": "Économie stable, diversifiée, hub Afrique du Nord", "outlook": "Positif"},
    "bvmt": {"pib_growth": 1.8,  "inflation": 9.0, "risque": 4, "note": "Pression budgétaire, mais amélioration 2024", "outlook": "Neutre"},
    "brvm": {"pib_growth": 6.0,  "inflation": 3.0, "risque": 3, "note": "Zone UEMOA stable, parité XOF fixe, croissance Sénégal/CI", "outlook": "Positif"},
    "dse":  {"pib_growth": 5.5,  "inflation": 3.8, "risque": 3, "note": "Croissance solide, marché peu liquide mais sous-évalué", "outlook": "Positif"},
}

# Mapping yf_index → slug pour récupérer le cache
_YF_TO_SLUG = {
    "EZA":        "jse",
    "^NGSEINDEX": "ngx",
    "^GGSECI":    "gse",
    "^NBI":       "nse",
    "^CASE":      "egx",
}


def _score_to_label(score: int) -> tuple[str, str]:
    if score >= 3:    return "Achat fort",    "#00CC66"
    if score >= 1:    return "Achat modéré",  "#FFD700"
    if score == 0:    return "Neutre",         "#888888"
    if score >= -2:   return "Vente modérée", "#FF6B35"
    return               "Vente forte",   "#FF4444"


def _generate_ai_text(exchange: dict, macro: dict, tech_last: dict | None, label: str) -> str:
    """Génère un texte de recommandation contextualisé."""
    nom  = exchange["nom"]
    pays = exchange["pays"]
    out  = macro["outlook"]
    note = macro["note"]

    intro = f"**{nom} ({pays})** — Outlook : *{out}*. {note}."

    if tech_last:
        rsi = tech_last.get("rsi") or 50
        ma16 = tech_last.get("ma16")
        ma246 = tech_last.get("ma246")
        cours = tech_last.get("cours")

        tech_parts = []
        if rsi < 35:
            tech_parts.append(f"RSI à {rsi:.0f} indique une zone de survente — rebond technique possible.")
        elif rsi > 65:
            tech_parts.append(f"RSI à {rsi:.0f} en zone de surachat — prudence à court terme.")
        else:
            tech_parts.append(f"RSI neutre ({rsi:.0f}).")

        if ma16 and ma246 and cours:
            if cours > ma246:
                tech_parts.append("Le cours est au-dessus de la MA246 — tendance long terme haussière.")
            else:
                tech_parts.append("Le cours est sous la MA246 — tendance long terme à surveiller.")

        if tech_parts:
            intro += " " + " ".join(tech_parts)

    # Signal global
    signals = {
        "Achat fort":   "Position initiale ou renforcement recommandé. Gestion du risque devise obligatoire.",
        "Achat modéré": "Entrée progressive possible. Diversification prudente dans l'exposition africaine.",
        "Neutre":       "Attente de confirmation de tendance. Surveiller les données macro locales.",
        "Vente modérée":"Réduction d'exposition conseillée. Conserver uniquement les positions solides.",
        "Vente forte":  "Sortie ou couverture recommandée. Conditions défavorables à court terme.",
    }
    intro += f"\n\n**Signal** : {label}. {signals.get(label, '')}"
    return intro


@router.get("/ai-reco")
async def get_ai_reco(db: AsyncSession = Depends(get_db)):
    """
    Recommandations IA sur les marchés africains.
    Combine signaux techniques (cache yfinance) + contexte macro curated.
    """
    from backend.app.models.market_models import IntlMarketCache
    from backend.app.pipeline.african_markets import AFRICAN_EXCHANGES, EXCHANGE_BY_SLUG

    recommendations = []

    for exchange in AFRICAN_EXCHANGES:
        slug     = exchange["slug"]
        macro    = _MACRO_CONTEXT.get(slug, {"pib_growth": 0, "inflation": 0, "risque": 5,
                                              "note": "", "outlook": "Neutre"})
        yf_index = exchange.get("yf_index")
        tech_last = None
        score     = 0
        reasons   = []

        # ── Signaux techniques depuis le cache yfinance ──────
        if yf_index:
            cached_row = await db.get(IntlMarketCache, yf_index)
            if cached_row:
                try:
                    payload   = json.loads(cached_row.data_json)
                    tech_last = payload.get("last", {})
                    score     = tech_last.get("score", 0)
                    reasons   = tech_last.get("reasons", [])
                except Exception:
                    pass

        # ── Ajustement macro ─────────────────────────────────
        outlook = macro["outlook"]
        if "Positif" in outlook:
            score += 1; reasons.append(f"Outlook macro positif ({exchange['pays']})")
        elif "Risqué" in outlook:
            score -= 1; reasons.append(f"Risque macro élevé ({exchange['pays']})")

        # Bonus stabilité
        risque = macro["risque"]
        if risque <= 2:
            score += 1; reasons.append("Stabilité politique/monétaire élevée")
        elif risque >= 7:
            score -= 1; reasons.append("Risque géopolitique élevé")

        label, color = _score_to_label(score)
        ai_text = _generate_ai_text(exchange, macro, tech_last, label)

        recommendations.append({
            "slug":       slug,
            "nom":        exchange["nom"],
            "pays":       exchange["pays"],
            "flag":       exchange["flag"],
            "devise":     exchange["devise"],
            "cap_usd_b":  exchange["cap_usd_b"],
            "score":      score,
            "label":      label,
            "color":      color,
            "reasons":    reasons,
            "ai_text":    ai_text,
            "macro": {
                "pib_growth": macro["pib_growth"],
                "inflation":  macro["inflation"],
                "risque":     macro["risque"],
                "outlook":    macro["outlook"],
            },
            "tech_last":  tech_last,
            "has_cache":  tech_last is not None,
        })

    # Trier par score décroissant
    recommendations.sort(key=lambda r: r["score"], reverse=True)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "count":        len(recommendations),
        "recommendations": recommendations,
    }
