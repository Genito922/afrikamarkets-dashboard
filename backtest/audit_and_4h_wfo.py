"""
Phase 1 : Audit PF cumule sur les 25 trades OOS daily (Go/No-Go)
Phase 2 : WFO 4H  —  EMA1200/1476 regime  +  OOS 1080 barres (180j)
"""
import os, sys, warnings
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")

from backtest.wfo_engine import (
    load_binance, build_signal,
    run_strict_backtest, compute_metrics,
    wilder_atr, MULTIPLIERS,
)
from backtest.regime_wfo import apply_regime_filter, get_regime_folds

# ═══════════════════════════════════════════════════════════════════════════════
# UTILITAIRE : backtest avec extraction trade-level
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest_with_trades(df_input, atr_multiplier=2.5, fee=0.0004):
    """
    Identique au moteur strict mais retourne aussi un DataFrame
    avec une ligne par trade (entry_date, exit_date, pnl_net).
    """
    df = df_input.copy()
    df["atr14"] = wilder_atr(df)

    closes  = df["close"].values
    opens   = df["open"].values
    atrs    = df["atr14"].values
    signals = df["signal"].values
    dates   = df.index
    n       = len(df)

    strat_returns = np.zeros(n)
    trades_log    = []

    position = 0; entry_price = 0.0; highest = 0.0
    stop = 0.0; exit_flag = False; entry_date = None; entry_idx = 0

    for i in range(1, n):
        if exit_flag:
            exec_px = opens[i]
            gross   = (exec_px - entry_price) / entry_price
            net     = gross - 2 * fee
            trades_log.append({
                "entry_date": entry_date,
                "exit_date" : dates[i],
                "entry_px"  : round(entry_price, 4),
                "exit_px"   : round(exec_px, 4),
                "pnl_net"   : round(net * 100, 3),
                "result"    : "WIN" if net > 0 else "LOSS",
            })
            position = 0; exit_flag = False
            continue

        if position == 1:
            highest = max(highest, closes[i])
            stop    = highest - atr_multiplier * atrs[i]
            if closes[i] < stop or signals[i] <= 0:
                exit_flag = True
            strat_returns[i] = closes[i] / closes[i-1] - 1
        elif position == 0 and signals[i-1] == 1:
            entry_price = opens[i] * (1 + fee)
            highest     = closes[i]
            stop        = highest - atr_multiplier * atrs[i]
            position    = 1
            entry_date  = dates[i]
            entry_idx   = i

    df["strat_returns"] = strat_returns
    return df, pd.DataFrame(trades_log)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — AUDIT DES TRADES OOS DAILY
# ═══════════════════════════════════════════════════════════════════════════════

def audit_oos_trades(df_full, asset_name, atr, n_folds=3, oos_days=180):
    df_f   = apply_regime_filter(df_full, asset_name)
    folds  = get_regime_folds(df_f, n_folds=n_folds, oos_days=oos_days)
    if not folds:
        return None

    all_trades = []
    for fold_idx, (df_is, df_oos) in enumerate(folds):
        _, trade_df = run_backtest_with_trades(df_oos, atr_multiplier=atr)
        if not trade_df.empty:
            trade_df["fold"]  = fold_idx + 1
            trade_df["asset"] = asset_name
            all_trades.append(trade_df)

    if not all_trades:
        return pd.DataFrame()
    return pd.concat(all_trades, ignore_index=True)


