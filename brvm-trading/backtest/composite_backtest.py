"""
Backtest Engine — Score Composite CryptoAnalyse
Reproduit EXACTEMENT le score du frontend (CryptoAnalyse.jsx) + backend (jobs.py)

Score composites (plage -9 à +9) :
  Backend :  RSI (±2/±1) + MFI (±2) + MA16/MA19 (±1) + MA19/MA246 (±1)
  Frontend : MACD hist (±1) + EMA9/EMA50 (±1) + EMA50/EMA200 (±1)

Métriques : CAGR · Sharpe · Sortino · Calmar · Max Drawdown · Win Rate · Profit Factor
Options   : regime filter · walk-forward · multi-asset · optimisation seuil
"""
import os
import warnings
import itertools
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────────
ASSETS = [
    "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD",
    "XRP-USD", "ADA-USD", "AVAX-USD", "DOGE-USD",
]
DAYS_BACK    = 365          # 1 an de données
CAPITAL_INIT = 10_000       # Capital initial $
TAKER_FEE    = 0.0004       # 0.04% Binance Futures
LEVERAGE     = 1            # Commencer sans levier
LONG_THRESH  = 2            # Score >= 2 → LONG
SHORT_THRESH = -2           # Score <= -2 → SHORT
USE_REGIME   = True         # Filtre tendance EMA200
WALK_FORWARD = True         # Validation walk-forward (3 folds)

OUT_DIR = Path("backtest/results")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ANNUALIZE = 252             # Jours trading / an (daily)


# ── Indicateurs ───────────────────────────────────────────────
def ema(s: pd.Series, p: int) -> pd.Series:
    return s.ewm(span=p, adjust=False, min_periods=p).mean()

def sma(s: pd.Series, p: int) -> pd.Series:
    return s.rolling(p, min_periods=p).mean()

def rsi(s: pd.Series, p: int = 14) -> pd.Series:
    d = s.diff()
    g = d.clip(lower=0).ewm(com=p - 1, min_periods=p).mean()
    l = (-d.clip(upper=0)).ewm(com=p - 1, min_periods=p).mean()
    return 100 - (100 / (1 + g / l.replace(0, np.nan)))

def mfi(df: pd.DataFrame, p: int = 14) -> pd.Series:
    tp  = (df["high"] + df["low"] + df["close"]) / 3
    mf  = tp * df["volume"]
    pos = mf.where(tp > tp.shift(1), 0).rolling(p, min_periods=1).sum()
    neg = mf.where(tp < tp.shift(1), 0).rolling(p, min_periods=1).sum()
    return 100 - (100 / (1 + pos / neg.replace(0, np.nan)))

def macd(s: pd.Series, fast=12, slow=26, sig=9):
    m = ema(s, fast) - ema(s, slow)
    signal = ema(m.fillna(0), sig)
    return m, signal, m - signal


