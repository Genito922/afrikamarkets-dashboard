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
from backend.app.models.models import Payment, User, PlanEnum, StatusEnum
from backend.app.routers.licences import generate_licence

router = APIRouter(prefix="/payments", tags=["payments"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
WAVE_API_KEY          = os.getenv("WAVE_API_KEY", "")
ORANGE_API_KEY        = os.getenv("ORANGE_API_KEY", "")
FRONTEND_URL          = os.getenv("FRONTEND_URL", "https://afrika-markets.streamlit.app")

PLANS = {
    "starter": {"price_cad": 9.99,  "price_fcfa": 4500,  "label": "Starter"},
    "pro":     {"price_cad": 24.99, "price_fcfa": 11000, "label": "Pro"},
    "expert":  {"price_cad": 49.99, "price_fcfa": 22000, "label": "Expert"},
}


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
                "unit_amount": int(plan_info["price_cad"] * 100),
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
                "amount":           str(int(plan_info["price_fcfa"])),
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
                "amount":       int(plan_info["price_fcfa"]),
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
