"""
Reporting Service — Afrika Markets Intelligence
Lit paper_trades.db (SQLite) + regime_state.json et produit des métriques propres.
Appelé par le router /performance.
"""

import json
import math
import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

# ─── Chemins configurables par env ────────────────────────────────────────────

_REPO_ROOT = Path(__file__).parent.parent.parent.parent  # brvm-analyzer/
PAPER_DB_PATH = Path(
    os.getenv("PAPER_DB_PATH", _REPO_ROOT / "brvm-trading" / "paper" / "paper_trades.db")
)
REGIME_STATE_PATH = Path(
    os.getenv("REGIME_STATE_PATH", _REPO_ROOT / "backtest" / "regime_state.json")
)
CAPITAL_INIT = float(os.getenv("PAPER_CAPITAL", "10000"))
# Crypto trade 24/7 → 365 jours de rendements par an (vs 252 pour les actions).
# Le paper trading est exposé principalement BTC/ETH/SOL : facteur √365.
ANNUALIZE = 365


# ─── Helpers internes ─────────────────────────────────────────────────────────

def _conn():
    if not PAPER_DB_PATH.exists():
        return None
    return sqlite3.connect(str(PAPER_DB_PATH))


def _empty_overview():
    return {
        "equity": CAPITAL_INIT,
        "pnl_pct": 0.0,
        "sharpe": 0.0,
        "max_dd_pct": 0.0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "n_trades": 0,
        "n_open_trades": 0,
        "capital_init": CAPITAL_INIT,
        "since": None,
        "db_ready": False,
    }


def _trade_stats(df: pd.DataFrame) -> dict:
    """Calcule WR, PF, best/worst trade à partir d'un DataFrame de trades."""
    if df.empty:
        return {"win_rate": 0.0, "profit_factor": 0.0,
                "best_pct": 0.0, "worst_pct": 0.0, "n": 0}
    wins = df[df["pnl_pct"] > 0]
    losses = df[df["pnl_pct"] <= 0]
    gp = float(wins["pnl_pct"].sum()) if not wins.empty else 0.0
    gl = float(abs(losses["pnl_pct"].sum())) if not losses.empty else 0.0
    return {
        "win_rate": round(len(wins) / len(df) * 100, 1),
        "profit_factor": round(gp / gl, 3) if gl > 0 else 0.0,
        "best_pct": round(float(df["pnl_pct"].max()), 2),
        "worst_pct": round(float(df["pnl_pct"].min()), 2),
        "n": len(df),
    }


# ─── API publique ──────────────────────────────────────────────────────────────

def get_overview() -> dict:
    """KPIs snapshot : equity, PnL%, Sharpe, MaxDD, WR, PF, n_trades."""
    conn = _conn()
    if conn is None:
        return _empty_overview()
    try:
        snap = pd.read_sql(
            "SELECT ts, equity FROM portfolio_snapshots ORDER BY ts", conn
        )
        if snap.empty:
            return _empty_overview()

        equity_now = float(snap["equity"].iloc[-1])
        pnl_pct = (equity_now / CAPITAL_INIT - 1) * 100

        snap["ret"] = snap["equity"].pct_change().fillna(0)
        std = snap["ret"].std()
        sharpe = (snap["ret"].mean() / std * math.sqrt(ANNUALIZE)) if std > 0 else 0.0

        eq_arr = snap["equity"].values
        running_max = np.maximum.accumulate(eq_arr)
        dds = (eq_arr - running_max) / running_max * 100
        max_dd = float(dds.min())

        trade_df = pd.read_sql(
            "SELECT pnl_pct FROM trades WHERE status='CLOSED'", conn
        )
        open_count = pd.read_sql(
            "SELECT COUNT(*) as n FROM trades WHERE status='OPEN'", conn
        ).iloc[0]["n"]

        ts = _trade_stats(trade_df)
        return {
            "equity": round(equity_now, 2),
            "pnl_pct": round(pnl_pct, 2),
            "sharpe": round(sharpe, 3),
            "max_dd_pct": round(max_dd, 2),
            "win_rate": ts["win_rate"],
            "profit_factor": ts["profit_factor"],
            "n_trades": ts["n"],
            "n_open_trades": int(open_count),
            "capital_init": CAPITAL_INIT,
            "since": snap["ts"].iloc[0],
            "db_ready": True,
        }
    finally:
        conn.close()


