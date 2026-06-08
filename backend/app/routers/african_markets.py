"""
African-Markets.com Router
  GET /african-markets/listed            → liste 47 titres BRVM (cours temps réel)
  GET /african-markets/company/{code}    → profil société (annonces, dividendes, rapports)
  GET /african-markets/currencies        → devises africaines + XOF
  GET /african-markets/news              → actualités BRVM

Résultats mis en cache 15 min en mémoire (pas besoin de DB).
"""
import asyncio
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/african-markets", tags=["african-markets"])

# ── Cache léger en mémoire ────────────────────────────────────────────────────
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


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/listed")
async def get_listed():
    """Liste des 47 titres BRVM avec cours, variation, P/E depuis african-markets.com."""
    cached = _cache_get("listed")
    if cached is not None:
        return {"source": "cache", "data": cached}

    try:
        from backend.app.pipeline.african_markets import fetch_brvm_listed
        data = await asyncio.get_event_loop().run_in_executor(None, fetch_brvm_listed)
    except Exception as exc:
        logger.error("[AM router] /listed — %s", exc)
        raise HTTPException(status_code=502, detail=f"Scraping échoué : {exc}")

    _cache_set("listed", data)
    return {"source": "live", "count": len(data), "data": data}


@router.get("/company/{code}")
async def get_company_profile(code: str):
    """Profil société BRVM : annonces, dividendes, rapports annuels."""
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
        raise HTTPException(status_code=502, detail=f"Scraping échoué : {exc}")

    _cache_set(key, data)
    return {"source": "live", "data": data}


@router.get("/currencies")
async def get_currencies():
    """Taux de change XOF/USD et devises africaines."""
    cached = _cache_get("currencies")
    if cached is not None:
        return {"source": "cache", "data": cached}

    try:
        from backend.app.pipeline.african_markets import fetch_currencies
        data = await asyncio.get_event_loop().run_in_executor(None, fetch_currencies)
    except Exception as exc:
        logger.error("[AM router] /currencies — %s", exc)
        raise HTTPException(status_code=502, detail=f"Scraping échoué : {exc}")

    _cache_set("currencies", data)
    return {"source": "live", "count": len(data), "data": data}


@router.get("/news")
async def get_news(limit: int = Query(20, ge=1, le=50)):
    """Actualités BRVM depuis african-markets.com."""
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
        raise HTTPException(status_code=502, detail=f"Scraping échoué : {exc}")

    _cache_set(key, data)
    return {"source": "live", "count": len(data), "data": data}
