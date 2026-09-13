"""
Router Licences — génération et validation
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta
import uuid
import logging

from backend.app.core.database import get_db
from backend.app.core.security import generate_licence_token
from backend.app.models.models import Licence, User, PlanEnum, StatusEnum

router = APIRouter(prefix="/licences", tags=["licences"])
logger = logging.getLogger("licences")

PLAN_DURATION_DAYS = 30  # durée standard d'une période (jours)

PLAN_RANK = {
    PlanEnum.FREE:           0,
    PlanEnum.STARTER:        1,
    PlanEnum.PRO:            2,
    PlanEnum.EXPERT:         3,
    PlanEnum.EXPERT_PREMIUM: 4,
}


@router.post("/generate")
async def generate_licence(
    user_id: str,
    plan: PlanEnum,
    db: AsyncSession = Depends(get_db),
):
    """
    Génère ou renouvelle une licence après paiement confirmé (appelé par le webhook).

    Logique :
    - Upgrade  (plan supérieur) → désactive l'ancienne, nouvelle période depuis aujourd'hui
    - Renouvellement (même plan) → prolonge depuis la fin de période actuelle
    - Première activation → nouvelle période depuis aujourd'hui
    """
    now = datetime.utcnow()

    # Cherche la licence active courante
    res = await db.execute(
        select(Licence)
        .where(Licence.user_id == user_id, Licence.status == StatusEnum.ACTIVE)
        .order_by(desc(Licence.expires_at))
        .limit(1)
    )
    current = res.scalar_one_or_none()

    if current:
        current_rank = PLAN_RANK.get(current.plan, 0)
        new_rank     = PLAN_RANK.get(plan, 0)

        if new_rank > current_rank:
            # UPGRADE : désactive l'ancienne, démarre immédiatement
            current.status = StatusEnum.INACTIVE
            period_start   = now
            expires_at     = now + timedelta(days=PLAN_DURATION_DAYS)
            logger.info(f"[Licence] UPGRADE {current.plan.value} -> {plan.value} user={user_id}")
        else:
            # RENOUVELLEMENT (même plan) : prolonge depuis la fin actuelle
            base           = max(current.expires_at, now)
            period_start   = base
            expires_at     = base + timedelta(days=PLAN_DURATION_DAYS)
            current.status = StatusEnum.INACTIVE
            logger.info(f"[Licence] RENOUVELLEMENT {plan.value} user={user_id} -> expires {expires_at.date()}")
    else:
        # Première activation
        period_start = now
        expires_at   = now + timedelta(days=PLAN_DURATION_DAYS)
        logger.info(f"[Licence] ACTIVATION {plan.value} user={user_id}")

    licence = Licence(
        id=str(uuid.uuid4()),
        user_id=user_id,
        token=generate_licence_token(),
        plan=plan,
        status=StatusEnum.ACTIVE,
        billing_period_start=period_start,
        expires_at=expires_at,
    )
    db.add(licence)

    # Met à jour l'utilisateur + efface tout changement en attente
    res2 = await db.execute(select(User).where(User.id == user_id))
    user = res2.scalar_one_or_none()
    if user:
        user.plan                = plan
        user.status              = StatusEnum.ACTIVE
        user.cancel_at_period_end = False
        user.pending_plan        = None

    await db.commit()
    return {"token": licence.token, "plan": plan, "expires_at": expires_at}


@router.get("/validate/{token}")
async def validate_licence(token: str, db: AsyncSession = Depends(get_db)):
    """Valider un token de licence (appelé par le Streamlit frontend)."""
    result = await db.execute(select(Licence).where(Licence.token == token))
    licence = result.scalar_one_or_none()

    if not licence:
        raise HTTPException(status_code=404, detail="Licence introuvable")
    if licence.status != StatusEnum.ACTIVE:
        raise HTTPException(status_code=403, detail="Licence inactive")
    if licence.expires_at < datetime.utcnow():
        licence.status = StatusEnum.INACTIVE
        await db.commit()
        raise HTTPException(status_code=403, detail="Licence expirée")

    return {
        "valid":          True,
        "plan":           licence.plan.value,
        "expires_at":     licence.expires_at,
        "days_remaining": (licence.expires_at - datetime.utcnow()).days,
    }
