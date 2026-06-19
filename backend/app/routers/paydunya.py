"""
Afrika Markets Intelligence — PayDunya Payment Router
Couvre : Wave CI, Orange Money CI/SN/BF, MTN MoMo CI, Moov CI, Airtel TG
Documentation : https://developers.paydunya.com
"""
import os
import uuid
import logging
import httpx

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.models.models import Payment, PlanEnum
from backend.app.routers.licences import generate_licence

router = APIRouter(prefix="/paydunya", tags=["paydunya"])
logger = logging.getLogger("paydunya")

# ── Config PayDunya ───────────────────────────────────────────
PD_MASTER_KEY  = os.getenv("PAYDUNYA_MASTER_KEY", "")
PD_PRIVATE_KEY = os.getenv("PAYDUNYA_PRIVATE_KEY", "")
PD_TOKEN       = os.getenv("PAYDUNYA_TOKEN", "")
FRONTEND_URL   = os.getenv("FRONTEND_URL", "https://afrikamarkets-dashboard.streamlit.app")
API_BASE_URL   = os.getenv("API_BASE_URL", "")

BASE_URL = "https://app.paydunya.com/api/v1"
HEADERS  = {
    "Content-Type":         "application/json",
    "PAYDUNYA-MASTER-KEY":  PD_MASTER_KEY,
    "PAYDUNYA-PRIVATE-KEY": PD_PRIVATE_KEY,
    "PAYDUNYA-TOKEN":       PD_TOKEN,
}

# ── Prix des plans en XOF ─────────────────────────────────────
PLANS_XOF = {
    "starter":        {"xof": 18000,  "usd": 29.99,  "label": "Starter"},
    "pro":            {"xof": 45000,  "usd": 74.99,  "label": "Pro"},
    "expert":         {"xof": 115000, "usd": 199.99, "label": "Expert"},
    "expert_premium": {"xof": 170000, "usd": 299.99, "label": "Expert Premium"},
}

# ── Endpoints SOFTPAY par opérateur ──────────────────────────
OPERATORS = {
    "wave_ci":          "/softpay/wave-ci",
    "orange_money_ci":  "/softpay/orange-money-ci",
    "orange_money_sn":  "/softpay/orange-money-senegal",
    "orange_money_bf":  "/softpay/orange-money-burkina",
    "mtn_ci":           "/softpay/mtn-ci",
    "moov_ci":          "/softpay/moov-ci",
    "airtel_tg":        "/softpay/airtel-togo",
}

OPERATOR_META = [
    {"id": "wave_ci",         "label": "Wave",            "flag": "🌊", "pays": "CI/SN", "frais": "1%"},
    {"id": "orange_money_ci", "label": "Orange Money CI", "flag": "🟠", "pays": "CI",    "frais": "2%"},
    {"id": "orange_money_sn", "label": "Orange Money SN", "flag": "🟠", "pays": "SN",    "frais": "2%"},
    {"id": "orange_money_bf", "label": "Orange Money BF", "flag": "🟠", "pays": "BF",    "frais": "2%"},
    {"id": "mtn_ci",          "label": "MTN MoMo",        "flag": "🟡", "pays": "CI",    "frais": "2%"},
    {"id": "moov_ci",         "label": "Moov Money",      "flag": "🔵", "pays": "CI",    "frais": "2%"},
    {"id": "airtel_tg",       "label": "Airtel Money",    "flag": "🔴", "pays": "TG",    "frais": "2%"},
]


# ── Schémas ───────────────────────────────────────────────────

class MobilePayRequest(BaseModel):
    user_id:       str
    plan:          str           # starter | pro | expert | expert_premium
    operator:      str           # wave_ci | orange_money_ci | mtn_ci | ...
    phone:         str           # ex: "0700000000"
    customer_name: Optional[str] = "Client Afrika Markets"


# ── Initier un paiement ───────────────────────────────────────