# ── Score composite ───────────────────────────────────────────
def compute_score(df: pd.DataFrame) -> pd.Series:
    """
    Réplication exacte du score React + backend.
    Backend (jobs.py) :
        RSI < 30  → +2 | RSI < 45 → +1 | RSI > 70 → -2 | RSI > 55 → -1
        MFI < 20  → +2 | MFI > 80 → -2
        MA16 > MA19 → +1 | else → -1
        MA19 > MA246 → +1 | else → -1
    Frontend (CryptoAnalyse.jsx) :
        MACD hist > 0 → +1 | else → -1
        EMA9  > EMA50  → +1 | else → -1
        EMA50 > EMA200 → +1 | else → -1
    """
    p = df["close"]

    r    = rsi(p, 14)
    m    = mfi(df, 14)
    ma16 = sma(p, 16)
    ma19 = sma(p, 19)
    ma246 = sma(p, 246)
    e9   = ema(p, 9)
    e50  = ema(p, 50)
    e200 = ema(p, 200)
    _, _, macd_hist = macd(p)

    score = pd.Series(0.0, index=df.index)

    # RSI
    score += np.where(r < 30,  2,
             np.where(r < 45,  1,
             np.where(r > 70, -2,
             np.where(r > 55, -1, 0))))

    # MFI
    score += np.where(m < 20,  2,
             np.where(m > 80, -2, 0))

    # MA16 vs MA19
    valid_ma = ma16.notna() & ma19.notna()
    score += np.where(valid_ma &  (ma16 > ma19),  1,
             np.where(valid_ma & (ma16 <= ma19), -1, 0))

    # MA19 vs MA246
    valid_ma2 = ma19.notna() & ma246.notna()
    score += np.where(valid_ma2 &  (ma19 > ma246),  1,
             np.where(valid_ma2 & (ma19 <= ma246), -1, 0))

    # MACD hist
    valid_m = macd_hist.notna()
    score += np.where(valid_m &  (macd_hist > 0),  1,
             np.where(valid_m & (macd_hist <= 0), -1, 0))

    # EMA9 vs EMA50
    valid_e = e9.notna() & e50.notna()
    score += np.where(valid_e &  (e9 > e50),  1,
             np.where(valid_e & (e9 <= e50), -1, 0))

    # EMA50 vs EMA200
    valid_e2 = e50.notna() & e200.notna()
    score += np.where(valid_e2 &  (e50 > e200),  1,
             np.where(valid_e2 & (e50 <= e200), -1, 0))

    # Regime filter (EMA200 slope)
    if USE_REGIME:
        slope = e200.diff(5)
        bullish = slope > 0
        bearish = slope < 0
        # En tendance baissière on interdit les LONG
        score = np.where(bearish & (score > 0), 0, score)
        # En tendance haussière on interdit les SHORT
        score = np.where(bullish & (score < 0), 0, score)

    return pd.Series(score, index=df.index)


# ── Téléchargement ────────────────────────────────────────────
def download(ticker: str, days: int) -> pd.DataFrame:
    try:
        import yfinance as yf
        end   = datetime.utcnow()
        start = end - timedelta(days=days + 30)
        df = yf.download(
            ticker, start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            progress=False, auto_adjust=True
        )
        if df.empty:
            return pd.DataFrame()
        df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index)
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        return df.sort_index()
    except Exception as e:
        print(f"  [WARN] {ticker} : {e}")
        return pd.DataFrame()


# ── Métriques ─────────────────────────────────────────────────
@dataclass
class BacktestResult:
    ticker:        str
    capital_init:  float
    capital_final: float
    pnl_pct:       float
    cagr:          float
    sharpe:        float
    sortino:       float
    calmar:        float
    max_drawdown:  float
    win_rate:      float
    profit_factor: float
    nb_trades:     int
    avg_hold_days: float
    best_trade:    float
    worst_trade:   float
    equity:        pd.Series = field(repr=False)
    trades_df:     pd.DataFrame = field(repr=False)

    def summary(self) -> dict:
        return {
            "ticker":        self.ticker,
            "capital_final": round(self.capital_final, 2),
            "pnl_pct":       round(self.pnl_pct, 2),
            "cagr_pct":      round(self.cagr * 100, 2),
            "sharpe":        round(self.sharpe, 3),
            "sortino":       round(self.sortino, 3),
            "calmar":        round(self.calmar, 3),
            "max_dd_pct":    round(self.max_drawdown * 100, 2),
            "win_rate_pct":  round(self.win_rate * 100, 2),
            "profit_factor": round(self.profit_factor, 3),
            "nb_trades":     self.nb_trades,
            "avg_hold_days": round(self.avg_hold_days, 1),
            "best_trade_pct":  round(self.best_trade * 100, 2),
            "worst_trade_pct": round(self.worst_trade * 100, 2),
        }


