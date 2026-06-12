"""
Regime Mapper — Cartographie de performance par regime macro
Ventile les rendements de la strategie SMA16/19+RSI+MFI+ATR Stop
selon Bull / Sideways / Bear (EMA200 vs EMA246, seuil +/-5%)
"""
import os, sys, warnings
import numpy as np
import pandas as pd
import yfinance as yf
from binance.client import Client
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")

# Reutilise les fonctions du moteur strict
from backtest.wfo_engine import (
    load_binance, load_yfinance,
    build_signal, run_strict_backtest,
    wilder_atr,
)

# ─── Regime Labelling ────────────────────────────────────────────────────────

def label_regime(df, ema_span=200, band=0.05):
    """
    Bull    : close > EMA * (1 + band)
    Bear    : close < EMA * (1 - band)
    Sideways: entre les deux bandes
    """
    df = df.copy()
    col = f"ema{ema_span}"
    df[col] = df["close"].ewm(span=ema_span, adjust=False).mean()
    upper    = df[col] * (1 + band)
    lower    = df[col] * (1 - band)
    df["regime"] = np.select(
        [df["close"] > upper, df["close"] < lower],
        ["bull", "bear"],
        default="sideways",
    )
    return df


# ─── Performance par regime ──────────────────────────────────────────────────

def regime_metrics(returns_series, label=""):
    """Sharpe annualise, PnL%, % du temps dans ce regime."""
    r = returns_series.dropna()
    if len(r) == 0 or r.std() == 0:
        return dict(sharpe=0.0, pnl=0.0, days=0, pct_time=0.0)
    sharpe = r.mean() / r.std() * np.sqrt(252)
    pnl    = (1 + r).prod() - 1
    return dict(
        sharpe   =round(float(sharpe), 3),
        pnl      =round(float(pnl * 100), 1),
        days     =int(len(r)),
        pct_time =0.0,   # rempli apres
    )


def compute_regime_map(df_input, asset_name, atr_multiplier=2.5,
                       ema_span=200, band=0.05):
    """
    Applique le backtest strict et ventile les rendements journaliers
    par regime macro determine par EMA(ema_span) +/- band%.
    """
    df = label_regime(df_input, ema_span=ema_span, band=band)
    df_res, _ = run_strict_backtest(df, atr_multiplier=atr_multiplier)
    df_res["strat_returns"] = df_res["strat_returns"].fillna(0)

    # Regime de J-1 pour decider l'action de J (coherence temporelle)
    df_res["regime_lag"] = df_res["regime"].shift(1)

    total_days = len(df_res)
    out = {"asset": asset_name, "ema": ema_span, "atr": atr_multiplier}

    for reg in ["bull", "sideways", "bear"]:
        mask = df_res["regime_lag"] == reg
        r    = df_res.loc[mask, "strat_returns"]
        m    = regime_metrics(r)
        m["pct_time"] = round(mask.sum() / total_days * 100, 1)
        out[reg] = m

    # Statistiques globales de la distribution des regimes
    counts = df_res["regime"].value_counts()
    out["regime_distribution"] = {
        k: round(counts.get(k, 0) / total_days * 100, 1)
        for k in ["bull", "sideways", "bear"]
    }

    return out


# ─── Affichage ───────────────────────────────────────────────────────────────

def print_regime_table(results_200, results_246):
    """
    Affiche la matrice cote-a-cote EMA200 vs EMA246 pour un actif.
    """
    assert results_200["asset"] == results_246["asset"]
    name = results_200["asset"]

    W = 96
    print(f"\n{'='*W}")
    print(f"  {name}  —  ATR {results_200['atr']}")
    print(f"{'='*W}")

    # Distribution des regimes
    d200 = results_200["regime_distribution"]
    d246 = results_246["regime_distribution"]
    print(
        f"  Distribution  Bull: {d200['bull']:>5.1f}%  "
        f"Side: {d200['sideways']:>5.1f}%  Bear: {d200['bear']:>5.1f}%"
        f"        "
        f"Bull: {d246['bull']:>5.1f}%  "
        f"Side: {d246['sideways']:>5.1f}%  Bear: {d246['bear']:>5.1f}%"
    )
    print(f"{'─'*W}")
    header = (
        f"  {'Regime':<10}"
        f"  {'EMA200':^28}"
        f"  {'EMA246':^28}"
        f"  {'Delta Sharpe':>12}"
    )
    print(header)
    sub = (
        f"  {'':10}"
        f"  {'Sharpe':>7} {'PnL%':>7} {'Days':>6} {'Time%':>5}"
        f"  {'Sharpe':>7} {'PnL%':>7} {'Days':>6} {'Time%':>5}"
    )
    print(sub)
    print(f"  {'─'*92}")

    for reg in ["bull", "sideways", "bear"]:
        m2  = results_200[reg]
        m24 = results_246[reg]
        delta = m24["sharpe"] - m2["sharpe"]
        delta_str = f"{delta:>+.3f}"
        tag = ""
        if reg == "sideways" and delta > 0.1:
            tag = " <-- meilleur"
        elif reg == "bull" and delta < -0.1:
            tag = " <-- coute"
        row = (
            f"  {reg.upper():<10}"
            f"  {m2['sharpe']:>7.3f} {m2['pnl']:>6.1f}% {m2['days']:>6} {m2['pct_time']:>5.1f}%"
            f"  {m24['sharpe']:>7.3f} {m24['pnl']:>6.1f}% {m24['days']:>6} {m24['pct_time']:>5.1f}%"
            f"  {delta_str:>12}{tag}"
        )
        print(row)

    print(f"{'='*W}")


