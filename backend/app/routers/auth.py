"""
Router Auth — inscription, connexion, profil
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional
import uuid

from backend.app.core.database import get_db
from backend.app.core.security import hash_password, verify_password, create_token, decode_token
from backend.app.models.models import User, AuditLog, PlanEnum, StatusEnum

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schémas ──────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email:     EmailStr
    password:  str
    full_name: str
    country:   str = "CA"
    phone:     str = ""


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    plan:         str
    status:       str
    full_name:    str


# ── Endpoints ────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    user = User(
        id=str(uuid.uuid4()),
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        country=req.country,
        phone=req.phone,
        plan=PlanEnum.FREE,
        status=StatusEnum.TRIAL,
        trial_ends_at=datetime.utcnow() + timedelta(days=14),
    )
    db.add(user)
    db.add(AuditLog(
        user_id=user.id,
        action="REGISTER",
        ip_address=request.client.host,
        details=f"Nouveau compte {req.email}",
    ))
    await db.commit()

    token = create_token({"user_id": user.id, "email": user.email, "plan": user.plan.value})
    return TokenResponse(
        access_token=token,
        plan=user.plan.value,
        status=user.status.value,
        full_name=user.full_name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    if user.status == StatusEnum.SUSPENDED:
        raise HTTPException(status_code=403, detail="Compte suspendu")

    db.add(AuditLog(
        user_id=user.id,
        action="LOGIN",
        ip_address=request.client.host,
        details="Connexion réussie",
    ))
    await db.commit()

    token = create_token({"user_id": user.id, "email": user.email, "plan": user.plan.value})
    return TokenResponse(
        access_token=token,
        plan=user.plan.value,
        status=user.status.value,
        full_name=user.full_name,
    )


@router.get("/me")
async def me(authorization: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    try:
        data = decode_token(authorization.split(" ")[1])
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

    result = await db.execute(select(User).where(User.id == data.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    return {
        "id":            user.id,
        "email":         user.email,
        "full_name":     user.full_name,
        "plan":          user.plan.value,
        "status":        user.status.value,
        "country":       user.country,
        "trial_ends_at": user.trial_ends_at,
        "created_at":    user.created_at,
    }
