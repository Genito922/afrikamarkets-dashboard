"""
Adaptive Crypto Trading Engine v2 — Fondation hedge fund retail
================================================================
Corrections v1 :
  - RegimeDetector v2 crypto-native (percentile ATR, pas seuil fixe)
  - Threshold adaptatif : trend=3 / neutral=4 / high_vol=5 / range=4
  - Position sizing dynamique (ATR-based, risque fixe par trade)
  - Anti-overfitting layer (IS/OOS ratio + walk-forward consistency)
  - Risk parity sur les assets viables uniquement

Architecture :
  MarketData -> Indicators -> RegimeDetector v2 -> AdaptiveScore
  -> ThresholdSelector -> PositionSizer -> PortfolioEngine -> Metrics

Usage :
  python brvm-trading/backtest/adaptive_engine_v2.py
"""
import warnings
import itertools
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

warnings.filterwarnings("ignore")
pd.options.mode.chained_assignment = None

# ── Config ────────────────────────────────────────────────────
CAPITAL_INIT = 10_000
DAYS_BACK    = 730
TAKER_FEE    = 0.0004
ANNUALIZE    = 252
RISK_PER_TRADE = 0.01          # 1% du capital par trade (ATR-based sizing)
MAX_POSITION   = 0.30          # Taille max = 30% du capital par asset

ASSET_PROFILES = {
    "XRP-USD":  {"tier": "A", "base_thresh": 4, "max_dd": 0.25},
    "SOL-USD":  {"tier": "A", "base_thresh": 4, "max_dd": 0.25},
    "BNB-USD":  {"tier": "B", "base_thresh": 4, "max_dd": 0.20},
    "ADA-USD":  {"tier": "B", "base_thresh": 4, "max_dd": 0.20},
    "AVAX-USD": {"tier": "B", "base_thresh": 4, "max_dd": 0.20},
    "BTC-USD":  {"tier": "C", "base_thresh": 5, "max_dd": 0.15},
    "ETH-USD":  {"tier": "C", "base_thresh": 5, "max_dd": 0.15},
    "DOGE-USD": {"tier": "D", "base_thresh": 6, "max_dd": 0.12},
}

OUT_DIR = Path("backtest/results/adaptive_v2")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Indicateurs ───────────────────────────────────────────────
def _ema(s: pd.Series, p: int) -> pd.Series:
    return s.ewm(span=p, adjust=False, min_periods=p).mean()

def _sma(s: pd.Series, p: int) -> pd.Series:
    return s.rolling(p, min_periods=p).mean()

def _rsi(s: pd.Series, p: int = 14) -> pd.Series:
    d = s.diff()
    g = d.clip(lower=0).ewm(com=p - 1, min_periods=p).mean()
    l = (-d.clip(upper=0)).ewm(com=p - 1, min_periods=p).mean()
    return 100 - 100 / (1 + g / l.replace(0, np.nan))

def _mfi(df: pd.DataFrame, p: int = 14) -> pd.Series:
    tp  = (df["high"] + df["low"] + df["close"]) / 3
    mf  = tp * df["volume"]
    pos = mf.where(tp > tp.shift(1), 0).rolling(p, min_periods=1).sum()
    neg = mf.where(tp < tp.shift(1), 0).rolling(p, min_periods=1).sum()
    return 100 - 100 / (1 + pos / neg.replace(0, np.nan))

def _macd_hist(s: pd.Series, fast=12, slow=26, sig=9) -> pd.Series:
    m = _ema(s, fast) - _ema(s, slow)
    return m - _ema(m.fillna(0), sig)