def print_global_summary(all_results):
    """Recapitulatif multi-actifs en une seule vue."""
    W = 100
    print(f"\n\n{'#'*W}")
    print(f"  SYNTHESE GLOBALE — Sharpe par regime  (EMA200 | EMA246)")
    print(f"{'#'*W}")
    hdr = (
        f"  {'Actif':<12}"
        f"  {'Bull200':>7} {'Bull246':>7}"
        f"  {'Side200':>7} {'Side246':>7}"
        f"  {'Bear200':>7} {'Bear246':>7}"
        f"  {'Verdict':>12}"
    )
    print(hdr)
    print(f"  {'─'*96}")

    for r200, r246 in all_results:
        bull_ok  = r200["bull"]["sharpe"]  >= 0.8
        side_ok  = r200["sideways"]["sharpe"] >= -0.1   # tolere legere perte
        bear_ok  = r200["bear"]["sharpe"]  >= -0.3
        asym     = (r200["bull"]["sharpe"] - r200["bear"]["sharpe"]) >= 1.0

        verdict = (
            "ASYMETRIE OK" if asym and bull_ok else
            "PARTIEL"      if bull_ok else
            "REGIME FAIBLE"
        )

        row = (
            f"  {r200['asset']:<12}"
            f"  {r200['bull']['sharpe']:>7.3f} {r246['bull']['sharpe']:>7.3f}"
            f"  {r200['sideways']['sharpe']:>7.3f} {r246['sideways']['sharpe']:>7.3f}"
            f"  {r200['bear']['sharpe']:>7.3f} {r246['bear']['sharpe']:>7.3f}"
            f"  {verdict:>12}"
        )
        print(row)

    print(f"{'#'*W}")
    print()
    print("  REGLES DU RegimeRouter (si asymetrie confirmee)")
    print("  ─────────────────────────────────────────────────────────")
    print("  BULL     : SMA16/19 + RSI>50 + MFI>50 + ATR Stop  --> LONG")
    print("  SIDEWAYS : Cash (preservation capital)")
    print("  BEAR     : Cash ou Or si Or en regime BULL")
    print(f"{'#'*W}")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # ATR optimal identifie lors du run precedent
    ASSET_CONFIG = {
        "BTCUSDT" : {"loader": lambda: load_binance("BTCUSDT"), "atr": 2.5},
        "ETHUSDT" : {"loader": lambda: load_binance("ETHUSDT"), "atr": 2.5},
        "SOLUSDT" : {"loader": lambda: load_binance("SOLUSDT"), "atr": 1.5},
        "GC=F (Or)": {"loader": lambda: load_yfinance("GC=F"),  "atr": 2.0},
    }

    all_results = []

    for name, cfg in ASSET_CONFIG.items():
        try:
            df_raw = cfg["loader"]()
            if df_raw.empty or len(df_raw) < 250:
                print(f"\n[SKIP] {name} — donnees insuffisantes")
                continue
            df = build_signal(df_raw)

            r200 = compute_regime_map(df, name, atr_multiplier=cfg["atr"],
                                      ema_span=200, band=0.05)
            r246 = compute_regime_map(df, name, atr_multiplier=cfg["atr"],
                                      ema_span=246, band=0.05)

            print_regime_table(r200, r246)
            all_results.append((r200, r246))

        except Exception as e:
            print(f"\n[ERROR] {name}: {e}")

    if all_results:
        print_global_summary(all_results)
