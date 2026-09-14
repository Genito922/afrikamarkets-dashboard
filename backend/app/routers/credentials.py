"""
Gestion des credentials broker chiffrés — /credentials
Accès : plan PRO+ (les bots live nécessitent EXPERT, mais stocker des clés dès PRO)
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import json

from backend.app.core.database import get_db
from backend.app.core.deps import require_plan
from backend.app.core.encryption import encrypt_secret, decrypt_secret
from backend.app.models.models import PlanEnum, UserBrokerCredential, User

router = APIRouter(
    prefix="/credentials",
    tags=["credentials"],
    dependencies=[Depends(require_plan(PlanEnum.PRO))],
)

SUPPORTED_BROKERS = {"binance", "exness", "deriv"}


class CredentialCreate(BaseModel):
    broker: str
    api_key: str | None = None
    api_secret: str | None = None
    extra: dict | None = None      # {"token": "...", "login": 123, "server": "Exness-MT5Real"}
    label: str = "default"
    is_testnet: bool = False


class CredentialOut(BaseModel):
    id: str
    broker: str
    label: str
    is_testnet: bool
    has_api_key: bool
    has_api_secret: bool
    has_extra: bool

    class Config:
        from_attributes = True


@router.post("", response_model=CredentialOut, status_code=201)
async def save_credential(
    body: CredentialCreate,
    user: User = Depends(require_plan(PlanEnum.PRO)),
    db: AsyncSession = Depends(get_db),
):
    if body.broker not in SUPPORTED_BROKERS:
        raise HTTPException(400, f"Broker non supporté. Valeurs : {SUPPORTED_BROKERS}")

    # Upsert par (user_id, broker, label)
    result = await db.execute(
        select(UserBrokerCredential).where(
            UserBrokerCredential.user_id == user.id,
            UserBrokerCredential.broker == body.broker,
            UserBrokerCredential.label == body.label,
        )
    )
    cred = result.scalar_one_or_none()

    if cred is None:
        cred = UserBrokerCredential(
            user_id=user.id,
            broker=body.broker,
            label=body.label,
        )
        db.add(cred)

    if body.api_key is not None:
        cred.api_key_enc = encrypt_secret(body.api_key)
    if body.api_secret is not None:
        cred.api_secret_enc = encrypt_secret(body.api_secret)
    if body.extra is not None:
        cred.extra_enc = encrypt_secret(json.dumps(body.extra))
    cred.is_testnet = body.is_testnet

    await db.commit()
    await db.refresh(cred)

    return CredentialOut(
        id=cred.id,
        broker=cred.broker,
        label=cred.label,
        is_testnet=cred.is_testnet,
        has_api_key=bool(cred.api_key_enc),
        has_api_secret=bool(cred.api_secret_enc),
        has_extra=bool(cred.extra_enc),
    )


@router.get("", response_model=list[CredentialOut])
async def list_credentials(
    user: User = Depends(require_plan(PlanEnum.PRO)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserBrokerCredential).where(UserBrokerCredential.user_id == user.id)
    )
    creds = result.scalars().all()
    return [
        CredentialOut(
            id=c.id,
            broker=c.broker,
            label=c.label,
            is_testnet=c.is_testnet,
            has_api_key=bool(c.api_key_enc),
            has_api_secret=bool(c.api_secret_enc),
            has_extra=bool(c.extra_enc),
        )
        for c in creds
    ]


@router.delete("/{credential_id}", status_code=204)
async def delete_credential(
    credential_id: str,
    user: User = Depends(require_plan(PlanEnum.PRO)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserBrokerCredential).where(
            UserBrokerCredential.id == credential_id,
            UserBrokerCredential.user_id == user.id,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(404, "Credential introuvable")
    await db.delete(cred)
    await db.commit()
