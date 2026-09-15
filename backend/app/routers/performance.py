"""
Router /performance — Afrika Markets Intelligence
Métriques paper trading + sous-systèmes depuis PostgreSQL (bot_trades).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.deps import require_plan
from backend.app.models.models import PlanEnum

router = APIRouter(
    prefix="/performance",
    tags=["Performance"],
    dependencies=[Depends(require_plan(PlanEnum.EXPERT))],
)


@router.get("/overview")
async def overview(db: AsyncSession = Depends(get_db)):
    """KPIs snapshot : equity, PnL%, Sharpe, MaxDD, WR, PF, n_trades."""
    from backend.app.services.reporting import get_overview
    return await get_overview(db)


@router.get("/equity")
async def equity_series(
    range: str = Query("all", description="7d | 30d | 90d | all"),
    db: AsyncSession = Depends(get_db),
):
    """Série temporelle daily : equity, drawdown_pct, pnl_pct."""
    from backend.app.services.reporting import get_equity_series
    range_map = {"7d": 7, "30d": 30, "90d": 90, "all": None}
    return await get_equity_series(db, range_map.get(range))


@router.get("/monthly")
async def monthly_returns(db: AsyncSession = Depends(get_db)):
    """Matrice year × month → return_pct pour heatmap."""
    from backend.app.services.reporting import get_monthly_returns
    return await get_monthly_returns(db)


@router.get("/subsystems")
async def subsystems(db: AsyncSession = Depends(get_db)):
    """Flotte bots, Signal B, Paper Executor — état et métriques."""
    from backend.app.services.reporting import get_subsystems
    return await get_subsystems(db)


@router.get("/trades")
async def trades_log(
    limit:  int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Trades fermés paginés, triés par created_at DESC."""
    from backend.app.services.reporting import get_trades
    return await get_trades(db, limit, offset)
