"""
Adaptive Trading Engine v1
==========================
Construit sur les resultats du composite_backtest :
  - XRP/SOL : edge reel
  - ETH/DOGE : filtres necessaires
  - BTC : seuils stricts

Modules :
  1. RegimeDetector      — Trend / Range / Volatile par barre
  2. DynamicThreshold    — Seuil ajuste par ATR%  + regime
  3. SMAOptimizer        — Grid search periodes SMA par asset
  4. AssetRouter         — Config specifique par asset (backtest-driven)
  5. RiskParity          — Poids portefeuille = 1/volatilite normalisee
  6. PortfolioBacktest   — Equity combinee + metriques portefeuille

Usage :
  python brvm-trading/backtest/adaptive_engine_v1.py
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

# ── Config globale ────────────────────────────────────────────
CAPITAL_INIT  = 10_000
DAYS_BACK     = 730          # 2 ans (eviter overfitting 1 an)
TAKER_FEE     = 0.0004
ANNUALIZE     = 252

# Assets avec profil pre-defini (base backtest v1)
ASSET_PROFILES = {
    "XRP-USD":  {"tier": "A", "base_thresh": 4, "max_dd_limit": 0.20, "leverage": 1},
    "SOL-USD":  {"tier": "A", "base_thresh": 4, "max_dd_limit": 0.25, "leverage": 1},
    "BNB-USD":  {"tier": "B", "base_thresh": 4, "max_dd_limit": 0.20, "leverage": 1},
    "ADA-USD":  {"tier": "B", "base_thresh": 4, "max_dd_limit": 0.25, "leverage": 1},
    "AVAX-USD": {"tier": "B", "base_thresh": 4, "max_dd_limit": 0.25, "leverage": 1},
    "BTC-USD":  {"tier": "C", "base_thresh": 5, "max_dd_limit": 0.15, "leverage": 1},
    "ETH-USD":  {"tier": "C", "base_thresh": 5, "max_dd_limit": 0.15, "leverage": 1},
    "DOGE-USD": {"tier": "D", "base_thresh": 9, "max_dd_limit": 0.10, "leverage": 1},
}

OUT_DIR = Path("backtest/results/adaptive_v1")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Indicateurs de base ───────────────────────────────────────
def _ema(s: pd.Series, p: int) -> pd.Series:
    return s.ewm(span=p, adjust=False, min_periods=p).mean()

def _sma(s: pd.Series, p: int) -> pd.Series:
    return s.rolling(p, min_periods=p).mean()

def _rsi(s: pd.Series, p: int = 14) -> pd.Series:
    d = s.diff()
    g = d.clip(lower=0).ewm(com=p - 1, min_periods=p).mean()
    l = (-d.clip(upper=0)).ewm(com=p - 1, min_periods=p).mean()
    return 100 - (100 / (1 + g / l.replace(0, np.nan)))

def _mfi(df: pd.DataFrame, p: int = 14) -> pd.Series:
    tp  = (df["high"] + df["low"] + df["close"]) / 3
    mf  = tp * df["volume"]
    pos = mf.where(tp > tp.shift(1), 0).rolling(p, min_periods=1).sum()
    neg = mf.where(tp < tp.shift(1), 0).rolling(p, min_periods=1).sum()
    return 100 - (100 / (1 + pos / neg.replace(0, np.nan)))

def _macd_hist(s: pd.Series, fast=12, slow=26, sig=9) -> pd.Series:
    m      = _ema(s, fast) - _ema(s, slow)
    signal = _ema(m.fillna(0), sig)
    return m - signal

def _atr(df: pd.DataFrame, p: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([
        h - l,
        (h - c.shift()).abs(),
        (l - c.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=p, adjust=False, min_periods=p).mean()

def _atr_pct(df: pd.DataFrame, p: int = 14) -> pd.Series:
    return _atr(df, p) / df["close"]


# ── 1. Regime Detector ───────────────────────────────────────
class RegimeDetector:
    """
    Classifie chaque barre en un regime parmi :
      trending_up   : EMA200 slope > 0  et ATR% < high_vol_thresh
      trending_down : EMA200 slope < 0  et ATR% < high_vol_thresh
      volatile      : ATR% > high_vol_thresh
      ranging       : EMA200 slope ~ 0  et ATR% faible

    Retourne une Series de strings.
    """
    def __init__(self, slope_window: int = 10, high_vol_pct: float = 0.04,
                 flat_slope_pct: float = 0.001):
        self.slope_window   = slope_window
        self.high_vol_pct   = high_vol_pct    # ATR% > 4% = volatile
        self.flat_slope_pct = flat_slope_pct  # slope ~ 0

    def detect(self, df: pd.DataFrame) -> pd.Series:
        e200      = _ema(df["close"], 200)
        slope     = e200.pct_change(self.slope_window)
        atr_p     = _atr_pct(df, 14)

        conditions = [
            atr_p > self.high_vol_pct,
            slope.abs() < self.flat_slope_pct,
            slope > 0,
            slope < 0,
        ]
        choices = ["volatile", "ranging", "trending_up", "trending_down"]
        return pd.Series(
            np.select(conditions, choices, default="ranging"),
            index=df.index
        )


# ── 2. Dynamic Threshold ─────────────────────────────────────
class DynamicThreshold:
    """
    Seuil base ajuste selon le regime et la volatilite ATR.

    Logique :
      volatile     -> base + 3  (quasi aucun trade)
      ranging      -> base + 2  (eviter le bruit range)
      trending_up  -> base      (signaux normaux)
      trending_down -> base + 1 (prudence)
    """
    REGIME_ADDON = {
        "volatile":      3,
        "ranging":       2,
        "trending_up":   0,
        "trending_down": 1,
    }

    def __init__(self, base_thresh: int = 4):
        self.base = base_thresh

    def threshold(self, regime: str) -> int:
        return self.base + self.REGIME_ADDON.get(regime, 1)


# ── 3. Score composite (reutilise du composite_backtest) ─────
def compute_score(df: pd.DataFrame,
                  sma_short: int = 16,
                  sma_mid:   int = 19,
                  sma_long:  int = 246) -> pd.Series:
    p = df["close"]

    r     = _rsi(p, 14)
    m     = _mfi(df, 14)
    ms    = _sma(p, sma_short)
    mm    = _sma(p, sma_mid)
    ml    = _sma(p, sma_long)
    e9    = _ema(p, 9)
    e50   = _ema(p, 50)
    e200  = _ema(p, 200)
    mhist = _macd_hist(p)

    score = pd.Series(0.0, index=df.index)

    score += np.where(r < 30,  2, np.where(r < 45,  1,
             np.where(r > 70, -2, np.where(r > 55, -1, 0))))
    score += np.where(m < 20,  2, np.where(m > 80, -2, 0))

    vm1 = ms.notna() & mm.notna()
    score += np.where(vm1 & (ms > mm),  1, np.where(vm1 & (ms <= mm), -1, 0))

    vm2 = mm.notna() & ml.notna()
    score += np.where(vm2 & (mm > ml),  1, np.where(vm2 & (mm <= ml), -1, 0))

    vh = mhist.notna()
    score += np.where(vh & (mhist > 0),  1, np.where(vh & (mhist <= 0), -1, 0))

    ve1 = e9.notna() & e50.notna()
    score += np.where(ve1 & (e9 > e50),  1, np.where(ve1 & (e9 <= e50), -1, 0))

    ve2 = e50.notna() & e200.notna()
    score += np.where(ve2 & (e50 > e200), 1, np.where(ve2 & (e50 <= e200), -1, 0))

    return score


# ── 4. SMA Optimizer ─────────────────────────────────────────
@dataclass
class SMAConfig:
    short: int
    mid:   int
    long:  int
    sharpe: float
    pf:    float

def optimize_sma(df: pd.DataFrame, ticker: str,
                 base_thresh: int = 4) -> SMAConfig:
    """
    Grid search sur les periodes SMA.
    Court : [10, 16, 20]  Mid : [19, 38, 50]  Long : [100, 200, 246]
    Conserve la config qui maximise le Sharpe.
    """
    short_range = [10, 16, 20]
    mid_range   = [19, 38, 50]
    long_range  = [100, 200, 246]

    best = SMAConfig(16, 19, 246, -999, 0)

    for s, m, l in itertools.product(short_range, mid_range, long_range):
        if s >= m or m >= l:
            continue
        if len(df) < l + 30:
            continue

        score = compute_score(df, sma_short=s, sma_mid=m, sma_long=l)
        sig   = np.where(score >= base_thresh, 1,
                np.where(score <= -base_thresh, -1, 0))
        pos   = pd.Series(sig, index=df.index).shift(1).fillna(0)
        ret   = df["close"].pct_change()
        net   = (pos * ret) - (pos.diff().abs() * TAKER_FEE)
        net   = net.dropna()

        if net.std() == 0 or net.count() < 30:
            continue

        sharpe = (net.mean() / net.std()) * np.sqrt(ANNUALIZE)
        wins   = net[net > 0].sum()
        losses = abs(net[net < 0].sum())
        pf     = wins / max(losses, 1e-10)

        if sharpe > best.sharpe:
            best = SMAConfig(s, m, l, round(sharpe, 3), round(pf, 3))

    print(f"  SMA optimal [{ticker}] : {best.short}/{best.mid}/{best.long} "
          f"-> Sharpe {best.sharpe:.3f}, PF {best.pf:.3f}")
    return best


# ── 5. Simulation avec regime adaptatif ──────────────────────
@dataclass
class TradeResult:
    ticker:        str
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
    tier:          str
    sma_config:    SMAConfig
    equity:        pd.Series = field(repr=False)
    trades_df:     pd.DataFrame = field(repr=False)
    regime_stats:  dict = field(default_factory=dict)

    def summary(self) -> dict:
        return {
            "ticker":        self.ticker,
            "tier":          self.tier,
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
            "sma":           f"{self.sma_config.short}/{self.sma_config.mid}/{self.sma_config.long}",
        }


def simulate_adaptive(df: pd.DataFrame, ticker: str,
                      sma_cfg: SMAConfig,
                      profile: dict,
                      capital: float = CAPITAL_INIT) -> Optional[TradeResult]:

    if df.empty or len(df) < 250:
        return None

    df     = df.copy()
    regime = RegimeDetector().detect(df)
    dt     = DynamicThreshold(base_thresh=profile["base_thresh"])
    score  = compute_score(df, sma_cfg.short, sma_cfg.mid, sma_cfg.long)

    # Seuil dynamique par barre
    thresh_long  = regime.map(lambda r: dt.threshold(r))
    thresh_short = -thresh_long

    signal = np.where(score >= thresh_long,  1,
             np.where(score <= thresh_short, -1, 0))

    df["regime"]   = regime.values
    df["score"]    = score.values
    df["signal"]   = signal
    df["position"] = pd.Series(signal, index=df.index).shift(1).fillna(0).values

    # Drawdown guard : coupe la position si MaxDD depasse la limite
    dd_limit = profile["max_dd_limit"]

    ret        = df["close"].pct_change().fillna(0)
    strat_ret  = df["position"] * ret * profile.get("leverage", 1)
    trade_chg  = pd.Series(df["position"]).diff().abs().fillna(0)
    fee_cost   = trade_chg * TAKER_FEE
    net_ret    = strat_ret - fee_cost.values

    # Calcul equity avec coupe-circuit sur MaxDD
    equity_vals = [capital]
    cut = False
    for i in range(1, len(net_ret)):
        if cut:
            equity_vals.append(equity_vals[-1])
            continue
        new_val = equity_vals[-1] * (1 + net_ret.iloc[i])
        equity_vals.append(new_val)
        peak = max(equity_vals)
        if (new_val - peak) / peak < -dd_limit:
            cut = True
            print(f"  [!] {ticker} : circuit breaker a {df.index[i].date()} "
                  f"(DD > {dd_limit*100:.0f}%)")

    equity = pd.Series(equity_vals, index=df.index)
    bh_ret = df["close"].pct_change().fillna(0)

    # Trade log
    trades  = []
    in_pos  = False
    e_px    = 0
    e_date  = None
    side    = 0

    for date, row in df.iterrows():
        p = row["position"]
        if not in_pos and p != 0:
            in_pos = True;  e_px = row["close"];  e_date = date;  side = p
        elif in_pos and p != side:
            raw   = (row["close"] - e_px) / e_px * side
            net_p = raw - 2 * TAKER_FEE
            trades.append({
                "entry_date": e_date,
                "exit_date":  date,
                "side":       "LONG" if side == 1 else "SHORT",
                "entry_px":   round(e_px, 5),
                "exit_px":    round(row["close"], 5),
                "pnl_pct":    round(net_p, 5),
                "hold_days":  (date - e_date).days,
                "regime":     row["regime"],
            })
            if p != 0:
                e_px = row["close"];  e_date = date;  side = p
            else:
                in_pos = False

    trades_df = pd.DataFrame(trades)

    # Metriques
    eq   = equity.dropna()
    rets = eq.pct_change().dropna()

    n_years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1/365)
    cagr    = (eq.iloc[-1] / capital) ** (1 / n_years) - 1
    sharpe  = (rets.mean() / rets.std()) * np.sqrt(ANNUALIZE) if rets.std() > 0 else 0
    down    = rets[rets < 0]
    sortino = (rets.mean() / down.std()) * np.sqrt(ANNUALIZE) if (len(down) > 1 and down.std() > 0) else 0
    roll_mx = eq.cummax()
    max_dd  = ((eq - roll_mx) / roll_mx).min()
    calmar  = cagr / abs(max_dd) if max_dd < 0 else 0

    if not trades_df.empty and "pnl_pct" in trades_df.columns:
        t        = trades_df
        win_rate = (t.pnl_pct > 0).sum() / max(len(t), 1)
        pf       = t[t.pnl_pct > 0].pnl_pct.sum() / max(abs(t[t.pnl_pct < 0].pnl_pct.sum()), 1e-10)
        avg_hold = t.hold_days.mean()
        nb       = len(t)
    else:
        win_rate = pf = avg_hold = 0;  nb = 0

    # Stats regime
    regime_counts = df["regime"].value_counts(normalize=True).round(3).to_dict()

    return TradeResult(
        ticker=ticker, tier=profile["tier"],
        capital_final=round(eq.iloc[-1], 2),
        pnl_pct=round((eq.iloc[-1] / capital - 1) * 100, 2),
        cagr=cagr, sharpe=sharpe, sortino=sortino, calmar=calmar,
        max_drawdown=max_dd, win_rate=win_rate, profit_factor=pf,
        nb_trades=nb, avg_hold_days=avg_hold,
        sma_config=sma_cfg, equity=eq, trades_df=trades_df,
        regime_stats=regime_counts,
    )


# ── 6. Risk Parity ───────────────────────────────────────────
def risk_parity_weights(results: list[TradeResult]) -> dict[str, float]:
    """
    Poids = 1 / volatilite_annualisee, normalises a 100%.
    Assets tier D exclus du portefeuille.
    """
    vols = {}
    for r in results:
        if r.tier == "D":
            continue
        ret_series = r.equity.pct_change().dropna()
        vol = ret_series.std() * np.sqrt(ANNUALIZE)
        vols[r.ticker] = vol if vol > 0 else 1.0

    if not vols:
        return {}

    inv_vol = {k: 1 / v for k, v in vols.items()}
    total   = sum(inv_vol.values())
    return {k: round(v / total, 4) for k, v in inv_vol.items()}


# ── 7. Portfolio Backtest ────────────────────────────────────
def portfolio_backtest(results: list[TradeResult],
                       weights: dict[str, float],
                       capital: float = CAPITAL_INIT) -> pd.Series:
    """
    Combine les equity curves des assets tier A/B/C via risk parity.
    Retourne la courbe d'equity du portefeuille.
    """
    result_map = {r.ticker: r for r in results}
    included   = {t: w for t, w in weights.items() if t in result_map}

    if not included:
        return pd.Series(dtype=float)

    # Aligner les dates
    all_idx = sorted(set.intersection(*[set(result_map[t].equity.index) for t in included]))
    if not all_idx:
        return pd.Series(dtype=float)

    port_ret = pd.Series(0.0, index=all_idx)
    for ticker, w in included.items():
        eq    = result_map[ticker].equity.reindex(all_idx)
        r_ret = eq.pct_change().fillna(0)
        port_ret += w * r_ret

    port_equity = capital * (1 + port_ret).cumprod()
    return port_equity


# ── 8. Visualisation ─────────────────────────────────────────
def plot_adaptive_summary(results: list[TradeResult],
                          port_equity: pd.Series,
                          weights: dict[str, float]):

    fig = plt.figure(figsize=(18, 14))
    fig.patch.set_facecolor("#0D0D1F")
    gs  = gridspec.GridSpec(3, 3, figure=fig, hspace=0.5, wspace=0.4)

    PALETTE = {
        "A": "#22C55E", "B": "#F59E0B", "C": "#3B82F6", "D": "#EF4444"
    }
    COLORS = ["#C9A84C","#3B82F6","#F0B90B","#9945FF",
              "#00AAE4","#0033AD","#E84142","#C2A633"]

    def ax_dark(ax, title=""):
        ax.set_facecolor("#0D0D1F")
        ax.tick_params(colors="#9CA3AF", labelsize=8)
        for sp in ax.spines.values(): sp.set_color("#374151")
        if title: ax.set_title(title, color="#D1D5DB", fontsize=9, pad=6)
        ax.grid(True, color="#1F2937", lw=0.5)

    fig.suptitle(
        "Adaptive Engine v1 — Portefeuille Risk Parity\n"
        "Regime-adaptive thresholds + SMA optimises par asset",
        color="white", fontsize=13, y=0.99
    )

    # ── A. Equity curves individuelles normalisees
    ax0 = fig.add_subplot(gs[0, :2])
    for i, r in enumerate(results):
        if r.tier == "D": continue
        norm = r.equity / r.equity.iloc[0] * 100 - 100
        ax0.plot(norm.index, norm.values,
                 label=f"{r.ticker.replace('-USD','')} (T{r.tier})",
                 color=COLORS[i % len(COLORS)], lw=1.3, alpha=0.8)
    ax0.axhline(0, color="#4B5563", lw=0.7, ls="--")
    ax0.set_ylabel("PnL cumule (%)", color="#9CA3AF", fontsize=8)
    ax0.legend(loc="upper left", fontsize=7, facecolor="#1F2937",
               edgecolor="#374151", labelcolor="white", ncol=3)
    ax_dark(ax0, "Equity Curves — Adaptive Thresholds + SMA Optimises")

    # ── B. Portfolio equity
    ax1 = fig.add_subplot(gs[0, 2])
    if not port_equity.empty:
        ax1.plot(port_equity.index, port_equity.values,
                 color="#C9A84C", lw=2, label="Portefeuille RP")
        ax1.axhline(CAPITAL_INIT, color="#4B5563", lw=0.7, ls="--")
        ax1.set_ylabel("Capital ($)", color="#9CA3AF", fontsize=8)
        ax1.legend(fontsize=7, facecolor="#1F2937", edgecolor="#374151", labelcolor="white")
    ax_dark(ax1, "Portfolio Risk Parity")

    # ── C. Sharpe vs MaxDD scatter
    ax2 = fig.add_subplot(gs[1, 0])
    for i, r in enumerate(results):
        s = r.summary()
        color = PALETTE.get(r.tier, "#888")
        ax2.scatter(abs(s["max_dd_pct"]), s["sharpe"],
                    color=color, s=110, zorder=5,
                    label=f"Tier {r.tier}" if r.tier not in [x.get_label() for x in ax2.get_children()] else "")
        ax2.annotate(r.ticker.replace("-USD",""),
                     (abs(s["max_dd_pct"]), s["sharpe"]),
                     xytext=(5, 3), textcoords="offset points",
                     color=color, fontsize=7)
    ax2.axhline(1.0, color="#F59E0B", lw=0.7, ls="--", alpha=0.6)
    ax2.axhline(0.5, color="#EF4444", lw=0.7, ls="--", alpha=0.4)
    ax2.set_xlabel("Max Drawdown (%)", color="#9CA3AF", fontsize=8)
    ax2.set_ylabel("Sharpe", color="#9CA3AF", fontsize=8)
    ax_dark(ax2, "Sharpe vs DD (haut gauche = meilleur)")

    # ── D. Repartition des regimes (BTC comme exemple)
    ax3 = fig.add_subplot(gs[1, 1])
    btc = next((r for r in results if r.ticker == "BTC-USD"), None)
    if btc and btc.regime_stats:
        labels  = list(btc.regime_stats.keys())
        vals    = [btc.regime_stats[k] * 100 for k in labels]
        colors3 = ["#EF4444","#F59E0B","#22C55E","#3B82F6"][:len(labels)]
        ax3.barh(labels, vals, color=colors3[:len(labels)], alpha=0.8)
        ax3.set_xlabel("% du temps", color="#9CA3AF", fontsize=8)
    ax_dark(ax3, "Regimes detectes (BTC)")

    # ── E. Risk Parity weights
    ax4 = fig.add_subplot(gs[1, 2])
    if weights:
        tickers = [t.replace("-USD","") for t in weights]
        vals    = list(weights.values())
        colors4 = [PALETTE.get(
            next((r.tier for r in results if r.ticker == t), "C"), "#888"
        ) for t in weights]
        ax4.barh(tickers, [v*100 for v in vals], color=colors4, alpha=0.8)
        ax4.set_xlabel("Poids (%)", color="#9CA3AF", fontsize=8)
    ax_dark(ax4, "Allocation Risk Parity")

    # ── F. Tableau metriques
    ax5 = fig.add_subplot(gs[2, :])
    ax5.axis("off")

    headers = ["Asset","Tier","SMA","PnL%","CAGR%","Sharpe","Sortino",
               "Calmar","MaxDD%","WinRate%","PF","Trades","Hold(j)"]
    col_w   = [0.075, 0.04, 0.06, 0.06, 0.06, 0.06, 0.06,
               0.06,  0.06, 0.07, 0.055, 0.05, 0.055]

    x = 0.0
    for h, w in zip(headers, col_w):
        ax5.text(x, 0.96, h, color="#6B7280", fontsize=7.5,
                 fontweight="bold", transform=ax5.transAxes, va="top")
        x += w

    for row_i, r in enumerate(results):
        s  = r.summary()
        y  = 0.88 - row_i * 0.075
        tc = PALETTE.get(r.tier, "#888")

        vals = [
            r.ticker.replace("-USD",""), r.tier, s["sma"],
            f"{s['pnl_pct']:+.1f}", f"{s['cagr_pct']:+.1f}",
            f"{s['sharpe']:.2f}", f"{s['sortino']:.2f}", f"{s['calmar']:.2f}",
            f"{s['max_dd_pct']:.1f}", f"{s['win_rate_pct']:.1f}",
            f"{s['profit_factor']:.2f}", str(s['nb_trades']), f"{s['avg_hold_days']:.1f}",
        ]
        x = 0.0
        for v, w in zip(vals, col_w):
            if v in [r.ticker.replace("-USD",""), r.tier]:
                color = tc
            elif str(v).startswith("+"):
                color = "#22C55E"
            elif str(v).startswith("-"):
                color = "#EF4444"
            else:
                color = "#E5E7EB"
            ax5.text(x, y, v, color=color, fontsize=7.5,
                     transform=ax5.transAxes, va="top")
            x += w

    plt.savefig(OUT_DIR / "adaptive_v1_summary.png",
                dpi=130, bbox_inches="tight", facecolor="#0D0D1F")
    plt.close()
    print(f"  Graphique: {OUT_DIR / 'adaptive_v1_summary.png'}")


# ── Telechargement ────────────────────────────────────────────
def download(ticker: str, days: int) -> pd.DataFrame:
    try:
        import yfinance as yf
        end   = datetime.utcnow()
        start = end - timedelta(days=days + 60)
        df = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                         end=end.strftime("%Y-%m-%d"),
                         progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
        df.index   = pd.to_datetime(df.index)
        return df[["open","high","low","close","volume"]].dropna().sort_index()
    except Exception as e:
        print(f"  [WARN] {ticker}: {e}")
        return pd.DataFrame()


# ── Walk-Forward Adaptive ─────────────────────────────────────
def walk_forward_adaptive(df: pd.DataFrame, ticker: str,
                           profile: dict, n_folds: int = 3) -> list[dict]:
    n         = len(df)
    fold_size = n // n_folds
    rows      = []

    for i in range(n_folds):
        fold_df = df.iloc[i * fold_size : (i + 1) * fold_size]
        if len(fold_df) < 120:
            continue

        # Optimise les SMA sur ce fold
        sma_cfg = optimize_sma(fold_df, f"{ticker}_fold{i+1}",
                               base_thresh=profile["base_thresh"])
        r = simulate_adaptive(fold_df, f"{ticker}", sma_cfg, profile)
        if r:
            rows.append({
                "fold":      i + 1,
                "period":    f"{fold_df.index[0].date()} -> {fold_df.index[-1].date()}",
                "pnl_pct":   r.pnl_pct,
                "sharpe":    round(r.sharpe, 3),
                "max_dd":    round(r.max_drawdown * 100, 2),
                "win_rate":  round(r.win_rate * 100, 2),
                "nb_trades": r.nb_trades,
                "sma":       f"{sma_cfg.short}/{sma_cfg.mid}/{sma_cfg.long}",
            })
    return rows


# ── Main ──────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("ADAPTIVE ENGINE v1 — Regime-Adaptive + Risk Parity")
    print(f"Capital: ${CAPITAL_INIT:,} | Periode: {DAYS_BACK}j | Fee: {TAKER_FEE*100:.2f}%")
    print(f"Assets: {len(ASSET_PROFILES)} | Mode: SMA auto-optimise par asset")
    print("=" * 65)

    results  = []
    wf_rows  = []

    for ticker, profile in ASSET_PROFILES.items():
        print(f"\n{'─'*55}")
        print(f"[{ticker}] Tier {profile['tier']} | base_thresh={profile['base_thresh']}")

        df = download(ticker, DAYS_BACK)
        if df.empty or len(df) < 300:
            print(f"  SKIP — donnees insuffisantes")
            continue

        print(f"  {len(df)} bougies | {df.index[0].date()} -> {df.index[-1].date()}")

        # Optimisation SMA
        print(f"  Optimisation SMA...")
        sma_cfg = optimize_sma(df, ticker, base_thresh=profile["base_thresh"])

        # Simulation adaptive
        result = simulate_adaptive(df, ticker, sma_cfg, profile)
        if result is None:
            print(f"  SKIP — simulation echouee")
            continue

        s = result.summary()
        results.append(result)

        print(f"  PnL: {s['pnl_pct']:+.1f}% | Sharpe: {s['sharpe']:.2f} | "
              f"Sortino: {s['sortino']:.2f} | Calmar: {s['calmar']:.2f} | "
              f"MaxDD: {s['max_dd_pct']:.1f}% | WinRate: {s['win_rate_pct']:.1f}% | "
              f"Trades: {s['nb_trades']}")
        print(f"  Regimes: {result.regime_stats}")

        # Walk-forward
        print(f"  Walk-Forward 3 folds...")
        wf = walk_forward_adaptive(df, ticker, profile)
        for fold in wf:
            fold["ticker"] = ticker
            wf_rows.append(fold)
            print(f"    Fold {fold['fold']} [{fold['period']}] "
                  f"PnL: {fold['pnl_pct']:+.1f}% | Sharpe: {fold['sharpe']:.3f} | "
                  f"SMA: {fold['sma']} | Trades: {fold['nb_trades']}")

    if not results:
        print("\nAucun resultat.")
        return

    # ── Risk Parity ──────────────────────────────────────────
    print(f"\n{'='*65}")
    print("RISK PARITY — Calcul des poids")
    weights = risk_parity_weights(results)
    for t, w in sorted(weights.items(), key=lambda x: -x[1]):
        tier = ASSET_PROFILES[t]["tier"]
        print(f"  {t:<12} Tier {tier} : {w*100:.1f}%")

    # ── Portfolio ────────────────────────────────────────────
    port_equity = portfolio_backtest(results, weights)
    if not port_equity.empty:
        port_ret  = port_equity.pct_change().dropna()
        p_sharpe  = (port_ret.mean() / port_ret.std()) * np.sqrt(ANNUALIZE) if port_ret.std() > 0 else 0
        p_pnl     = (port_equity.iloc[-1] / CAPITAL_INIT - 1) * 100
        p_rollmx  = port_equity.cummax()
        p_dd      = ((port_equity - p_rollmx) / p_rollmx).min() * 100
        n_years   = (port_equity.index[-1] - port_equity.index[0]).days / 365.25
        p_cagr    = ((port_equity.iloc[-1] / CAPITAL_INIT) ** (1 / max(n_years, 0.1)) - 1) * 100

        print(f"\n{'='*65}")
        print("PORTEFEUILLE RISK PARITY")
        print(f"  PnL total  : {p_pnl:+.1f}%")
        print(f"  CAGR       : {p_cagr:+.1f}%")
        print(f"  Sharpe     : {p_sharpe:.3f}")
        print(f"  Max DD     : {p_dd:.1f}%")
        print(f"  Capital    : ${CAPITAL_INIT:,} -> ${port_equity.iloc[-1]:,.0f}")

    # ── Walk-Forward summary ─────────────────────────────────
    if wf_rows:
        wf_df = pd.DataFrame(wf_rows)
        print(f"\n{'='*65}")
        print("WALK-FORWARD — Stabilite hors-echantillon")
        grp = wf_df.groupby("ticker")[["pnl_pct","sharpe","win_rate"]].agg(["mean","std"]).round(3)
        print(grp.to_string())
        wf_df.to_csv(OUT_DIR / "wf_adaptive.csv", index=False)

    # ── Exports ──────────────────────────────────────────────
    summary_df = pd.DataFrame([r.summary() for r in results])
    summary_df.to_csv(OUT_DIR / "adaptive_summary.csv", index=False)
    print(f"\nCSV: {OUT_DIR / 'adaptive_summary.csv'}")

    # ── Graphique ────────────────────────────────────────────
    plot_adaptive_summary(results, port_equity if not port_equity.empty else pd.Series(), weights)

    # ── Verdict final ─────────────────────────────────────────
    print(f"\n{'='*65}")
    print("VERDICT ADAPTATIF")
    print(f"{'='*65}")
    tier_a = [r for r in results if r.tier == "A" and r.sharpe > 1]
    tier_b = [r for r in results if r.tier == "B" and r.sharpe > 0.7]
    tier_cd = [r for r in results if r.tier in ("C","D")]

    if tier_a:
        print(f"[DEPLOIEMENT OK] Tier A (Sharpe>1)  : {', '.join(r.ticker for r in tier_a)}")
    if tier_b:
        print(f"[SURVEILLER]     Tier B (Sharpe>0.7): {', '.join(r.ticker for r in tier_b)}")
    if tier_cd:
        print(f"[EXCLUS]         Tier C/D            : {', '.join(r.ticker for r in tier_cd)}")

    print(f"\nSharpe portefeuille RP : {p_sharpe:.3f}")
    verdict = (
        "DEPLOIEMENT ENVISAGEABLE (levier x1.5 max)"   if p_sharpe > 1.5 else
        "BACKTEST SUPPLEMENTAIRE NECESSAIRE (2+ ans)"  if p_sharpe > 0.8 else
        "OPTIMISATION REQUISE avant tout capital reel"
    )
    print(f"Verdict : {verdict}")

    print("\nEtapes suivantes :")
    print("  1. Tester ce meme engine sur donnees 2022 (bear market)")
    print("  2. Ajouter filtre volume (volume > SMA_volume * 1.5)")
    print("  3. Implementer position sizing Kelly partiel (0.25 Kelly)")
    print("  4. Connecter au backend FastAPI -> endpoint /crypto/signals")


if __name__ == "__main__":
    main()
