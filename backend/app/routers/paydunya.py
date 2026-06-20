"""
Afrika Markets Intelligence — PayDunya Payment Router
Opérateurs supportés (source : https://developers.paydunya.com) :
  CI  : wave-ci, orange-money-ci, mtn-ci, moov-ci, djamo-ci
  SN  : wave-senegal, orange-money-senegal, free-money-senegal,
        expresso-sn, wizall-senegal, djamo-sn
  BF  : orange-money-burkina, moov-burkina-faso
  ML  : orange-money-mali, moov-ml
  TG  : t-money-togo, moov-togo
  BJ  : mtn-benin, moov-benin
  CM  : mtn-cameroun  (XAF)
  ALL : card (CB internationale)
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
FRONTEND_URL   = os.getenv("FRONTEND_URL", "https://sentinel-lccafrika.space")
API_BASE_URL   = os.getenv("API_BASE_URL", "")

BASE_URL = "https://app.paydunya.com/api/v1"

def _headers():
    """Headers dynamiques — lit les env vars au moment de la requête (pas au démarrage)."""
    return {
        "Content-Type":         "application/json",
        "PAYDUNYA-MASTER-KEY":  os.getenv("PAYDUNYA_MASTER_KEY", ""),
        "PAYDUNYA-PRIVATE-KEY": os.getenv("PAYDUNYA_PRIVATE_KEY", ""),
        "PAYDUNYA-TOKEN":       os.getenv("PAYDUNYA_TOKEN", ""),
    }

# ── Prix des plans ────────────────────────────────────────────
# XOF = UEMOA (CI/SN/BF/ML/TG/BJ) — 1 USD ≈ 600 XOF
# XAF = CEMAC (CM)                  — 1 USD ≈ 600 XAF (même taux EUR)
PLANS_XOF = {
    "starter":        {"xof": 18000,  "xaf": 18000,  "usd": 29.99,  "label": "Starter"},
    "pro":            {"xof": 45000,  "xaf": 45000,  "usd": 74.99,  "label": "Pro"},
    "expert":         {"xof": 115000, "xaf": 115000, "usd": 199.99, "label": "Expert"},
    "expert_premium": {"xof": 170000, "xaf": 170000, "usd": 299.99, "label": "Expert Premium"},
}

# ── Catalogue des opérateurs ──────────────────────────────────
# type :
#   "wave"       → flux redirect (pas de numéro requis à l'init)
#   "orange_ci"  → champ spécial orange_money_ci_customer_number
#   "phone"      → champ customer_phone (standard)
#   "card"       → checkout page (CB internationale)
OPERATORS = {
    # ── Côte d'Ivoire ──────────────────────────────────────
    "wave-ci":            {"path": "/softpay/wave-ci",           "type": "wave",     "currency": "XOF", "pays": "CI",    "label": "Wave CI",           "flag": "🌊", "frais": "1%"},
    "orange-money-ci":    {"path": "/softpay/orange-money-ci",   "type": "orange_ci","currency": "XOF", "pays": "CI",    "label": "Orange Money CI",   "flag": "🟠", "frais": "2%"},
    "mtn-ci":             {"path": "/softpay/mtn-ci",            "type": "phone",    "currency": "XOF", "pays": "CI",    "label": "MTN MoMo CI",       "flag": "🟡", "frais": "2%"},
    "moov-ci":            {"path": "/softpay/moov-ci",           "type": "phone",    "currency": "XOF", "pays": "CI",    "label": "Moov Money CI",     "flag": "🔵", "frais": "2%"},
    "djamo-ci":           {"path": "/softpay/djamo-ci",          "type": "phone",    "currency": "XOF", "pays": "CI",    "label": "Djamo CI",          "flag": "💜", "frais": "1.5%"},
    # ── Sénégal ────────────────────────────────────────────
    "wave-senegal":       {"path": "/softpay/wave-senegal",      "type": "wave",     "currency": "XOF", "pays": "SN",    "label": "Wave Sénégal",      "flag": "🌊", "frais": "1%"},
    "orange-money-senegal":{"path":"/softpay/orange-money-senegal","type":"phone",   "currency": "XOF", "pays": "SN",    "label": "Orange Money SN",   "flag": "🟠", "frais": "2%"},
    "free-money-senegal": {"path": "/softpay/free-money-senegal","type": "phone",    "currency": "XOF", "pays": "SN",    "label": "Free Money SN",     "flag": "🟣", "frais": "2%"},
    "expresso-sn":        {"path": "/softpay/expresso-sn",       "type": "phone",    "currency": "XOF", "pays": "SN",    "label": "Expresso SN",       "flag": "🔴", "frais": "2%"},
    "wizall-senegal":     {"path": "/softpay/wizall-senegal",    "type": "phone",    "currency": "XOF", "pays": "SN",    "label": "Wizall SN",         "flag": "🟢", "frais": "2%"},
    "djamo-sn":           {"path": "/softpay/djamo-sn",          "type": "phone",    "currency": "XOF", "pays": "SN",    "label": "Djamo SN",          "flag": "💜", "frais": "1.5%"},
    # ── Burkina Faso ───────────────────────────────────────
    "orange-money-burkina":{"path":"/softpay/orange-money-burkina","type":"phone",   "currency": "XOF", "pays": "BF",    "label": "Orange Money BF",   "flag": "🟠", "frais": "2%"},
    "moov-burkina-faso":  {"path": "/softpay/moov-burkina-faso", "type": "phone",    "currency": "XOF", "pays": "BF",    "label": "Moov BF",           "flag": "🔵", "frais": "2%"},
    # ── Mali ───────────────────────────────────────────────
    "orange-money-mali":  {"path": "/softpay/orange-money-mali", "type": "phone",    "currency": "XOF", "pays": "ML",    "label": "Orange Money ML",   "flag": "🟠", "frais": "2%"},
    "moov-ml":            {"path": "/softpay/moov-ml",           "type": "phone",    "currency": "XOF", "pays": "ML",    "label": "Moov Mali",         "flag": "🔵", "frais": "2%"},
    # ── Togo ───────────────────────────────────────────────
    "t-money-togo":       {"path": "/softpay/t-money-togo",      "type": "phone",    "currency": "XOF", "pays": "TG",    "label": "T-Money TG",        "flag": "🟤", "frais": "2%"},
    "moov-togo":          {"path": "/softpay/moov-togo",         "type": "phone",    "currency": "XOF", "pays": "TG",    "label": "Moov Togo",         "flag": "🔵", "frais": "2%"},
    # ── Bénin ──────────────────────────────────────────────
    "mtn-benin":          {"path": "/softpay/mtn-benin",         "type": "phone",    "currency": "XOF", "pays": "BJ",    "label": "MTN MoMo BJ",       "flag": "🟡", "frais": "2%"},
    "moov-benin":         {"path": "/softpay/moov-benin",        "type": "phone",    "currency": "XOF", "pays": "BJ",    "label": "Moov Bénin",        "flag": "🔵", "frais": "2%"},
    # ── Cameroun (XAF) ────────────────────────────────────
    "mtn-cameroun":       {"path": "/softpay/mtn-cameroun",      "type": "phone",    "currency": "XAF", "pays": "CM",    "label": "MTN MoMo CM",       "flag": "🟡", "frais": "2%"},
    # ── Carte bancaire (internationale) ───────────────────
    "card":               {"path": "/softpay/card",              "type": "card",     "currency": "XOF", "pays": "ALL",   "label": "Carte bancaire",    "flag": "💳", "frais": "3%"},
}

# ── Regroupement par pays (pour le frontend) ──────────────────
OPERATORS_BY_COUNTRY = {
    "CI": ["wave-ci", "orange-money-ci", "mtn-ci", "moov-ci", "djamo-ci"],
    "SN": ["wave-senegal", "orange-money-senegal", "free-money-senegal", "expresso-sn", "wizall-senegal", "djamo-sn"],
    "BF": ["orange-money-burkina", "moov-burkina-faso"],
    "ML": ["orange-money-mali", "moov-ml"],
    "TG": ["t-money-togo", "moov-togo"],
    "BJ": ["mtn-benin", "moov-benin"],
    "CM": ["mtn-cameroun"],
    "ALL": ["card"],
}


# ── Schéma de requête ─────────────────────────────────────────

class MobilePayRequest(BaseModel):
    user_id:       str
    plan:          str           # starter | pro | expert | expert_premium
    operator:      str           # ex: "wave-ci", "orange-money-ci", "mtn-cameroun"...
    phone:         Optional[str] = None   # obligatoire sauf pour wave et card
    customer_name: Optional[str] = "Client Afrika Markets"
    customer_email: Optional[str] = None


# ── Initier un paiement ───────────────────────────────────────

@router.post("/pay")
async def initiate_payment(req: MobilePayRequest, db: AsyncSession = Depends(get_db)):
    """
    Initie un paiement via PayDunya.

    Flux selon le type d'opérateur :
    - wave       → retourne redirect_url (redirection navigateur/app)
    - orange_ci  → champ spécial, retourne payment_token
    - phone      → customer_phone standard, retourne payment_token / ussd_code
    - card       → retourne redirect_url vers page de paiement CB
    """
    plan_info = PLANS_XOF.get(req.plan)
    if not plan_info:
        raise HTTPException(400, f"Plan invalide : {req.plan}. Options : {list(PLANS_XOF)}")

    op = OPERATORS.get(req.operator)
    if not op:
        raise HTTPException(400, f"Opérateur non supporté : {req.operator}. Options : {list(OPERATORS)}")

    # Numéro de téléphone requis sauf pour wave et card
    if op["type"] not in ("wave", "card") and not req.phone:
        raise HTTPException(400, f"Le champ 'phone' est obligatoire pour l'opérateur {req.operator}")

    currency  = op["currency"]                        # XOF ou XAF
    amount    = plan_info["xaf"] if currency == "XAF" else plan_info["xof"]
    ref       = f"AM-{req.user_id[:8].upper()}-{req.plan.upper()}-{uuid.uuid4().hex[:6].upper()}"
    callback  = f"{API_BASE_URL}/api/v1/paydunya/webhook"
    desc      = f"Afrika Markets Intelligence — {plan_info['label']}"

    # ── Construction du payload selon le type ────────────
    if op["type"] == "wave":
        payload = {
            "amount":        amount,
            "currency":      currency,
            "description":   desc,
            "client_ref":    ref,
            "callback_url":  callback,
            "return_url":    f"{FRONTEND_URL}?payment=success&ref={ref}",
            "cancel_url":    f"{FRONTEND_URL}?payment=cancelled",
            "customer_name": req.customer_name,
        }

    elif op["type"] == "orange_ci":
        payload = {
            "orange_money_ci_customer_number": req.phone,
            "amount":        amount,
            "description":   desc,
            "client_ref":    ref,
            "callback_url":  callback,
        }

    elif op["type"] == "card":
        payload = {
            "amount":        amount,
            "currency":      currency,
            "description":   desc,
            "client_ref":    ref,
            "callback_url":  callback,
            "return_url":    f"{FRONTEND_URL}?payment=success&ref={ref}",
            "cancel_url":    f"{FRONTEND_URL}?payment=cancelled",
            "customer_name": req.customer_name,
        }
        if req.customer_email:
            payload["customer_email"] = req.customer_email

    else:  # type == "phone" — tous les autres opérateurs
        payload = {
            "customer_phone": req.phone,
            "amount":         amount,
            "description":    desc,
            "client_ref":     ref,
            "callback_url":   callback,
        }

    # ── Appel API PayDunya ───────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{BASE_URL}{op['path']}",
                json=payload,
                headers=_headers(),
            )
        data = resp.json()
    except Exception as exc:
        logger.error(f"[PAYDUNYA] Erreur réseau : {exc}")
        raise HTTPException(502, "PayDunya inaccessible")

    if not data.get("success"):
        logger.warning(f"[PAYDUNYA] Échec initiation {req.operator} : {data}")
        raise HTTPException(400, data.get("message", "Erreur PayDunya"))

    # ── Enregistrement en DB ─────────────────────────────
    db.add(Payment(
        id=str(uuid.uuid4()),
        user_id=req.user_id,
        amount=amount,
        currency=currency,
        method=req.operator,
        status="pending",
        provider_ref=ref,
        plan=PlanEnum(req.plan),
    ))
    await db.commit()

    logger.info(f"[PAYDUNYA] {req.operator} | {amount} {currency} | ref={ref}")

    return {
        "success":       True,
        "ref":           ref,
        "operator":      req.operator,
        "operator_label": op["label"],
        "amount":        amount,
        "currency":      currency,
        "amount_usd":    plan_info["usd"],
        "plan":          plan_info["label"],
        # Wave & Card → redirect ; Orange/MTN/Moov → token/USSD
        "redirect_url":  data.get("url") or data.get("redirect_url"),
        "payment_token": data.get("payment_token"),
        "ussd_code":     data.get("ussd_code"),
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
                headers=_headers(),
            )
        data   = resp.json()
        status = data.get("status", "unknown")
        return {
            "ref":      ref,
            "status":   status,
            "paid":     status == "completed",
            "amount":   data.get("receipt", {}).get("total_amount"),
            "currency": data.get("receipt", {}).get("currency"),
            "method":   data.get("receipt", {}).get("payment_method"),
        }
    except Exception as exc:
        raise HTTPException(502, str(exc))


# ── IPN / Webhook PayDunya ────────────────────────────────────

@router.post("/webhook")
async def paydunya_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    IPN PayDunya (Instant Payment Notification).
    PayDunya POSTe ce endpoint après confirmation du paiement.
    Déclarez cette URL dans le dashboard PayDunya → votre AppDunya → IPN URL :
        https://votre-api.com/api/v1/paydunya/webhook
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Payload invalide")

    status = payload.get("status", "")
    # PayDunya envoie client_ref dans custom_data ou à la racine selon le flux
    ref = (payload.get("custom_data") or {}).get("client_ref") or payload.get("client_ref", "")

    logger.info(f"[IPN] PayDunya status={status} ref={ref}")

    if status == "completed" and ref:
        result  = await db.execute(select(Payment).where(Payment.provider_ref == ref))
        payment = result.scalar_one_or_none()

        if payment and payment.status == "pending":
            payment.status = "success"
            await generate_licence(user_id=payment.user_id, plan=payment.plan, db=db)
            await db.commit()
            logger.info(f"[IPN] Licence activée — user={payment.user_id} plan={payment.plan}")

    return {"received": True}


# ── Catalogue opérateurs & plans (pour le frontend) ──────────

@router.get("/operators")
async def list_operators():
    """
    Retourne tous les opérateurs PayDunya disponibles, groupés par pays,
    avec les prix des plans en XOF/XAF/USD.
    """
    operators_list = [
        {
            "id":      op_id,
            "label":   op["label"],
            "flag":    op["flag"],
            "pays":    op["pays"],
            "frais":   op["frais"],
            "currency": op["currency"],
            "type":    op["type"],
        }
        for op_id, op in OPERATORS.items()
    ]

    return {
        "operators":          operators_list,
        "operators_by_country": OPERATORS_BY_COUNTRY,
        "plans": {
            k: {
                "xof":   v["xof"],
                "xaf":   v["xaf"],
                "usd":   v["usd"],
                "label": v["label"],
            }
            for k, v in PLANS_XOF.items()
        },
        "note": (
            "Clients diaspora (Canada/France/USA) → Stripe (carte bancaire). "
            "Clients Afrique → PayDunya Mobile Money selon pays. "
            "Cameroun utilise XAF (taux identique à XOF vs EUR)."
        ),
    }
