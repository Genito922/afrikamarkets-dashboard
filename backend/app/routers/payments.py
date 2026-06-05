"""
Router Payments — Stripe (CAD/EUR) + Wave CI + Orange Money
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import stripe
import os
import uuid
import hmac
import hashlib
import httpx

from backend.app.core.database import get_db
from backend.app.core.exchange_rates import get_rates, convert, get_cache_info
from backend.app.models.models import Payment, User, PlanEnum, StatusEnum
from backend.app.routers.licences import generate_licence

router = APIRouter(prefix="/payments", tags=["payments"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
WAVE_API_KEY          = os.getenv("WAVE_API_KEY", "")
ORANGE_API_KEY        = os.getenv("ORANGE_API_KEY", "")
FRONTEND_URL          = os.getenv("FRONTEND_URL", "https://afrika-markets.streamlit.app")

# Taux de change (mis à jour manuellement — 1 USD ≈ 600 XOF, 1 CAD ≈ 440 XOF)
# Taux récupérés dynamiquement via exchange_rates.py
# Les prix FCFA dans PLANS sont calculés au moment de la requête
async def _xof(usd: float) -> int:
    """Conversion USD → XOF via API taux de change (cache 6h)."""
    from backend.app.core.exchange_rates import xof_rate
    rate = await xof_rate()
    return round(usd * rate / 1000) * 1000

PLANS = {
    "starter": {
        "price_usd":  29.99,
        "price_cad":  29.99,
        "price_fcfa": _xof(29.99),   # ~18 000 XOF
        "label":      "Starter",
        "paddle_id":  os.getenv("PADDLE_PLAN_STARTER", ""),
    },
    "pro": {
        "price_usd":  74.99,
        "price_cad":  74.99,
        "price_fcfa": _xof(74.99),   # ~45 000 XOF
        "label":      "Pro",
        "paddle_id":  os.getenv("PADDLE_PLAN_PRO", ""),
    },
    "expert": {
        "price_usd":  199.99,
        "price_cad":  299.99,
        "price_fcfa": _xof(199.99),  # ~120 000 XOF
        "label":      "Expert",
        "paddle_id":  os.getenv("PADDLE_PLAN_EXPERT", ""),
    },
    "expert_premium": {
        "price_usd":  199.99,
        "price_cad":  299.99,
        "price_fcfa": _xof(199.99),  # ~120 000 XOF
        "label":      "Expert Premium",
        "paddle_id":  os.getenv("PADDLE_PLAN_EXPERT_PREMIUM", ""),
    },
}

def get_price(plan: str, currency: str = "USD") -> float:
    """Retourne le prix dans la devise demandée."""
    p = PLANS.get(plan, {})
    if currency == "XOF":  return float(p.get("price_fcfa", 0))
    if currency == "CAD":  return float(p.get("price_cad",  0))
    return float(p.get("price_usd", 0))  # USD par défaut


# ── Schémas ──────────────────────────────────────────────────

class StripeCheckoutRequest(BaseModel):
    user_id:     str
    plan:        str
    success_url: str = f"{FRONTEND_URL}?payment=success"
    cancel_url:  str = f"{FRONTEND_URL}?payment=cancelled"


class WavePaymentRequest(BaseModel):
    user_id: str
    plan:    str
    phone:   str  # ex: "+2250700000000"


class OrangeMoneyRequest(BaseModel):
    user_id: str
    plan:    str
    phone:   str  # ex: "+2250700000000"


# ── Stripe ───────────────────────────────────────────────────

@router.post("/stripe/checkout")
async def stripe_checkout(req: StripeCheckoutRequest, db: AsyncSession = Depends(get_db)):
    plan_info = PLANS.get(req.plan)
    if not plan_info:
        raise HTTPException(status_code=400, detail="Plan invalide")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "cad",
                "product_data": {"name": f"Afrika Markets Intelligence — {plan_info['label']}"},
                "unit_amount": int(plan_info.get("price_usd", plan_info.get("price_cad", 0)) * 100),
                "recurring": {"interval": "month"},
            },
            "quantity": 1,
        }],
        mode="subscription",
        success_url=req.success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=req.cancel_url,
        metadata={"user_id": req.user_id, "plan": req.plan},
    )

    db.add(Payment(
        id=str(uuid.uuid4()),
        user_id=req.user_id,
        amount=plan_info["price_cad"],
        currency="CAD",
        method="stripe",
        status="pending",
        provider_ref=session.id,
        plan=PlanEnum(req.plan),
    ))
    await db.commit()

    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Webhook Stripe — provisionne la licence après paiement réussi."""
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Signature Stripe invalide")

    if event["type"] in ("checkout.session.completed", "invoice.paid"):
        meta    = event["data"]["object"].get("metadata", {})
        user_id = meta.get("user_id")
        plan    = meta.get("plan")

        if user_id and plan:
            # Mettre à jour le paiement
            ref = event["data"]["object"].get("id", "")
            result = await db.execute(select(Payment).where(Payment.provider_ref == ref))
            payment = result.scalar_one_or_none()
            if payment:
                payment.status = "success"

            # Générer la licence
            await generate_licence(user_id=user_id, plan=PlanEnum(plan), db=db)

    return {"received": True}