@router.post("/pay")
async def initiate_payment(req: MobilePayRequest, db: AsyncSession = Depends(get_db)):
    """
    Initie un paiement Mobile Money via PayDunya.
    - Wave CI : retourne redirect_url (redirection navigateur)
    - Orange / MTN / Moov / Airtel : retourne payment_token ou ussd_code
    """
    plan_info = PLANS_XOF.get(req.plan)
    if not plan_info:
        raise HTTPException(400, f"Plan invalide : {req.plan}. Disponibles : {list(PLANS_XOF)}")

    operator_path = OPERATORS.get(req.operator)
    if not operator_path:
        raise HTTPException(400, f"Opérateur non supporté : {req.operator}. Disponibles : {list(OPERATORS)}")

    ref      = f"AM-{req.user_id[:8].upper()}-{req.plan.upper()}-{uuid.uuid4().hex[:6].upper()}"
    callback = f"{API_BASE_URL}/api/v1/paydunya/webhook"
    amount   = plan_info["xof"]
    desc     = f"Afrika Markets Intelligence — {plan_info['label']}"

    if req.operator == "wave_ci":
        payload = {
            "amount":        amount,
            "currency":      "XOF",
            "description":   desc,
            "client_ref":    ref,
            "callback_url":  callback,
            "return_url":    f"{FRONTEND_URL}?payment=success&ref={ref}",
            "cancel_url":    f"{FRONTEND_URL}?payment=cancelled",
            "customer_name": req.customer_name,
        }
    elif req.operator == "orange_money_ci":
        payload = {
            "orange_money_ci_customer_number": req.phone,
            "amount":       amount,
            "description":  desc,
            "client_ref":   ref,
            "callback_url": callback,
        }
    else:
        payload = {
            "customer_phone": req.phone,
            "amount":         amount,
            "description":    desc,
            "client_ref":     ref,
            "callback_url":   callback,
        }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(f"{BASE_URL}{operator_path}", json=payload, headers=HEADERS)
        data = resp.json()
    except Exception as exc:
        logger.error(f"[PAYDUNYA] Erreur réseau : {exc}")
        raise HTTPException(502, "PayDunya inaccessible")

    if not data.get("success"):
        logger.warning(f"[PAYDUNYA] Échec : {data}")
        raise HTTPException(400, data.get("message", "Erreur PayDunya"))

    db.add(Payment(
        id=str(uuid.uuid4()),
        user_id=req.user_id,
        amount=amount,
        currency="XOF",
        method=req.operator,
        status="pending",
        provider_ref=ref,
        plan=PlanEnum(req.plan),
    ))
    await db.commit()

    logger.info(f"[PAYDUNYA] {req.operator} | {amount} XOF | ref={ref}")

    return {
        "success":       True,
        "ref":           ref,
        "operator":      req.operator,
        "amount_xof":    amount,
        "amount_usd":    plan_info["usd"],
        "plan":          plan_info["label"],
        "redirect_url":  data.get("url") or data.get("redirect_url"),   # Wave
        "payment_token": data.get("payment_token"),                       # Orange/MTN
        "ussd_code":     data.get("ussd_code"),                           # MTN
        "message":       data.get("message", ""),
    }


# ── Vérification statut ───────────────────────────────────────

@router.get("/status/{ref}")
async def check_status(ref: str):
    """Vérifie le statut d'une transaction PayDunya via son client_ref."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{BASE_URL}/checkout-invoice/confirm/{ref}",
                headers=HEADERS,
            )
        data   = resp.json()
        status = data.get("status", "unknown")
        return {
            "ref":    ref,
            "status": status,
            "paid":   status == "completed",
            "amount": data.get("receipt", {}).get("total_amount"),
            "method": data.get("receipt", {}).get("payment_method"),
        }
    except Exception as exc:
        raise HTTPException(502, str(exc))


# ── Webhook PayDunya ──────────────────────────────────────────

@router.post("/webhook")
async def paydunya_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Webhook PayDunya — active la licence après paiement confirmé.
    PayDunya POST ce endpoint avec le statut de la transaction.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Payload invalide")

    status = payload.get("status", "")
    ref    = (payload.get("custom_data") or {}).get("client_ref") or payload.get("client_ref", "")

    logger.info(f"[WEBHOOK] PayDunya status={status} ref={ref}")

    if status == "completed" and ref:
        result  = await db.execute(select(Payment).where(Payment.provider_ref == ref))
        payment = result.scalar_one_or_none()

        if payment and payment.status == "pending":
            payment.status = "success"
            await generate_licence(user_id=payment.user_id, plan=payment.plan, db=db)
            await db.commit()
            logger.info(f"[WEBHOOK] Licence activée — user={payment.user_id} plan={payment.plan}")

    return {"received": True}


# ── Opérateurs & plans disponibles ───────────────────────────

@router.get("/operators")
async def list_operators():
    """Liste des opérateurs Mobile Money et prix des plans en XOF."""
    return {
        "operators": OPERATOR_META,
        "plans": {
            k: {"xof": v["xof"], "usd": v["usd"], "label": v["label"]}
            for k, v in PLANS_XOF.items()
        },
        "note": (
            "Clients diaspora (Canada/France/USA) → Stripe (carte bancaire). "
            "Clients Afrique (CI/SN/BF/TG) → PayDunya Mobile Money."
        ),
    }
