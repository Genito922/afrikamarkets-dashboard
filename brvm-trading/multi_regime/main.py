"""
Multi-Regime Engine — main.py
===============================
Pipeline complet :
  1. Chargement (Binance / yfinance)
  2. Detection de regime (ATR%/ADX par classe d'actif)
  3. Routing strategie (SMATrend / MeanReversion / RiskOff)
  4. Walk-forward 3 folds
  5. Allocation portefeuille (hybride regime + risk parity)
  6. Tableau comparatif final

Usage :
  python brvm-trading/multi_regime/main.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd

from loader    import load, asset_class, REGISTRY
from detector  import RegimeDetector
from strategies import StrategyRouter
from allocator  import HybridAllocator, RiskParityAllocator, print_weights
from backtest   import run_backtest, compute_metrics, WalkForward

# ── Config ─────────────────────────────────────────────────────
UNIVERSE = [
    "BTCUSDT",   # crypto large cap
    "ETHUSDT",   # crypto large cap
    "SOLUSDT",   # crypto mid cap
    "XRPUSDT",   # crypto mid cap
    "XAUUSD",    # commodity (yfinance)
    # "EURUSD",  # forex (decommente si besoin)
]

INTERVAL     = "4h"       # 30m -> 4H  (SMA_L=361×4H = 60 jours, cohérent pour trend following)
DAYS_BACK    = 365 * 3    # 3 ans
CAPITAL      = 1000       # $ par actif
SMA_S, SMA_M, SMA_L = 16, 246, 361  # en 4H: 2.7j / 41j / 60j — sens économique réel
WF_FOLDS     = 3
WF_TRAIN_PCT = 0.70
MIN_BARS     = SMA_L + 100   # minimum apres dropna

# ── Pipeline ───────────────────────────────────────────────────
def run_asset(symbol: str) -> dict | None:
    ac = asset_class(symbol)
    print(f"\n{'='*65}")
    print(f"  {symbol}  [{ac}]")
    print(f"{'='*65}")

    # 1. Data
    try:
        df = load(symbol, interval=INTERVAL, days=DAYS_BACK)
    except Exception as e:
        print(f"  ERREUR chargement : {e}")
        return None

    # 2. Regime
    rd   = RegimeDetector()
    df   = rd.detect(df, asset_class=ac)
    rs   = rd.regime_stats(df)
    print(f"  Regimes : trend={rs['trend']}% range={rs['range']}% high_vol={rs['high_vol']}%")

    # 3. Strategy routing
    router = StrategyRouter(SMA_S, SMA_M, SMA_L)
    df     = router.apply_regime_aware(df, asset_class=ac)
    df.dropna(subset=["close","position"], inplace=True)

    if len(df) < MIN_BARS:
        print(f"  SKIP : {len(df)} bars < {MIN_BARS} minimum")
        return None

    sig_l = (df.signal == 1).sum()
    sig_s = (df.signal ==-1).sum()
    print(f"  Signaux apres routing : LONG={sig_l:,} SHORT={sig_s:,} NEUTRE={(df.signal==0).sum():,}")
    print(f"  Bars utilisables : {len(df):,}")

    # 4. Backtest full period
    bt          = run_backtest(df, capital=CAPITAL)
    m, trades   = compute_metrics(bt, capital=CAPITAL)
    vol_annual  = RiskParityAllocator.realized_vol(bt["equity"])

    print(f"\n  FULL PERIOD")
    print(f"  PnL: {m['pnl_pct']:+.1f}%  Sharpe: {m['sharpe']:.3f}  "
          f"MaxDD: {m['max_drawdown_pct']:.1f}%  PF: {m['profit_factor']:.3f}  "
          f"Trades: {m['nb_trades']}  B&H: {m['buy_hold_pct']:+.1f}%")

    if not trades.empty:
        trades.to_csv(f"backtest/mr_trades_{symbol}.csv", index=False)

    # 5. Walk-forward
    wf    = WalkForward(n_folds=WF_FOLDS, train_pct=WF_TRAIN_PCT)
    folds = wf.run(bt, capital=CAPITAL)
    WalkForward.print_folds(folds, symbol)
    wf_summary = WalkForward.summary(folds)

    return {
        "symbol":      symbol,
        "asset_class": ac,
        "metrics":     m,
        "regimes":     rs,
        "wf":          wf_summary,
        "last_regime": df["regime"].iloc[-1],
        "vol_annual":  vol_annual,
        "ok":          _is_ok(m, wf_summary),
    }


def _is_ok(m: dict, wf: dict) -> bool:
    if not wf:
        return False
    return (
        wf.get("avg_oos_sharpe", 0) >= 0.8
        and wf.get("avg_oos_pf",    0) >= 1.3
        and wf.get("n_overfit",     1) == 0
        and wf.get("std_oos_sharpe",1) < 0.4
        and m.get("nb_trades",      0) >= 10
    )


def print_comparison(results: list[dict]):
    print("\n" + "="*95)
    print(f"COMPARATIF MULTI-ACTIFS  SMA {SMA_S}/{SMA_M}/{SMA_L}  {INTERVAL}  {DAYS_BACK//365}ans")
    print("="*95)
    hdr = (f"  {'Symbol':<12} {'Class':<10} {'PnL%':>7} {'Sharpe':>7} {'DD%':>6} "
           f"{'PF':>6} {'Trades':>7} {'OOS_Sh':>8} {'OOS_PF':>8} {'OF':>4}  GO")
    print(hdr)
    print("-"*95)
    for r in results:
        m  = r["metrics"]
        wf = r["wf"]
        go = "  GO" if r["ok"] else "  --"
        print(
            f"  {r['symbol']:<12} {r['asset_class']:<10} "
            f"{m['pnl_pct']:>+7.1f} {m['sharpe']:>7.3f} "
            f"{m['max_drawdown_pct']:>6.1f} {m['profit_factor']:>6.3f} "
            f"{m['nb_trades']:>7} "
            f"{wf.get('avg_oos_sharpe',0):>8.3f} "
            f"{wf.get('avg_oos_pf',0):>8.3f} "
            f"{wf.get('n_overfit','-'):>4}"
            f"{go}"
        )
    print("="*95)
    go_symbols = [r["symbol"] for r in results if r["ok"]]
    print(f"\nGO ({len(go_symbols)}/{len(results)}) : {', '.join(go_symbols) or 'aucun'}")
    print("Criteres GO : OOS Sharpe>=0.8, OOS PF>=1.3, 0 overfit, std<0.4, trades>=10")


def print_allocation(results: list[dict]):
    active = [r for r in results if r["ok"]]
    if not active:
        print("\nAucun actif GO — allocation non calculee.")
        return

    regimes = {r["symbol"]: r["last_regime"] for r in active}
    vols    = {r["symbol"]: r["vol_annual"]   for r in active}

    alloc = HybridAllocator()
    w     = alloc.compute(regimes, vols)
    print_weights(w, label="Allocation portefeuille (hybride regime + risk parity)")

    total_capital = CAPITAL * len(active)
    print(f"\n  Capital total deploye : ${total_capital:,.0f}")
    for sym, weight in sorted(w.items(), key=lambda x: -x[1]):
        print(f"  {sym:<12} => ${total_capital * weight:,.0f}  ({weight*100:.1f}%)")


def main():
    print("="*65)
    print(f"MULTI-REGIME ENGINE  |  {INTERVAL}  {DAYS_BACK//365} ans")
    print(f"Univers : {', '.join(UNIVERSE)}")
    print(f"Strategies : SMATrend({SMA_S}/{SMA_M}/{SMA_L}) | MeanReversion | RiskOff")
    print("="*65)

    results = []
    for symbol in UNIVERSE:
        res = run_asset(symbol)
        if res:
            results.append(res)

    if not results:
        print("\nAucun actif traite avec succes.")
        return

    print_comparison(results)
    print_allocation(results)


if __name__ == "__main__":
    main()
