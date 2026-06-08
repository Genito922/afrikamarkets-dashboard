"""
Afrika Markets Intelligence — FastAPI Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from backend.app.core.database import init_db
from backend.app.routers import auth, licences, payments
from backend.app.routers import market, analysis, intel
from backend.app.routers import african_markets


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init DB (create tables si nécessaire)
    await init_db()
    await seed_initial_users()
    # Démarrage du scheduler de scraping
    from backend.app.pipeline.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Afrika Markets Intelligence API",
    version="2.0.0",
    description="Market Intelligence Platform for African Frontier Markets — Auth, Licences, Data, Paiements",
    lifespan=lifespan,
)

# CORS — Streamlit Cloud + localhost dev
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://sentinel-lccafrika.space,https://afrika-markets.streamlit.app,http://localhost:8501,http://localhost:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(licences.router)
app.include_router(payments.router)
app.include_router(market.router)
app.include_router(analysis.router)
app.include_router(intel.router)
app.include_router(african_markets.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "afrika-markets-intelligence-api", "version": "2.0.0"}


@app.post("/admin/seed-history")
async def force_seed_history(days: int = 40, secret: str = ""):
    """Déclenche manuellement le seed historique BRVM (admin seulement)."""
    admin_secret = os.getenv("ADMIN_SECRET", "")
    if not admin_secret or secret != admin_secret:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Accès refusé")
    import asyncio
    from backend.app.pipeline.jobs import job_seed_history
    asyncio.create_task(job_seed_history(days=days))
    return {"status": "started", "days": days}


async def seed_initial_users():
    """Seed les comptes testeurs au démarrage si la DB est vide."""
    import uuid
    from backend.app.core.security import hash_password
    from backend.app.core.database import AsyncSessionLocal
    from backend.app.models.models import User, PlanEnum, StatusEnum
    from sqlalchemy import select
    from datetime import datetime, timedelta

    async with AsyncSessionLocal() as s:
        TESTERS = [
            ("testeur1@afrikamarkets.com", "Test@Afrika1",  "Testeur Un",    "CI", False),
            ("testeur2@afrikamarkets.com", "Test@Afrika2",  "Testeur Deux",  "SN", False),
            ("testeur3@afrikamarkets.com", "Test@Afrika3",  "Testeur Trois", "CA", False),
            ("testeur4@afrikamarkets.com", "Test@Afrika4",  "Testeur Quatre","FR", False),
            ("testeur5@afrikamarkets.com", "Test@Afrika5",  "Testeur Cinq",  "BF", False),
            ("ndoubajeanclaude@outlook.com", "Afrika@Admin2024!", "Jean-Claude N'Douba", "CI", True),
        ]
        created = updated = 0
        for email, pwd, name, country, is_admin in TESTERS:
            res = await s.execute(select(User).where(User.email == email))
            u = res.scalar_one_or_none()
            if u:
                u.hashed_password = hash_password(pwd)
                u.plan = PlanEnum.EXPERT
                u.status = StatusEnum.ACTIVE
                u.is_admin = is_admin
                u.trial_ends_at = datetime.utcnow() + timedelta(days=365)
                updated += 1
            else:
                s.add(User(
                    id=str(uuid.uuid4()),
                    email=email,
                    hashed_password=hash_password(pwd),
                    full_name=name,
                    country=country,
                    plan=PlanEnum.EXPERT,
                    status=StatusEnum.ACTIVE,
                    is_admin=is_admin,
                    trial_ends_at=datetime.utcnow() + timedelta(days=365),
                ))
                created += 1
        await s.commit()
        print(f"[Seed] {created} crees, {updated} mis a jour")