def get_equity_series(range_days: int | None = None) -> list[dict]:
    """
    Courbe equity + drawdown % + PnL % agrégée en daily.
    range_days=None → tout l'historique.
    """
    conn = _conn()
    if conn is None:
        return []
    try:
        df = pd.read_sql(
            "SELECT ts, equity FROM portfolio_snapshots ORDER BY ts", conn
        )
        if df.empty:
            return []
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.set_index("ts").resample("1D").last().ffill().reset_index()

        if range_days:
            df = df.tail(range_days)

        eq = df["equity"].values
        running_max = np.maximum.accumulate(eq)
        df["drawdown_pct"] = (eq - running_max) / running_max * 100
        df["pnl_pct"] = (eq / CAPITAL_INIT - 1) * 100
        df["date"] = df["ts"].dt.strftime("%Y-%m-%d")

        return [
            {
                "date": row["date"],
                "equity": round(row["equity"], 2),
                "drawdown_pct": round(row["drawdown_pct"], 2),
                "pnl_pct": round(row["pnl_pct"], 2),
            }
            for _, row in df.iterrows()
        ]
    finally:
        conn.close()


_MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def get_monthly_returns() -> list[dict]:
    """
    Matrice rendements mensuels pivotée pour heatmap.
    Format : [{ "year": 2025, "Jan": 1.2, "Feb": -0.5, …, "Dec": null }, …]
    Les mois sans données (futurs ou avant démarrage) sont null.
    """
    conn = _conn()
    if conn is None:
        return []
    try:
        df = pd.read_sql(
            "SELECT ts, equity FROM portfolio_snapshots ORDER BY ts", conn
        )
        if df.empty:
            return []
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.set_index("ts").resample("1D").last().ffill()
        df["ret"] = df["equity"].pct_change()
        monthly = (
            df["ret"].resample("ME").apply(lambda x: (1 + x).prod() - 1) * 100
        )

        # Pivote en lignes année
        by_year: dict[int, dict[str, float]] = {}
        for ts, val in monthly.items():
            yr  = int(ts.year)
            mon = _MONTH_ABBR[ts.month - 1]
            by_year.setdefault(yr, {})[mon] = round(float(val), 2)

        # Construit les lignes — mois non encore écoulés → null
        rows = []
        for yr in sorted(by_year):
            row: dict = {"year": yr}
            for m in _MONTH_ABBR:
                row[m] = by_year[yr].get(m, None)
            rows.append(row)
        return rows
    finally:
        conn.close()