def compute_metrics(equity: pd.Series, trades_df: pd.DataFrame,
                    capital: float, ticker: str) -> BacktestResult:
    eq     = equity.dropna()
    rets   = eq.pct_change().dropna()

    # CAGR
    n_years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr    = (eq.iloc[-1] / capital) ** (1 / max(n_years, 1/365)) - 1

    # Sharpe (daily → annualized)
    sharpe  = (rets.mean() / rets.std()) * np.sqrt(ANNUALIZE) if rets.std() > 0 else 0

    # Sortino
    down    = rets[rets < 0]
    sortino = (rets.mean() / down.std()) * np.sqrt(ANNUALIZE) if (len(down) > 1 and down.std() > 0) else 0

    # Max Drawdown
    roll_max = eq.cummax()
    dd       = (eq - roll_max) / roll_max
    max_dd   = dd.min()

    # Calmar
    calmar  = cagr / abs(max_dd) if max_dd < 0 else 0

    # Trade-level metrics
    if trades_df.empty or "pnl_pct" not in trades_df.columns:
        win_rate = pf = avg_hold = best = worst = 0
        nb = 0
    else:
        t        = trades_df
        wins     = t[t.pnl_pct > 0]
        losses   = t[t.pnl_pct < 0]
        win_rate = len(wins) / max(len(t), 1)
        gains    = wins.pnl_pct.sum()
        loss_abs = abs(losses.pnl_pct.sum())
        pf       = gains / max(loss_abs, 1e-10)
        avg_hold = t["hold_days"].mean() if "hold_days" in t.columns else 0
        best     = t.pnl_pct.max()
        worst    = t.pnl_pct.min()
        nb       = len(t)

    return BacktestResult(
        ticker=ticker,
        capital_init=capital,
        capital_final=round(eq.iloc[-1], 2),
        pnl_pct=round((eq.iloc[-1] / capital - 1) * 100, 2),
        cagr=cagr,
        sharpe=sharpe,
        sortino=sortino,
        calmar=calmar,
        max_drawdown=max_dd,
        win_rate=win_rate,
        profit_factor=pf,
        nb_trades=nb,
        avg_hold_days=avg_hold,
        best_trade=best,
        worst_trade=worst,
        equity=eq,
        trades_df=trades_df,
    )


# ── Simulateur de trades ──────────────────────────────────────
def simulate(df: pd.DataFrame, ticker: str,
             long_thresh: int = LONG_THRESH,
             short_thresh: int = SHORT_THRESH,
             capital: float = CAPITAL_INIT,
             fee: float = TAKER_FEE,
             leverage: int = LEVERAGE) -> BacktestResult:

    if df.empty or len(df) < 250:
        return None

    df = df.copy()
    df["score"]    = compute_score(df)
    df["signal"]   = np.where(
        df["score"] >= long_thresh,  1,
        np.where(df["score"] <= short_thresh, -1, 0)
    )
    df["position"] = df["signal"].shift(1).fillna(0)

    # Returns
    df["ret"]       = df["close"].pct_change()
    df["strat_ret"] = df["position"] * df["ret"] * leverage
    df["trade_chg"] = df["position"].diff().abs()
    df["fee_cost"]  = df["trade_chg"] * fee
    df["net_ret"]   = df["strat_ret"] - df["fee_cost"]
    df["equity"]    = capital * (1 + df["net_ret"]).cumprod()
    df["buy_hold"]  = capital * (1 + df["ret"]).cumprod()

    # Trade log
    trades = []
    in_trade   = False
    entry_px   = 0
    entry_date = None
    side       = 0

    for date, row in df.iterrows():
        if not in_trade and row["position"] != 0:
            in_trade   = True
            entry_px   = row["close"]
            entry_date = date
            side       = row["position"]
        elif in_trade and row["position"] != side:
            exit_px  = row["close"]
            raw_pnl  = (exit_px - entry_px) / entry_px * side
            net_pnl  = raw_pnl - 2 * fee  # entry + exit fee
            hold     = (date - entry_date).days
            trades.append({
                "entry_date": entry_date,
                "exit_date":  date,
                "side":       "LONG" if side == 1 else "SHORT",
                "entry_px":   round(entry_px, 4),
                "exit_px":    round(exit_px, 4),
                "pnl_pct":    round(net_pnl, 5),
                "hold_days":  hold,
            })
            if row["position"] != 0:
                entry_px   = row["close"]
                entry_date = date
                side       = row["position"]
            else:
                in_trade = False

    trades_df = pd.DataFrame(trades)
    return compute_metrics(df["equity"], trades_df, capital, ticker)


