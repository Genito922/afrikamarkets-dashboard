"""
Router Payments — catalogue des plans & taux de change.
Les paiements effectifs passent par /paydunya (router dédié).
"""
from fastapi import APIRouter, HTTPException
import os

from backend.app.core.exchange_rates import get_rates, convert, get_cache_info

router = APIRouter(prefix="/payments", tags=["payments"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://sentinel-lccafrika.space")

# ── Prix des plans ────────────────────────────────────────────
# XOF = UEMOA (CI/SN/BF/ML/TG/BJ) — XAF = CEMAC (CM)
# Synchronisé avec backend/app/routers/paydunya.py → PLANS_XOF
PLANS = {
    "starter": {
        "label":     "Starter",
        "price_usd": 29.99,
        "price_cad": 29.99,
        "price_xof": 18000,
        "price_xaf": 18000,
    },
    "pro": {
        "label":     "Pro",
        "price_usd": 74.99,
        "price_cad": 74.99,
        "price_xof": 45000,
        "price_xaf": 45000,
    },
    "expert": {
        "label":     "Expert",
        "price_usd": 199.99,
        "price_cad": 199.99,
        "price_xof": 115000,
        "price_xaf": 115000,
    },
    "expert_premium": {
        "label":     "Expert Premium",
        "price_usd": 299.99,
        "price_cad": 299.99,
        "price_xof": 170000,
        "price_xaf": 170000,
    },
}


# ── Endpoints ─────────────────────────────────────────────────

@router.get("/plans")
async def get_plans():
    """Retourne les plans avec prix dans toutes les devises."""
    return {
        key: {
            "label":     p["label"],
            "price_usd": p["price_usd"],
            "price_cad": p["price_cad"],
            "price_xof": p["price_xof"],
            "price_fcfa": p["price_xof"],  # alias lisible
        }
        for key, p in PLANS.items()
    }


@router.get("/plans/{currency}")
async def get_plans_currency(currency: str):
    """Plans avec prix dans une devise spécifique (USD, CAD, XOF, XAF)."""
    currency = currency.upper()
    mapping = {"USD": "price_usd", "CAD": "price_cad", "XOF": "price_xof", "XAF": "price_xaf"}
    if currency not in mapping:
        raise HTTPException(400, "Devise non supportée. Utilisez USD, CAD, XOF ou XAF.")
    field = mapping[currency]
    return {
        key: {"label": p["label"], "price": p[field], "currency": currency}
        for key, p in PLANS.items()
    }


@router.get("/rates")
async def get_exchange_rates():
    """Taux de change USD-based en temps réel (cache 6h)."""
    rates = await get_rates()
    return {
        "base": "USD",
        "rates": {
            "XOF": rates.get("XOF"),
            "XAF": rates.get("XAF"),
            "CAD": rates.get("CAD"),
            "EUR": rates.get("EUR"),
            "GBP": rates.get("GBP"),
        },
        "cache": get_cache_info(),
    }


@router.get("/plans/convert/{currency}")
async def get_plans_converted(currency: str):
    """Plans avec prix convertis dynamiquement depuis USD."""
    currency = currency.upper()
    if currency not in ("USD", "CAD", "XOF", "XAF", "EUR", "GBP"):
        raise HTTPException(400, "Devise non supportée")
    result = {}
    for key, plan in PLANS.items():
        converted = await convert(plan["price_usd"], "USD", currency)
        result[key] = {
            "label":     plan["label"],
            "price":     converted,
            "currency":  currency,
            "price_usd": plan["price_usd"],
        }
    return result
