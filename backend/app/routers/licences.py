"""
Router Licences — génération et validation
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import uuid

from backend.app.core.database import get_db
from backend.app.core.security import generate_licence_token
from backend.app.models.models import Licence, User, PlanEnum, StatusEnum

router = APIRouter(prefix="/licences", tags=["licences"])

PLAN_DURATION_DAYS = {
    PlanEnum.FREE:    30,
    PlanEnum.STARTER: 30,
    PlanEnum.PRO:     30,
    PlanEnum.EXPERT:  30,
}


@router.post("/generate")
async def generate_licence(
    user_id: str,
    plan: PlanEnum,
    db: AsyncSession = Depends(get_db),
):
    """Générer une licence après paiement confirmé (appelé par le webhook)."""
    token = generate_licence_token()
    days  = PLAN_DURATION_DAYS.get(plan, 30)

    licence = Licence(
        id=str(uuid.uuid4()),
        user_id=user_id,
        token=token,
        plan=plan,
        status=StatusEnum.ACTIVE,
        expires_at=datetime.utcnow() + timedelta(days=days),
    )
    db.add(licence)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.plan   = plan
        user.status = StatusEnum.ACTIVE

    await db.commit()
    return {"token": token, "plan": plan, "expires_at": licence.expires_at}


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
