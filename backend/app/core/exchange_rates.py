"""
Afrika Markets — Module taux de change automatique
Primary  : Frankfurter (BCE + 84 banques centrales, no API key)
Fallback : fawazahmed0/exchange-api (200+ devises, no rate limit)
Cache    : 6h en mémoire pour ne pas surcharger les APIs
"""
import asyncio
import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ── Cache en mémoire ──────────────────────────────────────────
_cache: dict = {}
_cache_expiry: Optional[datetime] = None
CACHE_TTL_HOURS = 6

# Taux de secours si toutes les APIs échouent
_FALLBACK_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "CAD": 1.38,
    "GBP": 0.78,
    "XOF": 600.0,   # 1 USD ≈ 600 XOF (FCFA BCEAO)
    "XAF": 600.0,   # 1 USD ≈ 600 XAF (FCFA BEAC)
}


async def _fetch_frankfurter() -> dict:
    """
    Frankfurter (BCE) — gratuit, no key, 84 devises.
    Essaie api.frankfurter.dev puis api.frankfurter.app (backup).
    XOF : parité fixe EUR (655.957 XOF = 1 EUR, accord UMOA/France).
    """
    urls = [
        "https://api.frankfurter.dev/v1/latest",
    ]
    async with httpx.AsyncClient(timeout=8) as client:
        for url in urls:
            try:
                r = await client.get(url, params={"base": "USD"})
                r.raise_for_status()
                data = r.json()
                rates = data.get("rates", {})
                if not rates:
                    continue
                # XOF : parité fixe avec EUR
                if "EUR" in rates and "XOF" not in rates:
                    rates["XOF"] = round(rates["EUR"] * 655.957, 2)
                if "XAF" not in rates and "EUR" in rates:
                    rates["XAF"] = round(rates["EUR"] * 655.957, 2)
                rates["USD"] = 1.0
                logger.info(f"[FX] Frankfurter OK ({url}) | USD/XOF={rates.get('XOF'):.0f}")
                return rates
            except Exception as e:
                logger.warning(f"[FX] Frankfurter {url} échoué: {e}")
    raise RuntimeError("Frankfurter indisponible")


async def _fetch_fawazahmed() -> dict:
    """
    fawazahmed0 exchange-api — 200+ devises, no key, no rate limit.
    Hébergé sur GitHub CDN.
    """
    url = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"
    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
        raw = data.get("usd", {})
        # Normaliser les clés en majuscules
        rates = {k.upper(): v for k, v in raw.items()}
        rates["USD"] = 1.0
        logger.info(f"[FX] fawazahmed OK | USD/XOF={rates.get('XOF'):.0f}")
        return rates


async def _fetch_exchangerate_api() -> dict:
    """
    ExchangeRate-API open access — dernier recours, no key.
    """
    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.get("https://open.er-api.com/v6/latest/USD")
        r.raise_for_status()
        data = r.json()
        rates = data.get("rates", {})
        rates["USD"] = 1.0
        logger.info(f"[FX] ExchangeRate-API OK | USD/XOF={rates.get('XOF', 'N/A')}")
        return rates


async def get_rates() -> dict:
    """
    Retourne les taux USD-based avec cache 6h.
    Essaie Frankfurter → fawazahmed → ExchangeRate-API → fallback hardcodé.
    """
    global _cache, _cache_expiry

    # Servir depuis le cache si encore valide
    if _cache and _cache_expiry and datetime.utcnow() < _cache_expiry:
        return _cache

    # Essayer les sources dans l'ordre
    for fetcher, name in [
        (_fetch_frankfurter,      "Frankfurter"),
        (_fetch_fawazahmed,       "fawazahmed"),
        (_fetch_exchangerate_api, "ExchangeRate-API"),
    ]:
        try:
            rates = await fetcher()
            if rates and "XOF" in rates:
                _cache = rates
                _cache_expiry = datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)
                logger.info(f"[FX] Cache mis à jour via {name} | expire dans {CACHE_TTL_HOURS}h")
                return _cache
        except Exception as e:
            logger.warning(f"[FX] {name} échoué : {e}")

    # Fallback hardcodé
    logger.error("[FX] Toutes les APIs échouées — utilisation des taux de secours")
    return _FALLBACK_RATES


async def convert(amount: float, from_currency: str, to_currency: str) -> float:
    """Convertit un montant entre deux devises."""
    if from_currency == to_currency:
        return amount
    rates = await get_rates()
    # Tout est basé en USD
    amount_usd = amount / rates.get(from_currency, 1.0)
    return round(amount_usd * rates.get(to_currency, 1.0), 2)


async def get_rate(from_currency: str, to_currency: str) -> float:
    """Retourne le taux de change entre deux devises."""
    return await convert(1.0, from_currency, to_currency)


async def xof_rate() -> float:
    """Raccourci — taux USD/XOF actuel."""
    rates = await get_rates()
    return rates.get("XOF", 600.0)


async def cad_rate() -> float:
    """Raccourci — taux USD/CAD actuel."""
    rates = await get_rates()
    return rates.get("CAD", 1.38)


def get_cache_info() -> dict:
    """Info sur l'état du cache."""
    if not _cache_expiry:
        return {"status": "vide", "expires_at": None, "currencies": 0}
    remaining = (_cache_expiry - datetime.utcnow()).seconds // 60
    return {
        "status":       "actif" if _cache else "vide",
        "expires_at":   _cache_expiry.isoformat(),
        "expires_in_min": remaining,
        "currencies":   len(_cache),
        "usd_xof":      _cache.get("XOF"),
        "usd_cad":      _cache.get("CAD"),
        "usd_eur":      _cache.get("EUR"),
    }
