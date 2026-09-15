"""
Reporting Service — Afrika Markets Intelligence
Lit bot_trades + trading_bots (PostgreSQL async).
Toutes les fonctions sont async — appelées directement par le router /performance.
"""

import math
import os

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

CAPITAL_INIT = float(os.getenv("PAPER_CAPITAL", "10000"))
ANNUALIZE    = 365

_MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _empty_overview():
    return {
        "equity":        CAPITAL_INIT,
        "pnl_pct":       0.0,
        "sharpe":        0.0,
        "max_dd_pct":    0.0,
        "win_rate":      0.0,
        "profit_factor": 0.0,
        "n_trades":      0,
        "n_open_trades": 0,
        "capital_init":  CAPITAL_INIT,
        "since":         None,
        "db_ready":      False,
    }


def _trade_stats(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"win_rate": 0.0, "profit_factor": 0.0,
                "best_pct": 0.0, "worst_pct": 0.0, "n": 0}
    wins   = df[df["pnl"] > 0]
    losses = df[df["pnl"] <= 0]
    gp = float(wins["pnl"].sum())        if not wins.empty   else 0.0
    gl = float(abs(losses["pnl"].sum())) if not losses.empty else 0.0
    n  = len(df)
    return {
        "win_rate":      round(len(wins) / n * 100, 1),
        "profit_factor": round(gp / gl, 3) if gl > 0 else 0.0,
        "best_pct":      round(float(df["pnl"].max()), 2),
        "worst_pct":     round(float(df["pnl"].min()), 2),
        "n":             n,
    }


async def _fetch_df(db: AsyncSession, sql: str) -> pd.DataFrame:
    try:
        result = await db.execute(text(sql))
        rows   = result.fetchall()
        cols   = list(result.keys())
        return pd.DataFrame(rows, columns=cols)
    except Exception:
        return pd.DataFrame()


# ─── API publique (async) ──────────────────────────────────────────────────────

async def get_overview(db: AsyncSession) -> dict:
    df = await _fetch_df(
        db, "SELECT pnl, created_at FROM bot_trades ORDER BY created_at"
    )
    if df.empty:
        return _empty_overview()

    df["created_at"] = pd.to_datetime(df["created_at"])
    df["cum_pnl"]    = df["pnl"].cumsum()
    equity_now       = CAPITAL_INIT + float(df["cum_pnl"].iloc[-1])
    pnl_pct          = (equity_now / CAPITAL_INIT - 1) * 100

    # Sharpe journalier
    daily = df.set_index("created_at")["pnl"].resample("1D").sum()
    eq_daily = (CAPITAL_INIT + daily.cumsum()).values
    if len(eq_daily) > 1:
        rets   = pd.Series(eq_daily).pct_change().dropna()
        std    = rets.std()
        sharpe = (rets.mean() / std * math.sqrt(ANNUALIZE)) if std > 0 else 0.0
    else:
        sharpe = 0.0

    # Max drawdown
    eq_arr      = np.array(eq_daily)
    running_max = np.maximum.accumulate(eq_arr)
    dds         = (eq_arr - running_max) / running_max * 100
    max_dd      = float(dds.min()) if len(dds) > 0 else 0.0

    ts = _trade_stats(df)
    return {
        "equity":        round(equity_now, 2),
        "pnl_pct":       round(pnl_pct, 2),
        "sharpe":        round(sharpe, 3),
        "max_dd_pct":    round(max_dd, 2),
        "win_rate":      ts["win_rate"],
        "profit_factor": ts["profit_factor"],
        "n_trades":      ts["n"],
        "n_open_trades": 0,
        "capital_init":  CAPITAL_INIT,
        "since":         str(df["created_at"].iloc[0]),
        "db_ready":      True,
    }


async def get_equity_series(db: AsyncSession, range_days: int | None = None) -> list[dict]:
    df = await _fetch_df(
        db, "SELECT pnl, created_at FROM bot_trades ORDER BY created_at"
    )
    if df.empty:
        return []

    df["created_at"] = pd.to_datetime(df["created_at"])
    daily = (
        df.set_index("created_at")["pnl"]
        .resample("1D").sum()
        .reset_index()
    )
    daily["equity"] = CAPITAL_INIT + daily["pnl"].cumsum()

    if range_days:
        daily = daily.tail(range_days)

    eq          = daily["equity"].values
    running_max = np.maximum.accumulate(eq)
    daily["drawdown_pct"] = (eq - running_max) / running_max * 100
    daily["pnl_pct"]      = (eq / CAPITAL_INIT - 1) * 100
    daily["date_str"]     = daily["created_at"].dt.strftime("%Y-%m-%d")

    return [
        {
            "date":         row["date_str"],
            "equity":       round(row["equity"], 2),
            "drawdown_pct": round(row["drawdown_pct"], 2),
            "pnl_pct":      round(row["pnl_pct"], 2),
        }
        for _, row in daily.iterrows()
    ]


