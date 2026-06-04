"""
Afrika Markets Intelligence — FastAPI Backend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from backend.app.core.database import init_db
from backend.app.routers import auth, licences, payments
from backend.app.routers import market


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init DB (create tables si nécessaire)
    await init_db()
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


@app.get("/health")
async def health():
    return {"status": "ok", "service": "afrika-markets-intelligence-api", "version": "2.0.0"}
