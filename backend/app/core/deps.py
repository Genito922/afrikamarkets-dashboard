"""
Dépendances FastAPI — authentification et contrôle d'accès par plan.

Hiérarchie des plans :
    FREE(0) < STARTER(1) < PRO(2) < EXPERT(3) < EXPERT_PREMIUM(4)

Usage dans un router :
    router = APIRouter(dependencies=[Depends(require_active)])
    router = APIRouter(dependencies=[Depends(require_plan(PlanEnum.PRO))])

Usage sur un endpoint précis :
    async def my_endpoint(user: User = Depends(require_active)): ...
"""
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional

from backend.app.core.database import get_db
from backend.app.core.security import decode_token
from backend.app.models.models import User, PlanEnum, StatusEnum

# ── Hiérarchie des plans ──────────────────────────────────────
PLAN_RANK: dict[PlanEnum, int] = {
    PlanEnum.FREE:            0,
    PlanEnum.STARTER:         1,
    PlanEnum.PRO:             2,
    PlanEnum.EXPERT:          3,
    PlanEnum.EXPERT_PREMIUM:  4,
}


# ── Dépendance de base : décode le JWT et charge l'utilisateur ─

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")

    try:
        token_data = decode_token(authorization.split(" ")[1])
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")

    # Auto-expiration du trial si la date est dépassée
    if user.status == StatusEnum.TRIAL and user.trial_ends_at and user.trial_ends_at < datetime.utcnow():
        user.status = StatusEnum.INACTIVE
        await db.commit()

    return user


# ── require_active : bloque les comptes expirés/suspendus ─────

async def require_active(user: User = Depends(get_current_user)) -> User:
    if user.status == StatusEnum.SUSPENDED:
        raise HTTPException(status_code=403, detail="Compte suspendu")
    if user.status == StatusEnum.INACTIVE:
        raise HTTPException(status_code=403, detail="Essai expiré — veuillez souscrire à un plan")
    return user


# ── require_plan : vérifie le niveau de plan minimum ─────────

def require_plan(min_plan: PlanEnum):
    """
    Factory — retourne une dépendance FastAPI qui exige un plan >= min_plan.

    Exemple :
        router = APIRouter(dependencies=[Depends(require_plan(PlanEnum.PRO))])
    """
    async def _check(user: User = Depends(require_active)) -> User:
        if PLAN_RANK.get(user.plan, 0) < PLAN_RANK[min_plan]:
            raise HTTPException(
                status_code=403,
                detail=f"Cette fonctionnalité requiert le plan {min_plan.value} ou supérieur "
                       f"(votre plan actuel : {user.plan.value})",
            )
        return user
    return _check