# ── Wave CI ──────────────────────────────────────────────────

@router.post("/wave/initiate")
async def wave_payment(req: WavePaymentRequest, db: AsyncSession = Depends(get_db)):
    plan_info = PLANS.get(req.plan)
    if not plan_info:
        raise HTTPException(status_code=400, detail="Plan invalide")

    client_ref = f"BRVM-{req.user_id[:8]}-{req.plan.upper()}-{uuid.uuid4().hex[:6]}"

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://api.wave.com/v1/checkout/sessions",
            headers={"Authorization": f"Bearer {WAVE_API_KEY}"},
            json={
                "amount":           str(int(plan_info.get("price_fcfa", 0))),
                "currency":         "XOF",
                "error_url":        f"{FRONTEND_URL}?payment=error",
                "success_url":      f"{FRONTEND_URL}?payment=success",
                "client_reference": client_ref,
            },
        )

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Wave API error: {r.text}")

    data = r.json()
    db.add(Payment(
        id=str(uuid.uuid4()),
        user_id=req.user_id,
        amount=plan_info["price_fcfa"],
        currency="XOF",
        method="wave",
        status="pending",
        provider_ref=client_ref,
        plan=PlanEnum(req.plan),
    ))
    await db.commit()

    return {
        "wave_launch_url": data.get("wave_launch_url"),
        "client_reference": client_ref,
    }