def get_subsystems() -> list[dict]:
    """Rapport par sous-système : Regime Engine, Signal B, Paper Executor."""
    result = []

    # ── 1. Regime Engine ──────────────────────────────────────────────────────
    regime_raw = {}
    run_at = None
    try:
        if REGIME_STATE_PATH.exists():
            with open(REGIME_STATE_PATH) as f:
                regime_raw = json.load(f)
            run_at = regime_raw.get("run_at")
    except Exception:
        pass

    assets_regime = []
    for sym, d in regime_raw.get("assets", {}).items():
        assets_regime.append({
            "symbol": sym,
            "regime": d.get("regime", "unknown"),
            "consec_days": d.get("consec_days", 0),
            "deploy_ready": d.get("deploy_ready", False),
            "signal_b": d.get("signal_b", 0),
            "dist_pct": d.get("dist_pct", 0.0),
            "rsi14": d.get("rsi14", 0.0),
            "mfi14": d.get("mfi14", 0.0),
            "flipped_up": d.get("flipped_up", False),
            "flipped_down": d.get("flipped_down", False),
        })

    n_deployed = sum(1 for a in assets_regime if a["deploy_ready"])
    result.append({
        "id": "regime",
        "name": "Regime Engine",
        "description": "Filtre macro EMA200/246 · détection Bull/Bear · flip alerts",
        "status": "active" if n_deployed > 0 else ("waiting" if assets_regime else "offline"),
        "assets": assets_regime,
        "n_deployed": n_deployed,
        "run_at": run_at,
    })

    # ── 2. Signal B ───────────────────────────────────────────────────────────
    conn = _conn()
    last_signals, sig_rate, sig_status = [], 0.0, "idle"
    try:
        if conn is not None:
            sig_df = pd.read_sql(
                "SELECT asset, regime, action, confidence, ts "
                "FROM signals ORDER BY ts DESC LIMIT 200",
                conn,
            )
            if not sig_df.empty:
                long_n = int((sig_df["action"] == "BUY").sum())
                sig_rate = round(long_n / len(sig_df) * 100, 1)
                last_signals = sig_df.head(10).to_dict("records")
                last_action = sig_df["action"].iloc[0]
                sig_status = "long" if last_action == "BUY" else "cash"
    except Exception:
        pass
    finally:
        if conn:
            conn.close()

    result.append({
        "id": "signal_b",
        "name": "Signal B (SMA16/19)",
        "description": "SMA16/19 + RSI>50 + MFI>50 + double confirmation 4H",
        "status": sig_status,
        "signal_rate_pct": sig_rate,
        "last_signals": last_signals,
    })

    # ── 3. Paper Executor ─────────────────────────────────────────────────────
    conn = _conn()
    exec_status = "inactive"
    closed_stats = _trade_stats(pd.DataFrame())
    n_open = 0
    try:
        if conn is not None:
            closed_df = pd.read_sql(
                "SELECT pnl_pct FROM trades WHERE status='CLOSED'", conn
            )
            n_open = int(
                pd.read_sql(
                    "SELECT COUNT(*) as n FROM trades WHERE status='OPEN'", conn
                ).iloc[0]["n"]
            )
            closed_stats = _trade_stats(closed_df)
            exec_status = (
                "active" if n_open > 0
                else ("idle" if closed_stats["n"] > 0 else "inactive")
            )
    except Exception:
        pass
    finally:
        if conn:
            conn.close()

    result.append({
        "id": "paper_executor",
        "name": "Paper Executor",
        "description": "Phase 1 BTC/ETH · Binance WebSocket · kill-switch DD>10%",
        "status": exec_status,
        "n_closed_trades": closed_stats["n"],
        "n_open_trades": n_open,
        "win_rate": closed_stats["win_rate"],
        "profit_factor": closed_stats["profit_factor"],
        "best_trade_pct": closed_stats["best_pct"],
        "worst_trade_pct": closed_stats["worst_pct"],
    })

    return result


def get_trades(limit: int = 50, offset: int = 0) -> dict:
    """Log des trades fermés avec pagination."""
    conn = _conn()
    if conn is None:
        return {"trades": [], "total": 0}
    try:
        total = int(
            pd.read_sql(
                "SELECT COUNT(*) as n FROM trades WHERE status='CLOSED'", conn
            ).iloc[0]["n"]
        )
        df = pd.read_sql(
            f"SELECT asset, entry_time, exit_time, entry_px, exit_px, "
            f"pnl_pct, fees, status "
            f"FROM trades WHERE status='CLOSED' "
            f"ORDER BY exit_time DESC "
            f"LIMIT {limit} OFFSET {offset}",
            conn,
        )
        return {
            "trades": df.to_dict("records") if not df.empty else [],
            "total": total,
        }
    finally:
        conn.close()
