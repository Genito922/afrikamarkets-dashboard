"""
Market Data Router — Afrika Markets Intelligence
GET /market/actions
GET /market/actions/{symbole}/history
GET /market/indices
GET /market/summary
POST /market/scrape  (déclenchement manuel)
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import date, timedelta

from backend.app.core.database import get_db
from backend.app.models.market_models import BrvmAction, BrvmIndex, BrvmMarketSummary

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/actions")
async def get_actions_latest(db: AsyncSession = Depends(get_db)):
    """Derniers cours de toutes les actions (date la plus récente en base)."""
    latest_row = await db.execute(
        select(BrvmAction.date).order_by(desc(BrvmAction.date)).limit(1)
    )
    latest_date = latest_row.scalar_one_or_none()
    if not latest_date:
        return {"date": None, "data": []}

    result = await db.execute(
        select(BrvmAction).where(BrvmAction.date == latest_date)
    )
    actions = result.scalars().all()
    return {
        "date": str(latest_date),
        "count": len(actions),
        "data": [
            {
                "symbole":      a.symbole,
                "nom":          a.nom,
                "secteur":      a.secteur,
                "cours":        a.cours,
                "cours_veille": a.cours_veille,
                "cours_ouv":    a.cours_ouv,
                "variation":    a.variation,
                "volume":       a.volume,
            }
            for a in actions
        ],
    }


@router.get("/actions/{symbole}/history")
async def get_action_history(
    symbole: str,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Historique OHLCV d'une action sur N jours (max 365)."""
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(BrvmAction)
        .where(BrvmAction.symbole == symbole.upper(), BrvmAction.date >= since)
        .order_by(BrvmAction.date)
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Aucune donnée pour {symbole.upper()}")
    return {
        "symbole": symbole.upper(),
        "days":    days,
        "count":   len(rows),
        "data": [
            {
                "date":         str(r.date),
                "cours":        r.cours,
                "cours_veille": r.cours_veille,
                "cours_ouv":    r.cours_ouv,
                "variation":    r.variation,
                "volume":       r.volume,
            }
            for r in rows
        ],
    }


@router.get("/indices")
async def get_indices_latest(db: AsyncSession = Depends(get_db)):
    """Derniers indices BRVM (marché + sectoriels)."""
    latest_row = await db.execute(
        select(BrvmIndex.date).order_by(desc(BrvmIndex.date)).limit(1)
    )
    latest_date = latest_row.scalar_one_or_none()
    if not latest_date:
        return {"date": None, "marche": [], "sectoriel": []}

    result = await db.execute(
        select(BrvmIndex).where(BrvmIndex.date == latest_date)
    )
    indices = result.scalars().all()
    out: dict = {"date": str(latest_date), "marche": [], "sectoriel": []}
    for idx in indices:
        entry = {
            "nom":          idx.nom,
            "cloture":      idx.cloture,
            "cloture_prec": idx.cloture_prec,
            "variation":    idx.variation,
            "var_ytd":      idx.var_ytd,
        }
        out[idx.type].append(entry)
    return out


@router.get("/summary")
async def get_market_summary(db: AsyncSession = Depends(get_db)):
    """Résumé global du marché (capitalisation, transactions)."""
    result = await db.execute(
        select(BrvmMarketSummary).order_by(desc(BrvmMarketSummary.date)).limit(1)
    )
    summary = result.scalar_one_or_none()
    if not summary:
        return {"date": None, "data": {}}
    return {
        "date": str(summary.date),
        "data": {
            "Capitalisation Actions":          summary.cap_actions_raw,
            "Capitalisation des obligations":  summary.cap_obligations_raw,
            "Valeur des transactions":         summary.transactions_raw,
        },
    }


@router.post("/scrape")
async def trigger_scrape_manual():
    """Déclenche un scraping immédiat (usage admin / dev)."""
    from backend.app.pipeline.jobs import job_scrape_market
    await job_scrape_market()
    return {"status": "ok", "message": "Scraping déclenché"}
