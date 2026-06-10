"""
Router /performance — Afrika Markets Intelligence
Métriques paper trading + sous-systèmes.
L'accès est filtré côté frontend (ProtectedRoute minPlan="expert").
"""

from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool

router = APIRouter(prefix="/performance", tags=["Performance"])


@router.get("/overview")
async def overview():
    """KPIs snapshot : equity, PnL%, Sharpe, MaxDD, WR, PF, n_trades."""
    from backend.app.services.reporting import get_overview
    return await run_in_threadpool(get_overview)


@router.get("/equity")
async def equity_series(
    range: str = Query("all", description="7d | 30d | 90d | all"),
):
    """Série temporelle daily : equity, drawdown_pct, pnl_pct."""
    from backend.app.services.reporting import get_equity_series
    range_map = {"7d": 7, "30d": 30, "90d": 90, "all": None}
    return await run_in_threadpool(get_equity_series, range_map.get(range))


@router.get("/monthly")
async def monthly_returns():
    """Matrice year × month → return_pct pour heatmap."""
    from backend.app.services.reporting import get_monthly_returns
    return await run_in_threadpool(get_monthly_returns)


@router.get("/subsystems")
async def subsystems():
    """Regime Engine, Signal B, Paper Executor — état et métriques."""
    from backend.app.services.reporting import get_subsystems
    return await run_in_threadpool(get_subsystems)


@router.get("/trades")
async def trades_log(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Trades fermés paginés, triés par exit_time DESC."""
    from backend.app.services.reporting import get_trades
    return await run_in_threadpool(get_trades, limit, offset)
