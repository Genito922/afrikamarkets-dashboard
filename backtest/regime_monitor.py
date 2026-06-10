"""
Regime Monitor — Production
Surveille quotidiennement les conditions de déploiement du Signal B.
Détecte le flip Bull pour BTC (EMA200×1.05) et SOL (EMA246×0.95).
Calcule le signal paper trading du jour et les métriques live.

Usage :
  python -m backtest.regime_monitor            # run once
  python -m backtest.regime_monitor --watch    # boucle toutes les heures
"""
import argparse
import json
import logging
import os
import sys
import time
import warnings
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")

from backtest.wfo_engine import load_binance, rsi, mfi, wilder_atr

# ─── Logging ──────────────────────────────────────────────────────────────────

_LOG_DIR = Path(__file__).parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_LOG_FILE = _LOG_DIR / "monitor.log"

def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("regime_monitor")
    if logger.handlers:
        return logger                        # déjà initialisé (watch mode)

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Fichier tournant : 1 Mo × 5 rotations
    fh = RotatingFileHandler(
        _LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Console : INFO+
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

log = _setup_logger()

# ─── Configuration déploiement ────────────────────────────────────────────────

DEPLOY_CONFIG = {
    "BTCUSDT": {
        "ema_span"    : 200,
        "bull_band"   : 1.05,
        "atr_mult"    : 2.5,
        "confirm_days": 2,
        "label"       : "BTC",
    },
    "SOLUSDT": {
        "ema_span"    : 246,
        "bull_band"   : 0.95,
        "atr_mult"    : 1.5,
        "confirm_days": 2,
        "label"       : "SOL",
    },
}

LOAD_DAYS = 400


# ─── Indicateurs ──────────────────────────────────────────────────────────────

def build_monitor_df(df_raw, ema_span, bull_band):
    df = df_raw.copy()
    col = f"ema{ema_span}"
    df[col]         = df["close"].ewm(span=ema_span, adjust=False).mean()
    df["threshold"] = df[col] * bull_band
    df["in_bull"]   = (df["close"] > df["threshold"]).astype(int)

    df["s16"]   = df["close"].rolling(16).mean()
    df["s19"]   = df["close"].rolling(19).mean()
    df["rsi14"] = rsi(df["close"], 14)
    df["mfi14"] = mfi(df, 14)
    df["atr14"] = wilder_atr(df)

    cond_now  = (df.s16 > df.s19) & (df.rsi14 > 50) & (df.mfi14 > 50)
    cond_prev = (
        (df.s16.shift(1) > df.s19.shift(1)) &
        (df.rsi14.shift(1) > 50) &
        (df.mfi14.shift(1) > 50)
    )
    df["signal_b"] = np.where(cond_now & cond_prev & (df["in_bull"] == 1), 1, 0)

    df["consec_bull"] = df["in_bull"].groupby(
        (df["in_bull"] != df["in_bull"].shift()).cumsum()
    ).cumcount() + 1
    df.loc[df["in_bull"] == 0, "consec_bull"] = 0

    df.dropna(inplace=True)
    return df


# ─── Rapport par actif ────────────────────────────────────────────────────────

def asset_report(symbol, cfg):
    log.debug("[%s] Téléchargement données (%d jours)…", cfg["label"], LOAD_DAYS)
    df_raw = load_binance(symbol, days=LOAD_DAYS)
    df     = build_monitor_df(df_raw, cfg["ema_span"], cfg["bull_band"])

    last  = df.iloc[-1]
    prev  = df.iloc[-2]

    in_bull      = bool(last["in_bull"])
    consec       = int(last["consec_bull"])
    deploy_ready = in_bull and (consec >= cfg["confirm_days"])

    flipped_up   = bool(last["in_bull"]) and not bool(prev["in_bull"])
    flipped_down = not bool(last["in_bull"]) and bool(prev["in_bull"])

    signal_today = int(last["signal_b"])

    ema_val  = last[f"ema{cfg['ema_span']}"]
    dist_pct = (last["close"] - last["threshold"]) / last["threshold"] * 100
    ema_5d   = df[f"ema{cfg['ema_span']}"].iloc[-6]
    ema_slope = (ema_val - ema_5d) / ema_5d * 100

    regime_str = "BULL" if in_bull else "BEAR"
    log.info(
        "[%s] %s | prix=%.2f | consec=%dj | dist=%+.2f%% | RSI=%.0f | MFI=%.0f | Signal=%s",
        cfg["label"], regime_str, last["close"], consec,
        dist_pct, last["rsi14"], last["mfi14"],
        "LONG" if signal_today == 1 else "----",
    )

    if flipped_up:
        log.warning("[%s] FLIP BULL détecté — EMA%d franchie à la hausse (%+.2f%%)",
                    cfg["label"], cfg["ema_span"], dist_pct)
    if flipped_down:
        log.warning("[%s] FLIP BEAR détecté — EMA%d cassée à la baisse (%+.2f%%)",
                    cfg["label"], cfg["ema_span"], dist_pct)

    if deploy_ready and signal_today == 1:
        stop = last["close"] - cfg["atr_mult"] * last["atr14"]
        log.critical(
            "[%s] *** PAPER TRADE SIGNAL *** LONG @ ouverture | Stop=%.2f | ATR×%.1f",
            cfg["label"], stop, cfg["atr_mult"],
        )

    return dict(
        symbol       = symbol,
        label        = cfg["label"],
        close        = last["close"],
        ema_val      = ema_val,
        threshold    = last["threshold"],
        dist_pct     = dist_pct,
        ema_slope_5d = ema_slope,
        in_bull      = in_bull,
        consec_bull  = consec,
        deploy_ready = deploy_ready,
        flipped_up   = flipped_up,
        flipped_down = flipped_down,
        signal_today = signal_today,
        rsi14        = last["rsi14"],
        mfi14        = last["mfi14"],
        atr14        = last["atr14"],
        sma16        = last["s16"],
        sma19        = last["s19"],
        atr_mult     = cfg["atr_mult"],
        confirm_days = cfg["confirm_days"],
        ema_span     = cfg["ema_span"],
        ts           = df.index[-1],
    )


# ─── Affichage console ────────────────────────────────────────────────────────

def print_dashboard(reports, run_ts):
    W = 72
    print(f"\n{'='*W}")
    print(f"  REGIME MONITOR v2  —  Signal B (SMA16/19 + RSI + MFI + confirm)")
    print(f"  {run_ts.strftime('%Y-%m-%d %H:%M UTC')}  |  log → {_LOG_FILE}")
    print(f"{'='*W}")

    any_deploy   = False
    flip_events  = []

    for r in reports:
        regime_str = "BULL " if r["in_bull"] else "BEAR "
        deploy_str = (
            "DEPLOY READY"
            if r["deploy_ready"]
            else f"attente ({r['consec_bull']}/{r['confirm_days']}j)"
        )

        flip_tag = ""
        if r["flipped_up"]:
            flip_tag = "  <<< FLIP BULL !"
            flip_events.append(f"{r['label']} vient de passer en BULL")
        elif r["flipped_down"]:
            flip_tag = "  <<< FLIP BEAR !"
            flip_events.append(f"{r['label']} vient de passer en BEAR")

        signal_tag = "LONG" if r["signal_today"] == 1 else "----"

        print(f"\n  {r['label']}  ({r['symbol']})")
        print(f"  {'─'*50}")
        print(f"  Prix        : {r['close']:>12,.2f}  USDT")
        print(f"  EMA{r['ema_span']}d seuil : {r['threshold']:>12,.2f}  "
              f"({r['dist_pct']:>+.2f}% vs seuil){flip_tag}")
        print(f"  Pente EMA/5j: {r['ema_slope_5d']:>+.3f}%  "
              f"({'montante' if r['ema_slope_5d'] > 0 else 'descendante'})")
        print(f"  Regime      : {regime_str}  |  Consécutif : {r['consec_bull']}j  |  {deploy_str}")
        print(f"  RSI14       : {r['rsi14']:.1f}   MFI14 : {r['mfi14']:.1f}   ATR14 : {r['atr14']:.4f}")
        print(f"  SMA16/SMA19 : {r['sma16']:.2f} / {r['sma19']:.2f}  "
              f"({'croisé' if r['sma16'] > r['sma19'] else 'sous'})")
        print(f"  Signal B    : [{signal_tag}]  "
              f"({'entré en position' if r['signal_today'] == 1 else 'hors marché / cash'})")

        if r["deploy_ready"] and r["signal_today"] == 1:
            stop = r["close"] - r["atr_mult"] * r["atr14"]
            print(f"\n  *** PAPER TRADE SIGNAL ***")
            print(f"  Entrée : LONG à l'open de la prochaine barre")
            print(f"  Stop   : {stop:,.2f}  (ATR×{r['atr_mult']} trailing)")
            print(f"  Taille : 1% du capital (paper trading)")
            any_deploy = True

    print(f"\n{'='*W}")

    if flip_events:
        print(f"\n  ALERTES FLIP DÉTECTÉES :")
        for ev in flip_events:
            print(f"    -> {ev}")

    if any_deploy:
        print(f"\n  STATUS : PAPER TRADING ACTIF — surveiller les signaux quotidiens")
    else:
        print(f"\n  STATUS : EN ATTENTE DU FLIP BULL")
        for r in reports:
            if not r["deploy_ready"]:
                needed    = r["threshold"] - r["close"]
                pct       = abs(r["dist_pct"])
                direction = "manque" if r["dist_pct"] < 0 else "au-dessus de"
                print(
                    f"    {r['label']} : {direction} {pct:.2f}% du seuil EMA  "
                    f"({'il faut +' + f'{needed:,.0f}' + ' USDT' if needed > 0 else 'régime valide'})"
                )
        if all(r["consec_bull"] == 0 for r in reports):
            print(f"\n  Aucune action requise. Vérifier demain.")

    print(f"{'='*W}\n")
    return any_deploy, flip_events


# ─── Sauvegarde état JSON ─────────────────────────────────────────────────────

def save_state(reports, run_ts, output_path="backtest/regime_state.json"):
    state = {
        "run_at": run_ts.isoformat(),
        "assets": {},
    }
    for r in reports:
        state["assets"][r["symbol"]] = {
            "close"       : round(r["close"], 4),
            "regime"      : "bull" if r["in_bull"] else "bear",
            "consec_days" : r["consec_bull"],
            "deploy_ready": r["deploy_ready"],
            "signal_b"    : r["signal_today"],
            "dist_pct"    : round(r["dist_pct"], 3),
            "rsi14"       : round(r["rsi14"], 1),
            "mfi14"       : round(r["mfi14"], 1),
            "flipped_up"  : r["flipped_up"],
            "flipped_down": r["flipped_down"],
        }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    log.info("État sauvegardé → %s", output_path)


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_once():
    run_ts  = datetime.now(timezone.utc)
    log.info("=== Run démarré — %d actifs ===", len(DEPLOY_CONFIG))
    reports = []

    for symbol, cfg in DEPLOY_CONFIG.items():
        try:
            r = asset_report(symbol, cfg)
            reports.append(r)
        except Exception as e:
            log.error("[%s] Erreur chargement données : %s", symbol, e, exc_info=True)

    if reports:
        print_dashboard(reports, run_ts)
        save_state(reports, run_ts)

    log.info("=== Run terminé — %d/%d actifs OK ===", len(reports), len(DEPLOY_CONFIG))
    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true",
                        help="Boucle de surveillance toutes les heures")
    parser.add_argument("--interval", type=int, default=3600,
                        help="Intervalle en secondes (défaut 3600)")
    args = parser.parse_args()

    if args.watch:
        log.info("Mode surveillance actif (intervalle : %ds)", args.interval)
        print(f"  Mode surveillance actif (intervalle : {args.interval}s)")
        print(f"  Ctrl+C pour arrêter\n")
        while True:
            try:
                run_once()
                log.info("Prochain check dans %d minutes.", args.interval // 60)
                print(f"  Prochain check dans {args.interval//60} minutes...")
                time.sleep(args.interval)
            except KeyboardInterrupt:
                log.info("Surveillance arrêtée par l'utilisateur.")
                print("\n  Surveillance arrêtée.")
                break
    else:
        run_once()