async def get_monthly_returns(db: AsyncSession) -> list[dict]:
    df = await _fetch_df(
        db, "SELECT pnl, created_at FROM bot_trades ORDER BY created_at"
    )
    if df.empty:
        return []

    df["created_at"] = pd.to_datetime(df["created_at"])
    daily        = df.set_index("created_at")["pnl"].resample("1D").sum()
    equity_daily = CAPITAL_INIT + daily.cumsum()
    ret_daily    = equity_daily.pct_change().fillna(0)
    monthly      = ret_daily.resample("ME").apply(lambda x: (1 + x).prod() - 1) * 100

    by_year: dict[int, dict[str, float]] = {}
    for ts, val in monthly.items():
        yr  = int(ts.year)
        mon = _MONTH_ABBR[ts.month - 1]
        by_year.setdefault(yr, {})[mon] = round(float(val), 2)

    rows = []
    for yr in sorted(by_year):
        row: dict = {"year": yr}
        for m in _MONTH_ABBR:
            row[m] = by_year[yr].get(m, None)
        rows.append(row)
    return rows


async def get_subsystems(db: AsyncSession) -> list[dict]:
    bots_df   = await _fetch_df(
        db,
        "SELECT id, name, strategy, status, mode, pnl_total, trades_count, paper_balance "
        "FROM trading_bots ORDER BY created_at DESC LIMIT 20"
    )
    trades_df = await _fetch_df(
        db, "SELECT bot_id, pnl FROM bot_trades ORDER BY created_at DESC LIMIT 500"
    )

    running = int((bots_df["status"] == "running").sum()) if not bots_df.empty else 0
    ts      = _trade_stats(trades_df) if not trades_df.empty else _trade_stats(pd.DataFrame())

    bots_list = []
    if not bots_df.empty:
        for _, b in bots_df.iterrows():
            bots_list.append({
                "id":            b["id"],
                "name":          b.get("name", ""),
                "strategy":      b.get("strategy", ""),
                "status":        b.get("status", "stopped"),
                "mode":          b.get("mode", "paper"),
                "pnl_total":     round(float(b["pnl_total"] or 0), 2),
                "trades_count":  int(b["trades_count"] or 0),
                "paper_balance": round(float(b["paper_balance"] or CAPITAL_INIT), 2),
            })

    return [
        {
            "id":          "fleet",
            "name":        "Flotte de bots",
            "description": "SMA Crossover · Paper & Live · Binance · Deriv · Exness",
            "status":      "active" if running > 0 else ("idle" if bots_list else "offline"),
            "assets":      bots_list,
            "n_deployed":  running,
            "run_at":      None,
        },
        {
            "id":              "signal_b",
            "name":            "Signal B (SMA16/19)",
            "description":     "SMA16/19 + RSI>50 + MFI>50 · confirmation double timeframe",
            "status":          "active" if running > 0 else "idle",
            "signal_rate_pct": ts["win_rate"],
            "last_signals":    [],
        },
        {
            "id":               "paper_executor",
            "name":             "Paper Executor",
            "description":      "Phase 1 BTC/ETH · kill-switch DD>10%",
            "status":           "active" if running > 0 else ("idle" if ts["n"] > 0 else "inactive"),
            "n_closed_trades":  ts["n"],
            "n_open_trades":    running,
            "win_rate":         ts["win_rate"],
            "profit_factor":    ts["profit_factor"],
            "best_trade_pct":   ts["best_pct"],
            "worst_trade_pct":  ts["worst_pct"],
        },
    ]


async def get_trades(db: AsyncSession, limit: int = 50, offset: int = 0) -> dict:
    total_df = await _fetch_df(db, "SELECT COUNT(*) as n FROM bot_trades")
    total    = int(total_df.iloc[0]["n"]) if not total_df.empty else 0

    df = await _fetch_df(
        db,
        f"SELECT symbol, side, qty, entry_price, exit_price, pnl, reason, created_at "
        f"FROM bot_trades ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}"
    )
    if df.empty:
        return {"trades": [], "total": total}

    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    return {"trades": df.to_dict("records"), "total": total}
