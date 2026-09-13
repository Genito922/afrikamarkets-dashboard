"""
Router Subscriptions — lifecycle de l'abonnement
GET  /subscriptions/me              → état courant + historique
POST /subscriptions/cancel          → annulation fin de période
POST /subscriptions/resume          → annulation de l'annulation
POST /subscriptions/downgrade/{plan}→ downgrade programmé fin de période
POST /subscriptions/upgrade/{plan}  → retourne le payload PayDunya pour paiement immédiat
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.app.core.database import get_db
from backend.app.core.deps import require_active, PLAN_RANK
from backend.app.models.models import Licence, Payment, User, PlanEnum, StatusEnum

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
logger = logging.getLogger("subscriptions")


# ── Helpers ───────────────────────────────────────────────────

async def _active_licence(user_id: str, db: AsyncSession) -> Licence | None:
    res = await db.execute(
        select(Licence)
        .where(Licence.user_id == user_id, Licence.status == StatusEnum.ACTIVE)
        .order_by(desc(Licence.expires_at))
        .limit(1)
    )
    return res.scalar_one_or_none()


# ── GET /subscriptions/me ─────────────────────────────────────

@router.get("/me")
async def get_subscription(
    user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    """Retourne l'état courant de l'abonnement + les 5 derniers paiements."""
    now     = datetime.utcnow()
    licence = await _active_licence(user.id, db)

    # Historique des 5 derniers paiements réussis
    res = await db.execute(
        select(Payment)
        .where(Payment.user_id == user.id, Payment.status == "success")
        .order_by(desc(Payment.created_at))
        .limit(5)
    )
    payments = res.scalars().all()

    sub = {
        "plan":                  user.plan.value,
        "status":                user.status.value,
        "cancel_at_period_end":  user.cancel_at_period_end or False,
        "pending_plan":          user.pending_plan.value if user.pending_plan else None,
        "current_period_end":    None,
        "days_remaining":        None,
        "billing_period_start":  None,
    }

    if licence:
        sub["current_period_end"]   = licence.expires_at.isoformat()
        sub["billing_period_start"] = licence.billing_period_start.isoformat() if licence.billing_period_start else None
        sub["days_remaining"]       = max(0, (licence.expires_at - now).days)

    sub["payment_history"] = [
        {
            "date":     p.created_at.isoformat() if p.created_at else None,
            "plan":     p.plan.value if p.plan else None,
            "amount":   p.amount,
            "currency": p.currency,
            "method":   p.method,
            "ref":      p.provider_ref,
        }
        for p in payments
    ]

    return sub


# ── POST /subscriptions/cancel ────────────────────────────────

@router.post("/cancel")
async def cancel_subscription(
    user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    """
    Planifie l'annulation de l'abonnement à la fin de la période en cours.
    L'accès reste actif jusqu'à expiration de la licence.
    """
    if user.cancel_at_period_end:
        raise HTTPException(400, "Abonnement déjà marqué pour annulation")
    if user.plan == PlanEnum.FREE:
        raise HTTPException(400, "Aucun abonnement actif à annuler")

    licence = await _active_licence(user.id, db)
    end_date = licence.expires_at.date() if licence else "fin de période"

    user.cancel_at_period_end = True
    await db.commit()

    logger.info(f"[Sub] CANCEL programmé user={user.id} plan={user.plan.value} end={end_date}")
    return {
        "message": f"Abonnement annulé — accès maintenu jusqu'au {end_date}",
        "cancel_at_period_end": True,
        "current_period_end": str(end_date),
    }


# ── POST /subscriptions/resume ────────────────────────────────

@router.post("/resume")
async def resume_subscription(
    user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    """Annule une annulation ou un downgrade programmé."""
    if not user.cancel_at_period_end and not user.pending_plan:
        raise HTTPException(400, "Aucun changement en attente à annuler")

    user.cancel_at_period_end = False
    user.pending_plan         = None
    await db.commit()

    logger.info(f"[Sub] RESUME user={user.id} plan={user.plan.value}")
    return {"message": "Abonnement maintenu — aucun changement programmé", "plan": user.plan.value}


# ── POST /subscriptions/downgrade/{plan} ─────────────────────

@router.post("/downgrade/{plan}")
async def schedule_downgrade(
    plan: PlanEnum,
    user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    """
    Programme un downgrade vers un plan inférieur à la fin de la période actuelle.
    Le changement sera appliqué par le scheduler nocturne.
    """
    if PLAN_RANK.get(plan, 0) >= PLAN_RANK.get(user.plan, 0):
        raise HTTPException(
            400,
            f"Le plan '{plan.value}' n'est pas inférieur à votre plan actuel '{user.plan.value}'. "
            "Utilisez /upgrade pour monter de plan."
        )

    licence  = await _active_licence(user.id, db)
    end_date = licence.expires_at.date() if licence else "fin de période"

    user.pending_plan         = plan
    user.cancel_at_period_end = False   # downgrade annule une éventuelle annulation
    await db.commit()

    logger.info(f"[Sub] DOWNGRADE {user.plan.value} -> {plan.value} programmé user={user.id} end={end_date}")
    return {
        "message":      f"Downgrade vers '{plan.value}' programmé pour le {end_date}",
        "current_plan": user.plan.value,
        "pending_plan": plan.value,
        "effective_at": str(end_date),
    }


# ── POST /subscriptions/upgrade/{plan} ───────────────────────

@router.post("/upgrade/{plan}")
async def initiate_upgrade(
    plan: PlanEnum,
    user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne les paramètres nécessaires pour initier un paiement d'upgrade via PayDunya.
    Le frontend appellera POST /api/v1/paydunya/pay avec ces valeurs.
    """
    if PLAN_RANK.get(plan, 0) <= PLAN_RANK.get(user.plan, 0):
        raise HTTPException(
            400,
            f"Le plan '{plan.value}' n'est pas supérieur à votre plan actuel '{user.plan.value}'. "
            "Utilisez /downgrade pour descendre de plan."
        )

    # Prix du nouveau plan
    from backend.app.routers.paydunya import PLANS_XOF
    plan_info = PLANS_XOF.get(plan.value)
    if not plan_info:
        raise HTTPException(500, "Configuration plan introuvable")

    logger.info(f"[Sub] UPGRADE init {user.plan.value} -> {plan.value} user={user.id}")
    return {
        "message":        f"Procédez au paiement pour passer au plan '{plan.value}'",
        "current_plan":   user.plan.value,
        "target_plan":    plan.value,
        "price_xof":      plan_info["xof"],
        "price_xaf":      plan_info["xaf"],
        "price_usd":      plan_info["usd"],
        "paydunya_params": {
            "user_id": user.id,
            "plan":    plan.value,
        },
        "note": "Passez ces paramètres à POST /api/v1/paydunya/pay avec votre opérateur",
    }