def print_trade_audit(trades_btc, trades_sol):
    W = 88
    print(f"\n{'='*W}")
    print(f"  PHASE 1 — AUDIT PF CUMULE : 25 TRADES OOS DAILY (Go / No-Go)")
    print(f"{'='*W}")

    for label, tdf in [("BTCUSDT", trades_btc), ("SOLUSDT", trades_sol)]:
        if tdf is None or tdf.empty:
            print(f"  {label} : aucun trade OOS\n")
            continue

        wins   = tdf[tdf["result"] == "WIN"]["pnl_net"]
        losses = tdf[tdf["result"] == "LOSS"]["pnl_net"].abs()
        pf     = wins.sum() / losses.sum() if losses.sum() > 0 else 99.0
        wr     = len(wins) / len(tdf) * 100
        avg    = tdf["pnl_net"].mean()
        total  = tdf["pnl_net"].sum()

        go = "GO  -- Edge confirme" if pf >= 1.3 else \
             "NEUTRE" if pf >= 1.0 else \
             "NO-GO -- Signal deficient"

        print(f"\n  {label}  ({len(tdf)} trades OOS)")
        print(f"  {'─'*50}")
        print(f"  Profit Factor  : {pf:.3f}   seuil GO = 1.30")
        print(f"  Win Rate       : {wr:.1f}%")
        print(f"  Avg Trade      : {avg:+.3f}%")
        print(f"  PnL OOS total  : {total:+.2f}%")
        print(f"  Decision       : {go}")

        print(f"\n  {'Fold':>4}  {'Date entree':>12}  {'Date sortie':>12}  {'PnL':>8}  {'':>5}")
        print(f"  {'─'*60}")
        for _, row in tdf.iterrows():
            bar = "+" * min(int(row["pnl_net"] / 0.5), 20) if row["pnl_net"] > 0 else \
                  "-" * min(int(abs(row["pnl_net"]) / 0.5), 20)
            print(f"  {row['fold']:>4}  {str(row['entry_date'])[:10]:>12}"
                  f"  {str(row['exit_date'])[:10]:>12}"
                  f"  {row['pnl_net']:>+7.2f}%  {bar}")

    # PF global combine
    all_df = pd.concat([t for t in [trades_btc, trades_sol]
                        if t is not None and not t.empty])
    if not all_df.empty:
        wins   = all_df[all_df["result"] == "WIN"]["pnl_net"]
        losses = all_df[all_df["result"] == "LOSS"]["pnl_net"].abs()
        pf_g   = wins.sum() / losses.sum() if losses.sum() > 0 else 99.0
        print(f"\n  {'='*W}")
        print(f"  PF GLOBAL COMBINE (BTC + SOL, {len(all_df)} trades) : {pf_g:.3f}")
        decision = "GO  -- Passage en 4H justifie" if pf_g >= 1.3 else \
                   "BORDERLINE -- Prudence" if pf_g >= 1.0 else \
                   "NO-GO -- Revoir le signal avant le 4H"
        print(f"  Decision globale : {decision}")
        print(f"  {'='*W}")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — WFO 4H
# ═══════════════════════════════════════════════════════════════════════════════

# Configuration 4H : equivalences daily × 6
REGIME_CONFIG_4H = {
    "BTCUSDT": {"ema_span": 1200, "bull_band": 1.05},   # EMA200 daily × 6
    "SOLUSDT": {"ema_span": 1476, "bull_band": 0.95},   # EMA246 daily × 6
}


def apply_regime_filter_4h(df, asset_name):
    cfg = REGIME_CONFIG_4H[asset_name]
    df  = df.copy()
    col = f"ema{cfg['ema_span']}"
    df[col] = df["close"].ewm(span=cfg["ema_span"], adjust=False).mean()
    df["regime_allowed"] = (df["close"] > df[col] * cfg["bull_band"]).astype(int)
    df["signal_raw"] = df["signal"].copy()
    df["signal"]     = np.where(
        (df["signal_raw"] == 1) & (df["regime_allowed"] == 1), 1, 0
    )
    return df


def get_4h_folds(df, n_folds=3, oos_bars=1080):
    """Folds ancres avec OOS = 1080 barres 4H (= 180 jours)."""
    total   = len(df)
    min_is  = oos_bars * 2
    folds   = []
    for fold in range(n_folds):
        end_is  = total - (n_folds - fold) * oos_bars
        end_oos = end_is + oos_bars
        if end_is < min_is or end_oos > total:
            continue
        folds.append((df.iloc[0:end_is], df.iloc[end_is:end_oos]))
    return folds


def optimize_is_4h(df_is):
    best_m  = 2.5
    best_sh = -np.inf
    for m in MULTIPLIERS:
        df_r, tr = run_strict_backtest(df_is, atr_multiplier=m)
        k = compute_metrics(df_r, tr)
        if k["pf"] >= 1.1 and k["trades"] >= 10 and k["sharpe"] > best_sh:
            best_sh = k["sharpe"]
            best_m  = m
    return best_m, round(best_sh, 3)


