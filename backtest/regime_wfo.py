"""
Regime WFO v1 — Walk-Forward avec filtre macro par actif
BTC  : EMA200  +5% seuil Bull
SOL  : EMA246  -5% seuil (ecarte uniquement le gros Bear)
OOS  : 180 jours minimum  |  IS ancre depuis le debut
"""
import os, sys, warnings
import numpy as np
import pandas as pd
import yfinance as yf
from binance.client import Client
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")

from backtest.wfo_engine import (
    load_binance, load_yfinance,
    build_signal, run_strict_backtest, compute_metrics,
    wilder_atr, MULTIPLIERS,
)

# ─── Filtre regime par actif ─────────────────────────────────────────────────

REGIME_CONFIG = {
    "BTCUSDT": {
        "ema_span" : 200,
        "bull_band": 1.05,   # close > EMA*1.05  --> LONG autorise
        "bear_band": None,   # en dessous : CASH total
    },
    "SOLUSDT": {
        "ema_span" : 246,
        "bull_band": 0.95,   # close > EMA*0.95  --> LONG autorise (inclut sideways)
        "bear_band": None,
    },
}

DEFAULT_CONFIG = {
    "ema_span" : 200,
    "bull_band": 1.05,
    "bear_band": None,
}


def apply_regime_filter(df, asset_name):
    cfg = REGIME_CONFIG.get(asset_name, DEFAULT_CONFIG)
    df  = df.copy()
    col = f"ema{cfg['ema_span']}"
    df[col] = df["close"].ewm(span=cfg["ema_span"], adjust=False).mean()

    threshold = df[col] * cfg["bull_band"]
    df["regime_allowed"] = (df["close"] > threshold).astype(int)

    # Signal filtre : LONG seulement si regime autorise
    df["signal_raw"]  = df["signal"].copy()
    df["signal"]      = np.where(
        (df["signal_raw"] == 1) & (df["regime_allowed"] == 1), 1, 0
    )
    return df


# ─── Folds ancres, OOS fixe ──────────────────────────────────────────────────

def get_regime_folds(df, n_folds=3, oos_days=180):
    """
    Ancrage fixe : IS commence toujours en 0 et grandit.
    OOS = fenetre de oos_days barres qui suit l'IS.
    Garantit >= oos_days barres par fenetre OOS.
    """
    total = len(df)
    # IS minimal pour avoir un premier fold coherent : 2x OOS
    min_is = oos_days * 2
    if total < min_is + oos_days:
        return []

    folds = []
    for fold in range(n_folds):
        end_is  = total - (n_folds - fold) * oos_days
        end_oos = end_is + oos_days
        if end_is < min_is or end_oos > total:
            continue
        folds.append((df.iloc[0:end_is], df.iloc[end_is:end_oos]))
    return folds


# ─── IS Optimizer ────────────────────────────────────────────────────────────

def optimize_is_regime(df_is):
    best_m  = 2.5
    best_sh = -np.inf
    for m in MULTIPLIERS:
        df_r, tr = run_strict_backtest(df_is, atr_multiplier=m)
        k = compute_metrics(df_r, tr)
        if k["pf"] >= 1.1 and k["trades"] >= 5 and k["sharpe"] > best_sh:
            best_sh = k["sharpe"]
            best_m  = m
    return best_m, round(best_sh, 3)


# ─── WFO Regime Runner ───────────────────────────────────────────────────────

W = 104