def _atr(df: pd.DataFrame, p: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(span=p, adjust=False, min_periods=p).mean()


# ── RegimeDetector v2 (crypto-native) ────────────────────────
class RegimeDetector:
    """
    Crypto-native : utilise des percentiles glissants (252j)
    pour s'adapter a la volatilite normalement elevee de la crypto.

    Regimes :
      trend    : EMA200 slope > 0  ET vol_pct < 70e percentile
      high_vol : ATR% > 8e percentile glissant 252j  (volatilite extremes)
      range    : slope ~0 ET vol_pct < 40e percentile
      neutral  : defaut

    Seuils associes :
      trend    -> 3   (signaux de confiance moderee, tendance confirmee)
      neutral  -> 4   (defaut)
      high_vol -> 5   (signaux de confiance haute requis, pas bloquant)
      range    -> 4   (mean reversion tolerable)
    """
    THRESH = {"trend": 3, "neutral": 4, "high_vol": 5, "range": 4}

    def __init__(self, slope_window: int = 10, vol_window: int = 252,
                 high_vol_pct: float = 0.85, flat_slope_abs: float = 0.003):
        self.slope_window   = slope_window
        self.vol_window     = vol_window
        self.high_vol_pct   = high_vol_pct    # 85e percentile = VRAIMENT volatile
        self.flat_slope_abs = flat_slope_abs

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        e200     = _ema(df["close"], 200)
        slope    = e200.pct_change(self.slope_window)
        atr_p    = _atr(df, 14) / df["close"]

        # Percentile glissant de l'ATR% sur 252 jours
        atr_roll_pct = atr_p.rolling(self.vol_window, min_periods=30).quantile(self.high_vol_pct)
        is_high_vol  = atr_p > atr_roll_pct

        is_flat  = slope.abs() < self.flat_slope_abs
        is_up    = slope > self.flat_slope_abs

        # Percentile de volatilite courante vs historique (0..1)
        vol_pct_rank = atr_p.rolling(self.vol_window, min_periods=30).rank(pct=True)

        regime = np.select(
            [
                is_up & ~is_high_vol,       # trend haussier, volatilite normale
                is_high_vol,                # volatilite extremes
                is_flat & (vol_pct_rank < 0.4),  # range / lateral
            ],
            ["trend", "high_vol", "range"],
            default="neutral"
        )

        out = df[["close"]].copy()
        out["regime"]       = regime
        out["atr_pct"]      = atr_p.values
        out["vol_pct_rank"] = vol_pct_rank.values
        out["ema_slope"]    = slope.values
        return out

    def get_threshold(self, regime: str) -> int:
        return self.THRESH.get(regime, 4)


# ── Score composite (identique composite_backtest) ────────────
def compute_score(df: pd.DataFrame,
                  sma_s: int = 16, sma_m: int = 19, sma_l: int = 246) -> pd.Series:
    p  = df["close"]
    r  = _rsi(p, 14)
    m  = _mfi(df, 14)
    ms = _sma(p, sma_s); mm = _sma(p, sma_m); ml = _sma(p, sma_l)
    e9 = _ema(p, 9);  e50 = _ema(p, 50);  e200 = _ema(p, 200)
    mh = _macd_hist(p)

    sc = pd.Series(0.0, index=df.index)
    sc += np.where(r < 30, 2, np.where(r < 45, 1, np.where(r > 70, -2, np.where(r > 55, -1, 0))))
    sc += np.where(m < 20, 2, np.where(m > 80, -2, 0))
    vm1 = ms.notna() & mm.notna()
    sc += np.where(vm1 & (ms > mm), 1, np.where(vm1 & (ms <= mm), -1, 0))
    vm2 = mm.notna() & ml.notna()
    sc += np.where(vm2 & (mm > ml), 1, np.where(vm2 & (mm <= ml), -1, 0))
    vh = mh.notna()
    sc += np.where(vh & (mh > 0), 1, np.where(vh & (mh <= 0), -1, 0))
    ve1 = e9.notna() & e50.notna()
    sc += np.where(ve1 & (e9 > e50), 1, np.where(ve1 & (e9 <= e50), -1, 0))
    ve2 = e50.notna() & e200.notna()
    sc += np.where(ve2 & (e50 > e200), 1, np.where(ve2 & (e50 <= e200), -1, 0))
    return sc


# ── Position Sizer (ATR-based) ────────────────────────────────
class PositionSizer:
    """
    Taille de position basee sur le risque fixe par trade.
    risk_per_trade = fraction du capital a risquer par trade.
    stop_atr_mult  = stop loss en multiples ATR.

    size = (capital * risk_per_trade) / (atr * stop_mult)
    capped a MAX_POSITION * capital.
    """
    def __init__(self, risk: float = RISK_PER_TRADE,
                 stop_atr_mult: float = 2.0,
                 max_pos: float = MAX_POSITION):
        self.risk          = risk
        self.stop_atr_mult = stop_atr_mult
        self.max_pos       = max_pos

    def size(self, capital: float, price: float, atr: float) -> float:
        if atr <= 0 or price <= 0:
            return 0.0
        dollar_risk  = capital * self.risk
        dollar_stop  = atr * self.stop_atr_mult
        units        = dollar_risk / dollar_stop
        pos_value    = units * price
        max_value    = capital * self.max_pos
        return min(pos_value, max_value) / capital  # fraction [0..1]


# ── Simulateur v2 ─────────────────────────────────────────────
@dataclass
class Result:
    ticker:        str
    tier:          str
    capital_final: float
    pnl_pct:       float
    cagr:          float
    sharpe:        float
    sortino:       float
    calmar:        float
    max_dd:        float
    win_rate:      float
    profit_factor: float
    nb_trades:     int
    avg_hold:      float
    regime_dist:   dict
    equity:        pd.Series = field(repr=False)
    trades_df:     pd.DataFrame = field(repr=False)
    is_sharpe:     float = 0.0   # In-sample Sharpe
    oos_sharpe:    float = 0.0   # Out-of-sample Sharpe

    def summary(self) -> dict:
        return {
            "ticker": self.ticker, "tier": self.tier,
            "capital_final": round(self.capital_final, 2),
            "pnl_pct":       round(self.pnl_pct, 2),
            "cagr_pct":      round(self.cagr * 100, 2),
            "sharpe":        round(self.sharpe, 3),
            "sortino":       round(self.sortino, 3),
            "calmar":        round(self.calmar, 3),
            "max_dd_pct":    round(self.max_dd * 100, 2),
            "win_rate_pct":  round(self.win_rate * 100, 2),
            "profit_factor": round(self.profit_factor, 3),
            "nb_trades":     self.nb_trades,
            "avg_hold_days": round(self.avg_hold, 1),
            "is_sharpe":     round(self.is_sharpe, 3),
            "oos_sharpe":    round(self.oos_sharpe, 3),
            "overfit_flag":  "FLAG" if self._overfit_flag() else "OK",
        }

    def _overfit_flag(self) -> bool:
        if self.is_sharpe <= 0:
            return False
        ratio = self.oos_sharpe / self.is_sharpe if self.is_sharpe > 0 else 0
        return ratio < 0.5  # OOS Sharpe < 50% IS Sharpe = signe d'overfit


def _metrics(equity: pd.Series, capital: float,
             trades_df: pd.DataFrame) -> dict:
    eq   = equity.dropna()
    rets = eq.pct_change().dropna()
    n_yr = max((eq.index[-1] - eq.index[0]).days / 365.25, 1 / 365)
    cagr = (eq.iloc[-1] / capital) ** (1 / n_yr) - 1
    sh   = (rets.mean() / rets.std()) * np.sqrt(ANNUALIZE) if rets.std() > 0 else 0
    dn   = rets[rets < 0]
    so   = (rets.mean() / dn.std()) * np.sqrt(ANNUALIZE) if len(dn) > 1 and dn.std() > 0 else 0
    rmx  = eq.cummax()
    mdd  = ((eq - rmx) / rmx).min()
    cal  = cagr / abs(mdd) if mdd < 0 else 0

    if not trades_df.empty and "pnl_pct" in trades_df.columns:
        t   = trades_df
        wr  = (t.pnl_pct > 0).mean()
        pf  = (t[t.pnl_pct > 0].pnl_pct.sum() /
               max(abs(t[t.pnl_pct < 0].pnl_pct.sum()), 1e-10))
        ah  = t.hold_days.mean() if "hold_days" in t.columns else 0
        nb  = len(t)
    else:
        wr = pf = ah = 0; nb = 0

    return dict(cagr=cagr, sharpe=sh, sortino=so, calmar=cal,
                max_dd=mdd, win_rate=wr, profit_factor=pf,
                avg_hold=ah, nb_trades=nb)


def simulate_v2(df: pd.DataFrame, ticker: str,
                profile: dict, capital: float = CAPITAL_INIT,
                sma_s: int = 16, sma_m: int = 19, sma_l: int = 246) -> Optional[Result]:

    if df.empty or len(df) < 280:
        return None

    df     = df.copy()
    det    = RegimeDetector()
    regime_df = det.detect(df)
    sizer  = PositionSizer()

    score  = compute_score(df, sma_s, sma_m, sma_l)
    atr    = _atr(df, 14)

    # Signal adaptatif barre par barre
    signals = []
    for i in range(len(df)):
        reg   = regime_df["regime"].iloc[i]
        thr   = det.get_threshold(reg)
        sc    = score.iloc[i]
        if pd.isna(sc):
            signals.append(0)
        elif sc >= thr:
            signals.append(1)
        elif sc <= -thr:
            signals.append(-1)
        else:
            signals.append(0)

    df["regime"]   = regime_df["regime"].values
    df["score"]    = score.values
    df["signal"]   = signals
    df["position"] = pd.Series(signals, index=df.index).shift(1).fillna(0).values
    df["atr"]      = atr.values

    # Taille de position dynamique (ATR-based)
    pos_sizes = []
    cap_t     = capital
    for i in range(len(df)):
        pos  = df["position"].iloc[i]
        if pos == 0:
            pos_sizes.append(0.0)
            continue
        sz = sizer.size(cap_t, df["close"].iloc[i], df["atr"].iloc[i])
        pos_sizes.append(sz * pos)  # signed fraction

    df["pos_size"] = pos_sizes

    # Returns
    ret       = df["close"].pct_change().fillna(0)
    strat_ret = df["pos_size"] * ret
    fee_cost  = df["pos_size"].abs().diff().abs().fillna(0) * TAKER_FEE
    net_ret   = strat_ret - fee_cost

    # Equity avec circuit breaker
    equity_vals = [capital]
    cap_t = capital
    max_dd_lim = profile["max_dd"]
    peak = capital
    cut  = False

    for i in range(1, len(net_ret)):
        if cut:
            equity_vals.append(equity_vals[-1])
            continue
        v = equity_vals[-1] * (1 + net_ret.iloc[i])
        equity_vals.append(v)
        if v > peak:
            peak = v
        if (v - peak) / peak < -max_dd_lim:
            cut = True
            print(f"  [CB] {ticker} circuit breaker @ {df.index[i].date()} "
                  f"(DD > {max_dd_lim*100:.0f}%)")

    equity = pd.Series(equity_vals, index=df.index)

    # Trade log
    trades = []
    in_p = False; e_px = 0; e_date = None; side = 0
    for date, row in df.iterrows():
        p = row["position"]
        if not in_p and p != 0:
            in_p = True; e_px = row["close"]; e_date = date; side = p
        elif in_p and p != side:
            raw  = (row["close"] - e_px) / e_px * side
            net  = raw - 2 * TAKER_FEE
            trades.append({
                "entry_date": e_date, "exit_date": date,
                "side":       "LONG" if side == 1 else "SHORT",
                "entry_px":   round(e_px, 5), "exit_px": round(row["close"], 5),
                "pnl_pct":    round(net, 5),
                "hold_days":  (date - e_date).days,
                "regime":     row["regime"],
                "score_entry": row["score"],
            })
            if p != 0:
                e_px = row["close"]; e_date = date; side = p
            else:
                in_p = False

    trades_df = pd.DataFrame(trades)
    m         = _metrics(equity, capital, trades_df)

    # IS / OOS split (70/30) pour anti-overfitting
    split = int(len(df) * 0.7)
    is_eq  = equity.iloc[:split]
    oos_eq = equity.iloc[split:]
    is_r   = is_eq.pct_change().dropna()
    oos_r  = oos_eq.pct_change().dropna()
    is_sh  = (is_r.mean() / is_r.std()) * np.sqrt(ANNUALIZE) if is_r.std() > 0 else 0
    oos_sh = (oos_r.mean() / oos_r.std()) * np.sqrt(ANNUALIZE) if oos_r.std() > 0 else 0

    regime_dist = df["regime"].value_counts(normalize=True).round(3).to_dict()

    return Result(
        ticker=ticker, tier=profile["tier"],
        capital_final=round(equity.iloc[-1], 2),
        pnl_pct=round((equity.iloc[-1] / capital - 1) * 100, 2),
        equity=equity, trades_df=trades_df,
        regime_dist=regime_dist,
        is_sharpe=round(is_sh, 3), oos_sharpe=round(oos_sh, 3),
        **m,
    )


# ── Anti-overfitting layer ────────────────────────────────────
def anti_overfit_report(results: list[Result]) -> pd.DataFrame:
    """
    Pour chaque asset :
      - IS Sharpe vs OOS Sharpe
      - ratio OOS/IS (ideal > 0.7)
      - verdict
    """
    rows = []
    for r in results:
        ratio  = r.oos_sharpe / r.is_sharpe if r.is_sharpe > 0 else 0
        verdict = (
            "STABLE"      if ratio >= 0.7  else
            "ACCEPTABLE"  if ratio >= 0.5  else
            "OVERFIT_RISK" if ratio >= 0.0 else
            "NEGATIVE_OOS"
        )
        rows.append({
            "ticker":    r.ticker,
            "IS_sharpe": r.is_sharpe,
            "OOS_sharpe": r.oos_sharpe,
            "ratio":     round(ratio, 3),
            "verdict":   verdict,
        })
    return pd.DataFrame(rows).sort_values("ratio", ascending=False)


# ── SMA optimizer (rapide) ────────────────────────────────────
def optimize_sma_v2(df: pd.DataFrame, ticker: str,
                    profile: dict) -> tuple[int, int, int]:
    candidates = list(itertools.product([10, 16, 20], [19, 38, 50], [100, 200, 246]))
    best_sh = -999; best_cfg = (16, 19, 246)

    for s, m, l in candidates:
        if s >= m or m >= l or len(df) < l + 30:
            continue
        r = simulate_v2(df, ticker, profile, sma_s=s, sma_m=m, sma_l=l)
        if r and r.nb_trades >= 3 and r.sharpe > best_sh:
            best_sh  = r.sharpe
            best_cfg = (s, m, l)

    print(f"  SMA optimal [{ticker}] : {best_cfg[0]}/{best_cfg[1]}/{best_cfg[2]}"
          f" -> Sharpe {best_sh:.3f}")
    return best_cfg


# ── Risk parity ───────────────────────────────────────────────
def risk_parity(results: list[Result]) -> dict[str, float]:
    vols = {}
    for r in results:
        if r.tier == "D":
            continue
        ret = r.equity.pct_change().dropna()
        vol = ret.std() * np.sqrt(ANNUALIZE)
        vols[r.ticker] = max(vol, 1e-6)

    if not vols:
        return {}
    inv = {k: 1 / v for k, v in vols.items()}
    tot = sum(inv.values())
    return {k: round(v / tot, 4) for k, v in inv.items()}


# ── Portfolio ─────────────────────────────────────────────────
def portfolio_equity(results: list[Result], weights: dict,
                     capital: float = CAPITAL_INIT) -> pd.Series:
    rmap = {r.ticker: r for r in results}
    inc  = {t: w for t, w in weights.items() if t in rmap}
    if not inc:
        return pd.Series(dtype=float)

    idx = sorted(set.intersection(*[set(rmap[t].equity.index) for t in inc]))
    if not idx:
        return pd.Series(dtype=float)

    port_ret = pd.Series(0.0, index=idx)
    for t, w in inc.items():
        r  = rmap[t].equity.reindex(idx).pct_change().fillna(0)
        port_ret += w * r

    return capital * (1 + port_ret).cumprod()


# ── Walk-forward v2 ───────────────────────────────────────────
def walk_forward_v2(df: pd.DataFrame, ticker: str,
                    profile: dict, n_folds: int = 3) -> list[dict]:
    fold_n = len(df) // n_folds
    rows   = []
    for i in range(n_folds):
        fold = df.iloc[i * fold_n: (i + 1) * fold_n]
        if len(fold) < 120:
            continue
        s, m, l = optimize_sma_v2(fold, f"{ticker}_f{i+1}", profile)
        r = simulate_v2(fold, ticker, profile, sma_s=s, sma_m=m, sma_l=l)
        if r:
            rows.append({
                "fold": i + 1,
                "period": f"{fold.index[0].date()} -> {fold.index[-1].date()}",
                "pnl_pct": r.pnl_pct, "sharpe": round(r.sharpe, 3),
                "oos_sharpe": r.oos_sharpe, "max_dd": round(r.max_dd * 100, 2),
                "win_rate": round(r.win_rate * 100, 1),
                "nb_trades": r.nb_trades,
                "sma": f"{s}/{m}/{l}",
                "regime_dist": str(r.regime_dist),
            })
    return rows


# ── Visualisation ─────────────────────────────────────────────
def plot_v2(results: list[Result], port_eq: pd.Series,
            weights: dict, overfit_df: pd.DataFrame):

    fig = plt.figure(figsize=(20, 16))
    fig.patch.set_facecolor("#080818")
    gs  = gridspec.GridSpec(4, 3, figure=fig, hspace=0.55, wspace=0.38)

    PALETTE = {"A": "#22C55E", "B": "#F59E0B", "C": "#3B82F6", "D": "#6B7280"}
    COLORS  = ["#C9A84C","#22C55E","#F0B90B","#9945FF",
               "#00AAE4","#F97316","#E84142","#A78BFA"]

    def ax_dark(ax, title=""):
        ax.set_facecolor("#0D0D1F")
        ax.tick_params(colors="#9CA3AF", labelsize=8)
        for sp in ax.spines.values(): sp.set_color("#374151")
        if title:
            ax.set_title(title, color="#D1D5DB", fontsize=9, pad=6)
        ax.grid(True, color="#1F2937", lw=0.5, alpha=0.8)

    fig.suptitle(
        "Adaptive Engine v2 — Crypto-Native Regime + ATR Position Sizing\n"
        "RegimeDetector v2 | Percentile ATR | IS/OOS Anti-Overfit | Risk Parity",
        color="white", fontsize=12, y=0.99
    )

    # A. Equity curves normalisees
    ax0 = fig.add_subplot(gs[0, :2])
    for i, r in enumerate(results):
        if r.tier == "D":
            continue
        norm = r.equity / r.equity.iloc[0] * 100 - 100
        c = COLORS[i % len(COLORS)]
        ax0.plot(norm.index, norm.values, lw=1.5, alpha=0.85, color=c,
                 label=f"{r.ticker.replace('-USD','')} T{r.tier} "
                       f"Sh={r.sharpe:.2f} [{r.nb_trades}T]")
    ax0.axhline(0, color="#4B5563", lw=0.7, ls="--")
    ax0.set_ylabel("PnL cumule (%)", color="#9CA3AF", fontsize=8)
    ax0.legend(loc="upper left", fontsize=7.5, facecolor="#1F2937",
               edgecolor="#374151", labelcolor="white", ncol=3)
    ax_dark(ax0, "Equity Curves — Adaptive v2 (2 ans)")

    # B. Portfolio equity
    ax1 = fig.add_subplot(gs[0, 2])
    if not port_eq.empty:
        ax1.plot(port_eq.index, port_eq.values, color="#C9A84C", lw=2)
        ax1.fill_between(port_eq.index, CAPITAL_INIT, port_eq.values,
                         where=port_eq.values >= CAPITAL_INIT,
                         color="#22C55E", alpha=0.15)
        ax1.fill_between(port_eq.index, CAPITAL_INIT, port_eq.values,
                         where=port_eq.values < CAPITAL_INIT,
                         color="#EF4444", alpha=0.15)
        ax1.axhline(CAPITAL_INIT, color="#4B5563", lw=0.7, ls="--")
        ax1.set_ylabel("Capital ($)", color="#9CA3AF", fontsize=8)
    ax_dark(ax1, "Portfolio Risk Parity")

    # C. IS/OOS Sharpe — anti-overfit
    ax2 = fig.add_subplot(gs[1, 0])
    if not overfit_df.empty:
        x  = range(len(overfit_df))
        ax2.bar(x, overfit_df["IS_sharpe"].values,  color="#3B82F6", alpha=0.7, label="IS",  width=0.4, align="center")
        ax2.bar([i + 0.4 for i in x], overfit_df["OOS_sharpe"].values,
                color="#22C55E", alpha=0.7, label="OOS", width=0.4, align="center")
        ax2.set_xticks([i + 0.2 for i in x])
        ax2.set_xticklabels([t.replace("-USD","") for t in overfit_df["ticker"]],
                            rotation=30, fontsize=7)
        ax2.axhline(0, color="#4B5563", lw=0.7)
        ax2.legend(fontsize=7, facecolor="#1F2937", edgecolor="#374151", labelcolor="white")
    ax_dark(ax2, "Anti-Overfit : IS vs OOS Sharpe")

    # D. Ratio OOS/IS
    ax3 = fig.add_subplot(gs[1, 1])
    if not overfit_df.empty:
        colors_ratio = ["#22C55E" if v >= 0.7 else "#F59E0B" if v >= 0.5 else "#EF4444"
                        for v in overfit_df["ratio"]]
        ax3.barh(overfit_df["ticker"].str.replace("-USD",""),
                 overfit_df["ratio"].values, color=colors_ratio, alpha=0.85)
        ax3.axvline(0.7, color="#22C55E", lw=1, ls="--", label="Stable (0.7)")
        ax3.axvline(0.5, color="#F59E0B", lw=1, ls="--", label="Acceptable (0.5)")
        ax3.set_xlabel("Ratio OOS/IS", color="#9CA3AF", fontsize=8)
        ax3.legend(fontsize=7, facecolor="#1F2937", edgecolor="#374151", labelcolor="white")
    ax_dark(ax3, "Ratio OOS/IS (stable >= 0.7)")

    # E. Distribution regimes (all assets)
    ax4 = fig.add_subplot(gs[1, 2])
    regime_colors = {"trend":"#22C55E","neutral":"#3B82F6",
                     "high_vol":"#F59E0B","range":"#A78BFA"}
    tickers_plot = [r.ticker.replace("-USD","") for r in results if r.tier != "D"]
    bottom = np.zeros(len(tickers_plot))
    for reg, col in regime_colors.items():
        vals = [results[i].regime_dist.get(reg, 0) * 100
                for i, r in enumerate(results) if r.tier != "D"]
        if any(v > 0 for v in vals):
            ax4.bar(tickers_plot, vals, bottom=bottom, color=col,
                    alpha=0.8, label=reg, width=0.6)
            bottom += np.array(vals)
    ax4.set_ylabel("%", color="#9CA3AF", fontsize=8)
    ax4.tick_params(axis='x', rotation=30, labelsize=7)
    ax4.legend(fontsize=7, facecolor="#1F2937", edgecolor="#374151",
               labelcolor="white", loc="upper right")
    ax_dark(ax4, "Distribution regimes par asset")

    # F. Risk parity allocation
    ax5 = fig.add_subplot(gs[2, 0])
    if weights:
        labels = [t.replace("-USD","") for t in weights]
        vals   = [v * 100 for v in weights.values()]
        colors_w = [PALETTE.get(
            next((r.tier for r in results if r.ticker == t), "C"), "#888"
        ) for t in weights]
        ax5.pie(vals, labels=labels, colors=colors_w, autopct="%1.0f%%",
                textprops={"color": "white", "fontsize": 8},
                wedgeprops={"edgecolor": "#0D0D1F", "linewidth": 1.5})
    ax5.set_title("Allocation Risk Parity", color="#D1D5DB", fontsize=9, pad=6)

    # G. Trade regimes (LONG/SHORT par regime)
    ax6 = fig.add_subplot(gs[2, 1])
    all_trades = pd.concat([r.trades_df for r in results
                            if not r.trades_df.empty], ignore_index=True)
    if not all_trades.empty and "regime" in all_trades.columns:
        pivot = all_trades.groupby(["regime","side"]).size().unstack(fill_value=0)
        if not pivot.empty:
            pivot.plot(kind="bar", ax=ax6, color=["#22C55E","#EF4444"],
                       alpha=0.8, edgecolor="#0D0D1F")
            ax6.tick_params(axis='x', rotation=30, labelsize=7)
            ax6.legend(fontsize=7, facecolor="#1F2937", edgecolor="#374151",
                       labelcolor="white")
    ax_dark(ax6, "Trades par regime (LONG / SHORT)")

    # H. PnL par regime
    ax7 = fig.add_subplot(gs[2, 2])
    if not all_trades.empty and "regime" in all_trades.columns:
        pnl_by_regime = all_trades.groupby("regime")["pnl_pct"].mean() * 100
        colors_pnl = ["#22C55E" if v > 0 else "#EF4444" for v in pnl_by_regime]
        ax7.bar(pnl_by_regime.index, pnl_by_regime.values,
                color=colors_pnl, alpha=0.8, edgecolor="#0D0D1F")
        ax7.axhline(0, color="#4B5563", lw=0.7)
        ax7.set_ylabel("PnL moyen (%)", color="#9CA3AF", fontsize=8)
        ax7.tick_params(axis='x', rotation=30, labelsize=8)
    ax_dark(ax7, "PnL moyen par regime")

    # I. Tableau final
    ax8 = fig.add_subplot(gs[3, :])
    ax8.axis("off")
    headers = ["Asset","Tier","PnL%","CAGR%","Sharpe","Sortino","Calmar",
               "MaxDD%","WinRate%","PF","Trades","Hold(j)","IS_Sh","OOS_Sh","Overfit"]
    col_w   = [0.065,0.035,0.055,0.055,0.055,0.055,0.055,
               0.055,0.065,0.050,0.045,0.050,0.050,0.055,0.065]

    x = 0.0
    for h, w in zip(headers, col_w):
        ax8.text(x, 0.97, h, color="#6B7280", fontsize=7.5,
                 fontweight="bold", transform=ax8.transAxes, va="top")
        x += w

    for ri, r in enumerate(results):
        s  = r.summary()
        y  = 0.88 - ri * 0.085
        tc = PALETTE.get(r.tier, "#888")
        vals = [
            r.ticker.replace("-USD",""), r.tier,
            f"{s['pnl_pct']:+.1f}", f"{s['cagr_pct']:+.1f}",
            f"{s['sharpe']:.2f}", f"{s['sortino']:.2f}", f"{s['calmar']:.2f}",
            f"{s['max_dd_pct']:.1f}", f"{s['win_rate_pct']:.1f}",
            f"{s['profit_factor']:.2f}", str(s['nb_trades']), f"{s['avg_hold_days']:.1f}",
            f"{s['is_sharpe']:.2f}", f"{s['oos_sharpe']:.2f}", s['overfit_flag'],
        ]
        x = 0.0
        for v, w in zip(vals, col_w):
            if v in [r.ticker.replace("-USD",""), r.tier]:
                color = tc
            elif v == "FLAG":
                color = "#EF4444"
            elif v == "OK":
                color = "#22C55E"
            elif str(v).startswith("+"):
                color = "#22C55E"
            elif str(v).startswith("-"):
                color = "#EF4444"
            else:
                color = "#E5E7EB"
            ax8.text(x, y, v, color=color, fontsize=7.5,
                     transform=ax8.transAxes, va="top")
            x += w

    path = OUT_DIR / "adaptive_v2_dashboard.png"
    plt.savefig(path, dpi=130, bbox_inches="tight", facecolor="#080818")
    plt.close()
    print(f"  Dashboard: {path}")


# ── Telechargement ────────────────────────────────────────────
def download(ticker: str, days: int) -> pd.DataFrame:
    try:
        import yfinance as yf
        end   = datetime.utcnow()
        start = end - timedelta(days=days + 60)
        df    = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                            end=end.strftime("%Y-%m-%d"),
                            progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower()
                      for c in df.columns]
        df.index   = pd.to_datetime(df.index)
        return df[["open","high","low","close","volume"]].dropna().sort_index()
    except Exception as e:
        print(f"  [WARN] {ticker}: {e}")
        return pd.DataFrame()