def run_4h_wfo(df_full, asset_name, n_folds=3, oos_bars=1080):
    df_f   = apply_regime_filter_4h(df_full, asset_name)
    folds  = get_4h_folds(df_f, n_folds=n_folds, oos_bars=oos_bars)

    cfg    = REGIME_CONFIG_4H[asset_name]
    pct_active = df_f["regime_allowed"].mean() * 100
    pct_sig    = df_f["signal"].mean() * 100
    pct_raw    = df_f["signal_raw"].mean() * 100
    oos_days   = oos_bars // 6

    W = 108
    print(f"\n{'='*W}")
    print(
        f"  REGIME WFO 4H -- {asset_name}"
        f"   ({len(df_f)} barres 4H = {len(df_f)//6}j"
        f" | EMA{cfg['ema_span']} x{cfg['bull_band']}"
        f" | OOS={oos_bars}b={oos_days}j | {n_folds} folds)"
    )
    print(f"{'='*W}")
    print(
        f"  Regime LONG actif : {pct_active:.1f}%  |"
        f"  Signal brut : {pct_raw:.1f}%  -->"
        f"  Signal filtre : {pct_sig:.1f}%"
        f"  (filtrage : {pct_raw-pct_sig:.1f}pts)"
    )
    print(f"{'─'*W}")

    hdr = (
        f"  {'Fold':>4} | {'Periode OOS':>23}"
        f" | {'IS bars':>8} | {'OOS bars':>8}"
        f" | {'ATR':>5} | {'IS Sh':>6}"
        f" | {'OOS Sh':>6} | {'PF':>5}"
        f" | {'DD':>7} | {'Tr':>4}"
        f" | {'WR':>5} | {'AvgTr':>6} | {'Ratio':>5}"
    )
    print(hdr)
    print(f"  {'─'*104}")

    oos_sharpes, oos_pfs, oos_dds, ratios, all_trades = [], [], [], [], []
    opt_atrs = []

    if not folds:
        print(f"  [SKIP] historique insuffisant pour {n_folds} folds de {oos_bars} barres")
        print(f"{'='*W}")
        return None

    for idx, (df_is, df_oos) in enumerate(folds):
        s_oos = df_oos.index[0].strftime("%Y-%m-%d")
        e_oos = df_oos.index[-1].strftime("%Y-%m-%d")

        best_atr, sh_is = optimize_is_4h(df_is)
        opt_atrs.append(best_atr)

        warmup   = df_is.iloc[-28*6:]          # 28j de warm-up ATR Wilder
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

        tag = " [PROD]" if k["sharpe"] >= 0.8 and k["pf"] >= 1.3 else \
              " [GO]  " if k["sharpe"] >= 0.5 and k["pf"] >= 1.2 else \
              " [+]   " if k["sharpe"] > 0 else ""

        line = (
            f"  {idx+1:>4} | {s_oos} -> {e_oos}"
            f" | {len(df_is):>8} | {len(df_oos):>8}"
            f" | {best_atr:>5} | {sh_is:>6.3f}"
            f" | {k['sharpe']:>6.3f} | {k['pf']:>5.2f}"
            f" | {k['maxdd']:>6.1f}% | {k['trades']:>4}"
            f" | {k['wr']:>4.0f}% | {k['avg_t']:>+5.2f}% | {ratio:>5.2f}{tag}"
        )
        print(line)

    print(f"  {'─'*104}")

    mean_sh    = round(float(np.mean(oos_sharpes)), 3)
    mean_pf    = round(float(np.mean(oos_pfs)), 2)
    mean_dd    = round(float(np.mean(oos_dds)), 1)
    mean_ratio = round(float(np.mean(ratios)), 2)
    total_t    = sum(all_trades)
    consist    = sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes) * 100
    drift_str  = f"stable ({opt_atrs[0]})" if len(set(opt_atrs)) == 1 else f"derive {opt_atrs}"

    synth = (
        f"  {'SYNTHESE':>4} | {'Moyenne OOS':>23}"
        f" | {' ':>8} | {' ':>8}"
        f" | {' ':>5} | {' ':>6}"
        f" | {mean_sh:>6.3f} | {mean_pf:>5.2f}"
        f" | {mean_dd:>6.1f}% | {total_t:>4}"
        f" | {' ':>5} | {' ':>6} | {mean_ratio:>5.2f}"
    )
    print(synth)
    print()
    print(f"  Consistance OOS Sharpe > 0   : {consist:.0f}%")
    print(f"  Ratio robustesse OOS/IS      : {mean_ratio:.2f}  (seuil >= 0.50)")
    print(f"  Derive ATR                   : {drift_str}")

    is_prod = mean_sh >= 0.7 and mean_pf >= 1.25 and mean_dd > -30 and mean_ratio >= 0.5
    is_go   = mean_sh >= 0.5 and mean_pf >= 1.15 and mean_ratio >= 0.35
    is_pos  = mean_sh > 0 and consist >= 66
    verdict = (
        "[PROD] Paper Trading valide  -- deployer en live monitor" if is_prod else
        "[GO]   Operationnel          -- paper trading 30 jours"   if is_go   else
        "[POS]  Edge positif          -- observer 1 fold de plus"  if is_pos  else
        "[SKIP] Insuffisant           -- ne pas deployer"
    )
    print(f"\n  VERDICT 4H : {verdict}")
    print(f"{'='*W}")

    return dict(
        asset=asset_name, mean_sh=mean_sh, mean_pf=mean_pf,
        mean_dd=mean_dd, mean_ratio=mean_ratio,
        consistency=consist, drift=drift_str,
        total_trades=total_t, opt_atrs=opt_atrs,
        verdict=verdict,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    print("\nChargement des donnees...")

    # Daily pour l'audit
    df_btc_d = build_signal(load_binance("BTCUSDT", days=1095))
    df_sol_d = build_signal(load_binance("SOLUSDT", days=1095))

    # 4H pour le WFO
    df_btc_4 = build_signal(load_binance("BTCUSDT", interval="4h", days=1095))
    df_sol_4 = build_signal(load_binance("SOLUSDT", interval="4h", days=1095))

    print(f"  BTC daily : {len(df_btc_d)} barres  |  4H : {len(df_btc_4)} barres")
    print(f"  SOL daily : {len(df_sol_d)} barres  |  4H : {len(df_sol_4)} barres")

    # ── Phase 1 : Audit trades OOS daily ─────────────────────────────────────
    print("\n\n[PHASE 1] Extraction des trades OOS daily...")
    trades_btc = audit_oos_trades(df_btc_d, "BTCUSDT", atr=2.5)
    trades_sol = audit_oos_trades(df_sol_d, "SOLUSDT", atr=1.5)
    print_trade_audit(trades_btc, trades_sol)

    # ── Phase 2 : WFO 4H ─────────────────────────────────────────────────────
    print("\n\n[PHASE 2] Walk-Forward 4H...")
    results_4h = []
    for name, df4 in [("BTCUSDT", df_btc_4), ("SOLUSDT", df_sol_4)]:
        r = run_4h_wfo(df4, name, n_folds=3, oos_bars=1080)
        if r:
            results_4h.append(r)

    # ── Recap final ───────────────────────────────────────────────────────────
    if results_4h:
        W = 108
        print(f"\n\n{'#'*W}")
        print(f"  RECAP FINAL 4H  |  RegimeRouter v1  |  SMA16/19+RSI+MFI+ATR+EMA filtre")
        print(f"{'#'*W}")
        hdr = (
            f"  {'Actif':<10} | {'Sh OOS':>6} | {'PF OOS':>6}"
            f" | {'DD OOS':>7} | {'Ratio':>5} | {'Consist':>7}"
            f" | {'Trades':>6} | {'ATR':>12} | Verdict"
        )
        print(hdr)
        print(f"  {'─'*(W-2)}")
        for r in results_4h:
            row = (
                f"  {r['asset']:<10} | {r['mean_sh']:>6.3f} | {r['mean_pf']:>6.2f}"
                f" | {r['mean_dd']:>6.1f}% | {r['mean_ratio']:>5.2f}"
                f" | {r['consistency']:>6.0f}%"
                f" | {r['total_trades']:>6} | {str(r['opt_atrs']):>12} | {r['verdict']}"
            )
            print(row)
        print(f"{'#'*W}")