def run_regime_wfo(df_full, asset_name, n_folds=3, oos_days=180):
    df_filtered = apply_regime_filter(df_full, asset_name)
    folds       = get_regime_folds(df_filtered, n_folds=n_folds, oos_days=oos_days)

    if not folds:
        print(f"\n[SKIP] {asset_name} -- historique insuffisant pour {n_folds} folds x {oos_days}j")
        return None

    cfg = REGIME_CONFIG.get(asset_name, DEFAULT_CONFIG)
    regime_label = (
        f"EMA{cfg['ema_span']} {'> ' + str(cfg['bull_band'])}"
    )

    print(f"\n{'='*W}")
    print(
        f"  REGIME WFO v1 -- {asset_name}"
        f"   ({len(df_filtered)} barres | filtre: {regime_label}"
        f" | OOS={oos_days}j | {n_folds} folds ancres)"
    )
    print(f"{'='*W}")

    # Statistiques du filtre
    pct_active = df_filtered["regime_allowed"].mean() * 100
    pct_signal = df_filtered["signal"].mean() * 100
    pct_raw    = df_filtered["signal_raw"].mean() * 100
    print(
        f"  Regime LONG autorise : {pct_active:.1f}% du temps  |"
        f"  Signal brut : {pct_raw:.1f}%  -->  Signal filtre : {pct_signal:.1f}%"
        f"  (filtrage : {pct_raw - pct_signal:.1f}pts)"
    )
    print(f"{'─'*W}")

    hdr = (
        f"  {'Fold':>4} | {'Periode OOS':>23}"
        f" | {'IS bars':>7} | {'OOS bars':>8}"
        f" | {'Opt ATR':>7} | {'IS Sh':>6}"
        f" | {'OOS Sh':>6} | {'OOS PF':>6}"
        f" | {'OOS DD':>7} | {'Trades':>6}"
        f" | {'WR':>5} | {'AvgTr':>6} | {'Ratio':>5}"
    )
    print(hdr)
    print(f"  {'─'*100}")

    oos_sharpes, oos_pfs, oos_dds, ratios, all_trades = [], [], [], [], []
    opt_atrs = []

    for idx, (df_is, df_oos) in enumerate(folds):
        start_oos = df_oos.index[0].strftime("%Y-%m-%d")
        end_oos   = df_oos.index[-1].strftime("%Y-%m-%d")

        best_atr, sh_is = optimize_is_regime(df_is)
        opt_atrs.append(best_atr)

        # Warm-up Wilder ATR (28 barres IS)
        warmup   = df_is.iloc[-28:]
        df_warm  = pd.concat([warmup, df_oos])
        df_r, _  = run_strict_backtest(df_warm, atr_multiplier=best_atr)
        df_oos_r = df_r.iloc[len(warmup):].copy()

        _, tr_oos = run_strict_backtest(df_oos, atr_multiplier=best_atr)
        k = compute_metrics(df_oos_r, tr_oos)

        ratio = round(k["sharpe"] / sh_is, 2) if sh_is > 0 else 0.0
        oos_sharpes.append(k["sharpe"])
        oos_pfs.append(k["pf"])
        oos_dds.append(k["maxdd"])
        ratios.append(ratio)
        all_trades.append(k["trades"])

        tag = " <-- GO" if k["sharpe"] >= 0.5 and k["pf"] >= 1.2 else \
              " <-- +" if k["sharpe"] > 0 else ""
        line = (
            f"  {idx+1:>4} | {start_oos} -> {end_oos}"
            f" | {len(df_is):>7} | {len(df_oos):>8}"
            f" | {best_atr:>7} | {sh_is:>6.3f}"
            f" | {k['sharpe']:>6.3f} | {k['pf']:>6.2f}"
            f" | {k['maxdd']:>6.1f}% | {k['trades']:>6}"
            f" | {k['wr']:>4.0f}% | {k['avg_t']:>+5.2f}% | {ratio:>5.2f}{tag}"
        )
        print(line)

    print(f"  {'─'*100}")

    mean_sh    = round(float(np.mean(oos_sharpes)), 3)
    mean_pf    = round(float(np.mean(oos_pfs)), 2)
    mean_dd    = round(float(np.mean(oos_dds)), 1)
    mean_ratio = round(float(np.mean(ratios)), 2)
    total_t    = sum(all_trades)
    consistency = sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes) * 100
    drift       = len(set(opt_atrs))
    drift_str   = f"stable ({opt_atrs[0]})" if drift == 1 else f"derive {opt_atrs}"

    synth = (
        f"  {'SYNTHESE':>4} | {'Moyenne OOS':>23}"
        f" | {' ':>7} | {' ':>8}"
        f" | {' ':>7} | {' ':>6}"
        f" | {mean_sh:>6.3f} | {mean_pf:>6.2f}"
        f" | {mean_dd:>6.1f}% | {total_t:>6}"
        f" | {' ':>5} | {' ':>6} | {mean_ratio:>5.2f}"
    )
    print(synth)
    print()
    print(f"  Consistance OOS Sharpe > 0   : {consistency:.0f}%")
    print(f"  Ratio robustesse OOS/IS      : {mean_ratio:.2f}  (seuil >= 0.50)")
    print(f"  Derive parametrique ATR      : {drift_str}")

    is_prod = mean_sh >= 0.8 and mean_pf >= 1.3 and mean_dd > -30 and mean_ratio >= 0.5
    is_go   = mean_sh >= 0.5 and mean_pf >= 1.2 and mean_ratio >= 0.4
    is_pos  = mean_sh > 0 and mean_pf >= 1.1 and consistency >= 66
    verdict = (
        "[PROD] ROBUSTE -- Paper Trading valide"           if is_prod else
        "[GO]   Operationnel -- Deployer en paper trading" if is_go   else
        "[POS]  Positif -- Surveiller 1 trimestre live"    if is_pos  else
        "[SKIP] Insuffisant -- Ne pas deployer"
    )
    print(f"\n  VERDICT : {verdict}")
    print(f"{'='*W}")

    return dict(
        asset=asset_name, mean_sh=mean_sh, mean_pf=mean_pf,
        mean_dd=mean_dd, mean_ratio=mean_ratio,
        consistency=consistency, drift=drift_str,
        opt_atrs=opt_atrs, verdict=verdict,
        regime_filter=regime_label, pct_active=round(pct_active, 1),
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    ASSETS = [
        ("BTCUSDT", lambda: load_binance("BTCUSDT")),
        ("SOLUSDT", lambda: load_binance("SOLUSDT")),
    ]

    summary = []
    for name, loader in ASSETS:
        try:
            df_raw = loader()
            if df_raw.empty or len(df_raw) < 300:
                print(f"\n[SKIP] {name} -- donnees insuffisantes")
                continue
            df = build_signal(df_raw)
            r  = run_regime_wfo(df, name, n_folds=3, oos_days=180)
            if r:
                summary.append(r)
        except Exception as e:
            import traceback
            print(f"\n[ERROR] {name}: {e}")
            traceback.print_exc()

    # ─── Recap ────────────────────────────────────────────────────────────────
    if summary:
        print(f"\n\n{'#'*W}")
        print(f"  RECAP REGIME WFO v1  |  SMA16/19 + RSI>50 + MFI>50 + ATR Stop + Filtre EMA")
        print(f"{'#'*W}")
        hdr2 = (
            f"  {'Actif':<10} | {'Filtre':<18} | {'Actif%':>6}"
            f" | {'Sh OOS':>6} | {'PF OOS':>6} | {'DD OOS':>7}"
            f" | {'Ratio':>5} | {'Consist':>7} | {'ATR':>10} | Verdict"
        )
        print(hdr2)
        print(f"  {'─'*(W-2)}")
        for r in summary:
            row = (
                f"  {r['asset']:<10} | {r['regime_filter']:<18} | {r['pct_active']:>5.1f}%"
                f" | {r['mean_sh']:>6.3f} | {r['mean_pf']:>6.2f} | {r['mean_dd']:>6.1f}%"
                f" | {r['mean_ratio']:>5.2f} | {r['consistency']:>6.0f}%"
                f" | {str(r['opt_atrs']):>10} | {r['verdict']}"
            )
            print(row)
        print(f"{'#'*W}")

        # Comparaison sans filtre vs avec filtre
        print(f"\n  IMPACT DU FILTRE DE REGIME (reference : WFO sans filtre)")
        print(f"  {'─'*60}")
        print(f"  WFO sans filtre (run precedent) :")
        print(f"    BTC  : Sharpe -0.848  |  Consistance 33%  |  Ratio -0.83")
        print(f"    SOL  : Sharpe -0.678  |  Consistance 33%  |  Ratio -0.42")
        print(f"\n  WFO avec filtre regime + OOS 180j (run actuel) :")
        for r in summary:
            print(f"    {r['asset']:<5}: Sharpe {r['mean_sh']:>+.3f}  |  Consistance {r['consistency']:.0f}%  |  Ratio {r['mean_ratio']:>.2f}")
        print(f"{'#'*W}")