@router.post("/wave/webhook")
async def wave_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Webhook Wave — provisionne la licence après paiement réussi."""
    payload = await request.json()

    # Wave envoie un HMAC SHA-256 dans le header X-Wave-Signature
    sig       = request.headers.get("X-Wave-Signature", "")
    raw_body  = await request.body()
    expected  = hmac.new(WAVE_API_KEY.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=400, detail="Signature Wave invalide")

    if payload.get("type") == "checkout.session.completed":
        ref = payload.get("client_reference", "")
        result = await db.execute(select(Payment).where(Payment.provider_ref == ref))
        payment = result.scalar_one_or_none()

        if payment and payment.status == "pending":
            payment.status = "success"
            await generate_licence(user_id=payment.user_id, plan=payment.plan, db=db)

    return {"received": True}


# ── Orange Money ─────────────────────────────────────────────

@router.post("/orange/initiate")
async def orange_payment(req: OrangeMoneyRequest, db: AsyncSession = Depends(get_db)):
    plan_info = PLANS.get(req.plan)
    if not plan_info:
        raise HTTPException(status_code=400, detail="Plan invalide")

    order_id = f"BRVM-{req.user_id[:8]}-{uuid.uuid4().hex[:8].upper()}"

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://api.orange.com/orange-money-webpay/ci/v1/webpayment",
            headers={
                "Authorization": f"Bearer {ORANGE_API_KEY}",
                "Content-Type":  "application/json",
            },
            json={
                "merchant_key": os.getenv("ORANGE_MERCHANT_KEY", ""),
                "currency":     "OUV",
                "order_id":     order_id,
                "amount":       int(plan_info.get("price_fcfa", 0)),
                "return_url":   f"{FRONTEND_URL}?payment=success",
                "cancel_url":   f"{FRONTEND_URL}?payment=cancelled",
                "notif_url":    f"{os.getenv('API_BASE_URL', '')}/payments/orange/webhook",
                "lang":         "fr",
                "reference":    order_id,
            },
        )

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Orange Money API error: {r.text}")

    data = r.json()
    db.add(Payment(
        id=str(uuid.uuid4()),
        user_id=req.user_id,
        amount=plan_info["price_fcfa"],
        currency="XOF",
        method="orange_money",
        status="pending",
        provider_ref=order_id,
        plan=PlanEnum(req.plan),
    ))
    await db.commit()

    return {
        "payment_url": data.get("payment_url"),
        "order_id":    order_id,
    }


@router.post("/orange/webhook")
async def orange_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Callback Orange Money — provisionne la licence après paiement réussi."""
    payload  = await request.json()
    order_id = payload.get("order_id") or payload.get("reference", "")
    status   = payload.get("status", "")

    if status == "SUCCESS" and order_id:
        result = await db.execute(select(Payment).where(Payment.provider_ref == order_id))
        payment = result.scalar_one_or_none()

        if payment and payment.status == "pending":
            payment.status = "success"
            await generate_licence(user_id=payment.user_id, plan=payment.plan, db=db)

    return {"received": True}


# ── Endpoint public — liste des plans ──────────────────────

@router.get("/plans")
async def get_plans():
    """Retourne les plans avec prix dans toutes les devises."""
    return {
        key: {
            "label":      p["label"],
            "price_usd":  p["price_usd"],
            "price_cad":  p["price_cad"],
            "price_xof":  p["price_fcfa"],
            "price_fcfa": p["price_fcfa"],
        }
        for key, p in PLANS.items()
    }


@router.get("/plans/{currency}")
async def get_plans_currency(currency: str):
    """Plans avec prix dans une devise spécifique (USD, CAD, XOF)."""
    currency = currency.upper()
    if currency not in ("USD", "CAD", "XOF"):
        raise HTTPException(400, "Devise non supportée. Utilisez USD, CAD ou XOF.")
    return {
        key: {
            "label": p["label"],
            "price": get_price(key, currency),
            "currency": currency,
        }
        for key, p in PLANS.items()
    }


# ── Taux de change live ──────────────────────────────────────

@router.get("/rates")
async def get_exchange_rates():
    """Taux de change USD-based en temps réel (cache 6h)."""
    from backend.app.core.exchange_rates import get_rates, get_cache_info
    rates = await get_rates()
    return {
        "base": "USD",
        "rates": {
            "XOF": rates.get("XOF"),
            "CAD": rates.get("CAD"),
            "EUR": rates.get("EUR"),
            "GBP": rates.get("GBP"),
        },
        "cache": get_cache_info(),
    }


@router.get("/plans/convert/{currency}")
async def get_plans_converted(currency: str):
    """Plans avec prix convertis dans la devise demandée."""
    from backend.app.core.exchange_rates import convert
    currency = currency.upper()
    if currency not in ("USD", "CAD", "XOF", "EUR", "GBP"):
        raise HTTPException(400, "Devise non supportée")
    result = {}
    for key, plan in PLANS.items():
        price_usd = plan.get("price_usd", 0)
        converted = await convert(price_usd, "USD", currency)
        result[key] = {
            "label":    plan["label"],
            "price":    converted,
            "currency": currency,
            "price_usd": price_usd,
        }
    return result