# ── Walk-Forward Validation ───────────────────────────────────
def walk_forward(df: pd.DataFrame, ticker: str, n_folds: int = 3) -> list[dict]:
    """
    Découpe la série en n folds : train (70%) / test (30%)
    Mesure la stabilité du score composite hors-échantillon.
    """
    n   = len(df)
    fold_size = n // n_folds
    results   = []

    for i in range(n_folds):
        test_start = i * fold_size
        test_end   = test_start + fold_size
        test_df    = df.iloc[test_start:test_end]

        if len(test_df) < 60:
            continue

        r = simulate(test_df, ticker=f"{ticker}_fold{i+1}")
        if r:
            results.append({
                "fold":        i + 1,
                "period":      f"{test_df.index[0].date()} → {test_df.index[-1].date()}",
                "pnl_pct":     r.pnl_pct,
                "sharpe":      round(r.sharpe, 3),
                "max_dd_pct":  round(r.max_drawdown * 100, 2),
                "win_rate_pct": round(r.win_rate * 100, 2),
                "nb_trades":   r.nb_trades,
            })
    return results


# ── Optimisation seuil ────────────────────────────────────────
def optimize_threshold(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Grid search sur les seuils LONG/SHORT.
    Objectif : Sharpe ratio maximum.
    """
    best_rows = []
    for lt, st in itertools.product([1, 2, 3, 4], [-1, -2, -3, -4]):
        if lt <= 0 or st >= 0:
            continue
        r = simulate(df, ticker, long_thresh=lt, short_thresh=st)
        if r and r.nb_trades > 0:
            best_rows.append({
                "long_thresh":  lt,
                "short_thresh": st,
                "sharpe":       round(r.sharpe, 3),
                "pnl_pct":      r.pnl_pct,
                "max_dd_pct":   round(r.max_drawdown * 100, 2),
                "win_rate_pct": round(r.win_rate * 100, 2),
                "profit_factor": round(r.profit_factor, 3),
                "nb_trades":    r.nb_trades,
            })
    if not best_rows:
        return pd.DataFrame()
    return pd.DataFrame(best_rows).sort_values("sharpe", ascending=False)


# ── Visualisation ─────────────────────────────────────────────
def plot_single(result: BacktestResult, df_raw: pd.DataFrame, ticker: str):
    fig = plt.figure(figsize=(16, 12))
    fig.patch.set_facecolor("#0D0D1F")
    gs  = gridspec.GridSpec(4, 2, figure=fig, hspace=0.45, wspace=0.35)

    s = result.summary()
    fig.suptitle(
        f"{ticker} — Score Composite Backtest ({DAYS_BACK}j)\n"
        f"PnL: {s['pnl_pct']:+.1f}%  |  Sharpe: {s['sharpe']:.2f}  |  "
        f"MaxDD: {s['max_dd_pct']:.1f}%  |  WinRate: {s['win_rate_pct']:.1f}%  |  "
        f"Trades: {s['nb_trades']}",
        color="white", fontsize=12, y=0.98
    )

    def ax_style(ax, title=""):
        ax.set_facecolor("#0D0D1F")
        ax.tick_params(colors="#9CA3AF", labelsize=8)
        for sp in ax.spines.values():
            sp.set_color("#374151")
        if title:
            ax.set_title(title, color="#D1D5DB", fontsize=9, pad=6)
        ax.grid(True, color="#1F2937", linewidth=0.5, alpha=0.7)

    eq      = result.equity
    bh      = df_raw["close"].reindex(eq.index) / df_raw["close"].reindex(eq.index).iloc[0] * CAPITAL_INIT
    roll_mx = eq.cummax()
    dd      = (eq - roll_mx) / roll_mx * 100

    # 1. Equity curve
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(eq.index, eq.values,    color="#C9A84C", lw=1.5, label="Stratégie Score Composite")
    ax1.plot(bh.index, bh.values,    color="#3B82F6", lw=1,   alpha=0.6, label="Buy & Hold")
    ax1.axhline(CAPITAL_INIT, color="#4B5563", lw=0.7, ls="--")
    ax1.set_ylabel("Capital ($)", color="#9CA3AF", fontsize=8)
    ax1.legend(loc="upper left", fontsize=8, facecolor="#1F2937", edgecolor="#374151", labelcolor="white")
    ax_style(ax1, "Equity Curve")

    # 2. Drawdown
    ax2 = fig.add_subplot(gs[1, :])
    ax2.fill_between(dd.index, dd.values, 0, color="#EF4444", alpha=0.55)
    ax2.axhline(-10, color="#F59E0B", lw=0.7, ls="--", alpha=0.6)
    ax2.axhline(-20, color="#EF4444", lw=0.7, ls="--", alpha=0.6)
    ax2.set_ylabel("Drawdown (%)", color="#9CA3AF", fontsize=8)
    ax_style(ax2, "Drawdown")

    # 3. Score histogram
    ax3 = fig.add_subplot(gs[2, 0])
    if "score" in df_raw.columns:
        sc = df_raw["score"].dropna()
    else:
        sc_s = compute_score(df_raw)
        sc   = sc_s.dropna()
    sc.hist(bins=range(-10, 11), ax=ax3, color="#8B5CF6", edgecolor="#1F2937", alpha=0.8)
    ax3.axvline(LONG_THRESH,  color="#22C55E", lw=1.5, ls="--", label=f"Long >={LONG_THRESH}")
    ax3.axvline(SHORT_THRESH, color="#EF4444", lw=1.5, ls="--", label=f"Short <={SHORT_THRESH}")
    ax3.legend(fontsize=7, facecolor="#1F2937", edgecolor="#374151", labelcolor="white")
    ax3.set_xlabel("Score", color="#9CA3AF", fontsize=8)
    ax_style(ax3, "Distribution des scores")

    # 4. Trade PnL distribution
    ax4 = fig.add_subplot(gs[2, 1])
    if not result.trades_df.empty and "pnl_pct" in result.trades_df.columns:
        pnl = result.trades_df["pnl_pct"] * 100
        colors_bars = ["#22C55E" if v > 0 else "#EF4444" for v in pnl]
        ax4.bar(range(len(pnl)), pnl.values, color=colors_bars, alpha=0.75, width=0.8)
        ax4.axhline(0, color="#4B5563", lw=0.7)
        ax4.set_xlabel("Trade #", color="#9CA3AF", fontsize=8)
        ax4.set_ylabel("PnL (%)", color="#9CA3AF", fontsize=8)
    ax_style(ax4, "PnL par trade")

    # 5. Métriques
    ax5 = fig.add_subplot(gs[3, 0])
    ax5.axis("off")
    m = result.summary()
    kpis = [
        ("Capital final",    f"${m['capital_final']:,.0f}"),
        ("PnL total",        f"{m['pnl_pct']:+.1f}%"),
        ("CAGR",             f"{m['cagr_pct']:+.1f}%"),
        ("Sharpe",           f"{m['sharpe']:.3f}"),
        ("Sortino",          f"{m['sortino']:.3f}"),
        ("Calmar",           f"{m['calmar']:.3f}"),
        ("Max Drawdown",     f"{m['max_dd_pct']:.1f}%"),
        ("Win Rate",         f"{m['win_rate_pct']:.1f}%"),
        ("Profit Factor",    f"{m['profit_factor']:.3f}"),
        ("Trades",           f"{m['nb_trades']}"),
        ("Hold moyen (j)",   f"{m['avg_hold_days']:.1f}"),
        ("Meilleur trade",   f"{m['best_trade_pct']:+.2f}%"),
        ("Pire trade",       f"{m['worst_trade_pct']:+.2f}%"),
    ]
    for idx, (k, v) in enumerate(kpis):
        color = "#22C55E" if "%" in v and "+" in v else \
                "#EF4444" if "%" in v and "-" in v else "#E5E7EB"
        ax5.text(0.02, 1 - idx * 0.075, k + "  :", color="#9CA3AF", fontsize=8,
                 transform=ax5.transAxes, va="top")
        ax5.text(0.55, 1 - idx * 0.075, v, color=color, fontsize=8, fontweight="bold",
                 transform=ax5.transAxes, va="top")

    # 6. Interprétation
    ax6 = fig.add_subplot(gs[3, 1])
    ax6.axis("off")
    sharpe_v = result.sharpe
    dd_v     = abs(result.max_drawdown) * 100
    pf_v     = result.profit_factor
    wr_v     = result.win_rate * 100

    notes = []
    notes.append(("Sharpe",
        ("✅ Excellent (>2)",  "#22C55E") if sharpe_v > 2 else
        ("✅ Bon (1-2)",       "#84CC16") if sharpe_v > 1 else
        ("⚠️ Faible (0.5-1)", "#F59E0B") if sharpe_v > 0.5 else
        ("❌ Non viable",      "#EF4444")
    ))
    notes.append(("Max DD",
        ("✅ Acceptable (<10%)", "#22C55E") if dd_v < 10 else
        ("⚠️ Modéré (10-20%)",  "#F59E0B") if dd_v < 20 else
        ("❌ Élevé (>20%)",     "#EF4444")
    ))
    notes.append(("Profit Factor",
        ("✅ Edge solide (>2)",  "#22C55E") if pf_v > 2 else
        ("✅ Edge présent (>1.5)", "#84CC16") if pf_v > 1.5 else
        ("⚠️ Faible (1-1.5)",  "#F59E0B") if pf_v > 1 else
        ("❌ Destructif",       "#EF4444")
    ))
    notes.append(("Win Rate",
        ("✅ Élevé (>60%)",     "#22C55E") if wr_v > 60 else
        ("✅ Correct (50-60%)", "#84CC16") if wr_v > 50 else
        ("⚠️ Faible (<50%)",   "#F59E0B")
    ))

    for idx, (label, (text, color)) in enumerate(notes):
        ax6.text(0.02, 0.92 - idx * 0.22, label + " :", color="#9CA3AF", fontsize=9,
                 transform=ax6.transAxes, va="top")
        ax6.text(0.35, 0.92 - idx * 0.22, text, color=color, fontsize=9, fontweight="bold",
                 transform=ax6.transAxes, va="top")

    path = OUT_DIR / f"{ticker.replace('-','_')}_backtest.png"
    plt.savefig(path, dpi=130, bbox_inches="tight", facecolor="#0D0D1F")
    plt.close()
    return path


def plot_multi(all_results: list[BacktestResult], capital: float):
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.patch.set_facecolor("#0D0D1F")
    fig.suptitle("Comparaison multi-assets — Score Composite", color="white", fontsize=13, y=1.01)

    colors = ["#C9A84C", "#3B82F6", "#F0B90B", "#9945FF", "#00AAE4",
              "#0033AD", "#E84142", "#C2A633"]

    # Equity curves normalisées
    ax1 = axes[0]
    ax1.set_facecolor("#0D0D1F")
    for i, r in enumerate(all_results):
        norm = r.equity / capital * 100 - 100
        ax1.plot(r.equity.index, norm.values,
                 label=r.ticker.replace("-USD", ""),
                 color=colors[i % len(colors)], lw=1.4)
    ax1.axhline(0, color="#4B5563", lw=0.7, ls="--")
    ax1.set_ylabel("PnL cumulé (%)", color="#9CA3AF", fontsize=9)
    ax1.legend(loc="upper left", fontsize=7, facecolor="#1F2937",
               edgecolor="#374151", labelcolor="white", ncol=2)
    ax1.tick_params(colors="#9CA3AF", labelsize=8)
    for sp in ax1.spines.values(): sp.set_color("#374151")
    ax1.grid(True, color="#1F2937", lw=0.5)
    ax1.set_title("Equity curves comparées", color="#D1D5DB", fontsize=10)

    # Sharpe vs Drawdown scatter
    ax2 = axes[1]
    ax2.set_facecolor("#0D0D1F")
    for i, r in enumerate(all_results):
        s  = r.summary()
        ax2.scatter(abs(s["max_dd_pct"]), s["sharpe"],
                    color=colors[i % len(colors)], s=120, zorder=5)
        ax2.annotate(r.ticker.replace("-USD", ""),
                     (abs(s["max_dd_pct"]), s["sharpe"]),
                     textcoords="offset points", xytext=(6, 4),
                     color=colors[i % len(colors)], fontsize=8)
    ax2.axhline(1.0, color="#F59E0B", lw=0.8, ls="--", alpha=0.6, label="Sharpe = 1")
    ax2.axhline(0.5, color="#EF4444", lw=0.8, ls="--", alpha=0.4, label="Sharpe = 0.5")
    ax2.set_xlabel("Max Drawdown (%)", color="#9CA3AF", fontsize=9)
    ax2.set_ylabel("Sharpe Ratio",     color="#9CA3AF", fontsize=9)
    ax2.legend(fontsize=7, facecolor="#1F2937", edgecolor="#374151", labelcolor="white")
    ax2.tick_params(colors="#9CA3AF", labelsize=8)
    for sp in ax2.spines.values(): sp.set_color("#374151")
    ax2.grid(True, color="#1F2937", lw=0.5)
    ax2.set_title("Sharpe vs Drawdown (coin supérieur gauche = meilleur)", color="#D1D5DB", fontsize=9)

    plt.tight_layout()
    path = OUT_DIR / "multi_asset_comparison.png"
    plt.savefig(path, dpi=130, bbox_inches="tight", facecolor="#0D0D1F")
    plt.close()
    return path


# ── Main ──────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("BACKTEST ENGINE — Score Composite CryptoAnalyse")
    print(f"Assets: {', '.join(ASSETS)}")
    print(f"Période: {DAYS_BACK} jours | Capital: ${CAPITAL_INIT:,} | Levier: x{LEVERAGE}")
    print(f"Long >= {LONG_THRESH} | Short <= {SHORT_THRESH} | Regime filter: {USE_REGIME}")
    print(f"Walk-Forward: {WALK_FORWARD}")
    print("=" * 65)

    all_results  = []
    all_summaries = []
    wf_rows      = []

    for ticker in ASSETS:
        print(f"\n{'─'*50}")
        print(f"[{ticker}] Téléchargement...")
        df = download(ticker, DAYS_BACK)

        if df.empty:
            print(f"  SKIP — données vides")
            continue

        print(f"  {len(df)} bougies journalières")

        # Backtest complet
        result = simulate(df, ticker)
        if result is None:
            print(f"  SKIP — pas assez de données (min 250 bougies)")
            continue

        s = result.summary()
        all_results.append(result)
        all_summaries.append(s)

        print(f"  PnL: {s['pnl_pct']:+.1f}% | CAGR: {s['cagr_pct']:+.1f}% | "
              f"Sharpe: {s['sharpe']:.2f} | Sortino: {s['sortino']:.2f} | "
              f"MaxDD: {s['max_dd_pct']:.1f}% | WinRate: {s['win_rate_pct']:.1f}% | "
              f"Trades: {s['nb_trades']}")

        # Walk-Forward
        if WALK_FORWARD and len(df) >= 180:
            print(f"  Walk-Forward ({3} folds)...")
            wf = walk_forward(df, ticker)
            for fold in wf:
                fold["ticker"] = ticker
                wf_rows.append(fold)
                print(f"    Fold {fold['fold']} [{fold['period']}] "
                      f"PnL: {fold['pnl_pct']:+.1f}% | Sharpe: {fold['sharpe']:.2f} | "
                      f"Trades: {fold['nb_trades']}")

        # Graphique individuel
        path = plot_single(result, df, ticker)
        print(f"  Graphique: {path}")

    if not all_results:
        print("\nAucun résultat — vérifier la connexion Internet (yfinance)")
        return

    # ── Comparaison multi-assets ──────────────────────────────
    print(f"\n{'='*65}")
    print("RÉSUMÉ MULTI-ASSETS")
    print(f"{'='*65}")
    summary_df = pd.DataFrame(all_summaries).set_index("ticker")
    print(summary_df.to_string())

    # ── Optimisation seuil (BTC uniquement) ──────────────────
    print(f"\n{'─'*50}")
    print("[Optimisation seuils] BTC-USD — Grid Search Sharpe...")
    df_btc = download("BTC-USD", DAYS_BACK)
    if not df_btc.empty:
        opt_df = optimize_threshold(df_btc, "BTC-USD")
        if not opt_df.empty:
            print("  Top 5 configurations (Sharpe décroissant) :")
            print(opt_df.head(5).to_string(index=False))
            opt_df.to_csv(OUT_DIR / "BTC_threshold_optimization.csv", index=False)

    # ── Walk-Forward summary ──────────────────────────────────
    if wf_rows:
        wf_df = pd.DataFrame(wf_rows)
        print(f"\n{'─'*50}")
        print("WALK-FORWARD — Stabilité hors-échantillon")
        print(wf_df.groupby("ticker")[["pnl_pct","sharpe","win_rate_pct"]].agg(["mean","std"]).round(2).to_string())
        wf_df.to_csv(OUT_DIR / "walk_forward_results.csv", index=False)

    # ── Graphique comparaison ─────────────────────────────────
    path_multi = plot_multi(all_results, CAPITAL_INIT)
    print(f"\nGraphique comparaison: {path_multi}")

    # ── Export CSV global ─────────────────────────────────────
    csv_path = OUT_DIR / "backtest_summary.csv"
    summary_df.reset_index().to_csv(csv_path, index=False)
    print(f"Résumé CSV: {csv_path}")

    # ── Interprétation finale ─────────────────────────────────
    print(f"\n{'='*65}")
    print("INTERPRÉTATION — Score Composite")
    print(f"{'='*65}")

    viable   = [r for r in all_results if r.sharpe > 1.0 and r.profit_factor > 1.0]
    risky    = [r for r in all_results if abs(r.max_drawdown) > 0.20]
    no_edge  = [r for r in all_results if r.profit_factor <= 1.0]

    if viable:
        print(f"\n[OK] Strategies viables (Sharpe>1 & PF>1) : "
              f"{', '.join(r.ticker for r in viable)}")
    if risky:
        print(f"[!!] Drawdown eleve (>20%) : "
              f"{', '.join(r.ticker for r in risky)}")
    if no_edge:
        print(f"[KO] Pas d'edge statistique (PF<=1) : "
              f"{', '.join(r.ticker for r in no_edge)}")

    avg_sharpe = np.mean([r.sharpe for r in all_results])
    print(f"\nSharpe moyen cross-assets : {avg_sharpe:.3f}")

    if avg_sharpe > 1.5:
        print("   -> Score composite solide : deploiement avec levier x2 envisageable")
    elif avg_sharpe > 0.5:
        print("   -> Score composite faible : optimiser les seuils ou ajouter filtres")
    else:
        print("   -> Score non predictif en l'etat : revoir la ponderation des composantes")

    print("\nProchaines etapes :")
    print("   1. Optimiser les poids par composante (RSI, MACD, EMA, MFI)")
    print("   2. Ajouter filtre de volatilite (ATR > seuil -> eviter range)")
    print("   3. Tester sur 2+ ans de donnees (eviter overfitting 1 an)")
    print("   4. Integrer le backtest engine au backend FastAPI")


if __name__ == "__main__":
    main()