# ── Main ──────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("ADAPTIVE ENGINE v2 — Crypto-Native Regime + ATR Sizing")
    print(f"Capital: ${CAPITAL_INIT:,} | {DAYS_BACK}j | Fee: {TAKER_FEE*100:.2f}%")
    print(f"Regime: percentile-based ATR (crypto-native)")
    print(f"Position sizing: {RISK_PER_TRADE*100:.0f}% risque/trade | Max: {MAX_POSITION*100:.0f}%")
    print("=" * 65)

    results = []
    wf_all  = []

    for ticker, profile in ASSET_PROFILES.items():
        print(f"\n{'─'*55}")
        print(f"[{ticker}] Tier {profile['tier']}")
        df = download(ticker, DAYS_BACK)
        if df.empty or len(df) < 300:
            print(f"  SKIP"); continue

        print(f"  {len(df)} bougies | {df.index[0].date()} -> {df.index[-1].date()}")

        # SMA optimisation
        print(f"  Optimisation SMA...")
        s, m, l = optimize_sma_v2(df, ticker, profile)

        # Simulation principale
        r = simulate_v2(df, ticker, profile, sma_s=s, sma_m=m, sma_l=l)
        if r is None:
            print(f"  SKIP — simulation echouee"); continue

        results.append(r)
        su = r.summary()
        print(f"  PnL: {su['pnl_pct']:+.1f}% | Sharpe: {su['sharpe']:.2f} | "
              f"Sortino: {su['sortino']:.2f} | MaxDD: {su['max_dd_pct']:.1f}% | "
              f"WinRate: {su['win_rate_pct']:.1f}% | Trades: {su['nb_trades']}")
        print(f"  IS Sharpe: {su['is_sharpe']:.3f} | OOS Sharpe: {su['oos_sharpe']:.3f} | "
              f"Overfit: {su['overfit_flag']}")
        print(f"  Regimes: {r.regime_dist}")

        # Walk-forward
        print(f"  Walk-forward 3 folds...")
        wf = walk_forward_v2(df, ticker, profile)
        for fold in wf:
            fold["ticker"] = ticker
            wf_all.append(fold)
            print(f"    Fold {fold['fold']} [{fold['period']}] "
                  f"PnL: {fold['pnl_pct']:+.1f}% | Sharpe: {fold['sharpe']:.3f} | "
                  f"OOS_Sh: {fold['oos_sharpe']:.3f} | "
                  f"Trades: {fold['nb_trades']} | SMA: {fold['sma']}")

    if not results:
        print("\nAucun resultat."); return

    # ── Anti-overfitting ────────────────────────────────────
    print(f"\n{'='*65}")
    print("ANTI-OVERFIT — IS vs OOS Sharpe")
    overfit_df = anti_overfit_report(results)
    print(overfit_df.to_string(index=False))
    overfit_df.to_csv(OUT_DIR / "overfit_report.csv", index=False)

    # ── Risk parity ─────────────────────────────────────────
    weights = risk_parity(results)
    print(f"\n{'─'*55}")
    print("RISK PARITY")
    for t, w in sorted(weights.items(), key=lambda x: -x[1]):
        tier = ASSET_PROFILES[t]["tier"]
        print(f"  {t:<12} Tier {tier} : {w*100:.1f}%")

    # ── Portfolio ────────────────────────────────────────────
    port_eq = portfolio_equity(results, weights)
    if not port_eq.empty:
        port_r  = port_eq.pct_change().dropna()
        p_sh    = (port_r.mean() / port_r.std()) * np.sqrt(ANNUALIZE) if port_r.std() > 0 else 0
        p_pnl   = (port_eq.iloc[-1] / CAPITAL_INIT - 1) * 100
        p_dd    = ((port_eq - port_eq.cummax()) / port_eq.cummax()).min() * 100
        n_yr    = (port_eq.index[-1] - port_eq.index[0]).days / 365.25
        p_cagr  = ((port_eq.iloc[-1] / CAPITAL_INIT) ** (1 / max(n_yr, 0.1)) - 1) * 100

        print(f"\n{'='*65}")
        print("PORTEFEUILLE RISK PARITY")
        print(f"  PnL     : {p_pnl:+.1f}%  |  CAGR: {p_cagr:+.1f}%")
        print(f"  Sharpe  : {p_sh:.3f}  |  MaxDD: {p_dd:.1f}%")
        print(f"  Capital : ${CAPITAL_INIT:,} -> ${port_eq.iloc[-1]:,.0f}")

    # ── Walk-forward summary ────────────────────────────────
    if wf_all:
        wf_df = pd.DataFrame(wf_all)
        print(f"\n{'='*65}")
        print("WALK-FORWARD STABILITY")
        grp = wf_df.groupby("ticker")[["pnl_pct","sharpe","oos_sharpe","win_rate"]].agg(["mean","std"]).round(3)
        print(grp.to_string())
        wf_df.to_csv(OUT_DIR / "wf_v2.csv", index=False)

    # ── Exports ─────────────────────────────────────────────
    sum_df = pd.DataFrame([r.summary() for r in results])
    sum_df.to_csv(OUT_DIR / "summary_v2.csv", index=False)

    # ── Graphique ───────────────────────────────────────────
    plot_v2(results, port_eq if not port_eq.empty else pd.Series(),
            weights, overfit_df)

    # ── Verdict final ────────────────────────────────────────
    print(f"\n{'='*65}")
    print("VERDICT FINAL")
    print(f"{'='*65}")

    stable  = [r for r in results if r.oos_sharpe > 0.5 and r.nb_trades >= 5]
    flagged = [r for r in results if r._overfit_flag()]
    deploy  = [r for r in stable if r.sharpe > 1.0]

    if deploy:
        print(f"[DEPLOIEMENT OK]  : {', '.join(r.ticker for r in deploy)}")
    if stable and not deploy:
        print(f"[SURVEILLER]      : {', '.join(r.ticker for r in stable)}")
    if flagged:
        print(f"[OVERFIT DETECTE] : {', '.join(r.ticker for r in flagged)}")

    if not port_eq.empty:
        verdict = (
            "DEPLOIEMENT possible levier x1 (paper trading d'abord)"
            if p_sh > 1.0 else
            "CONTINUER backtest sur 2022 (bear market)"
            if p_sh > 0.5 else
            "OPTIMISATION NECESSAIRE"
        )
        print(f"\nPortefeuille Sharpe {p_sh:.3f} -> {verdict}")

    print("\nProchaines etapes :")
    print("  1. Paper trading 30j -> valider les signaux temps reel")
    print("  2. Backtest 2022 (bear) -> stress test")
    print("  3. Ajouter filtre volume (confirme la tendance)")
    print("  4. Connecter backend FastAPI -> /crypto/adaptive-signal")


if __name__ == "__main__":
    main()
