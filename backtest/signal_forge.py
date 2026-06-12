"""
Signal Forge — Refonte du moteur d'entree
Teste 4 variantes de signal vs baseline SMA16/19 :
  A : SMA20/50   (gap 30p — anti-whipsaw structurel)
  B : SMA16/19 + confirmation J-1  (2 closes consec.)
  C : SMA20/50  + confirmation J-1  (A + B combines)
  D : SMA30/60   (gap max, structure institutionnelle)

Pipeline complet par variante :
  1. Matrice ATR [1.5-3.5] sur 3 ans full sample
  2. WFO 3 folds ancres, OOS 180j, filtre regime EMA200/246
  3. Audit PF sur trades OOS
"""
import os, sys, warnings
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")

from backtest.wfo_engine import (
    load_binance, run_strict_backtest, compute_metrics,
    wilder_atr, rsi, mfi, MULTIPLIERS,
)
from backtest.regime_wfo import apply_regime_filter, get_regime_folds
from backtest.audit_and_4h_wfo import run_backtest_with_trades


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_signal_variant(df_raw, fast, slow, confirm=False,
                         rsi_th=50, mfi_th=50):
    """
    Construit le signal Long-only avec :
      fast, slow  : periodes des deux SMA
      confirm     : exige 2 closes consecutives en position (anti-whipsaw)
      rsi_th      : seuil RSI (50 standard)
      mfi_th      : seuil MFI (50 standard)
    """
    df = df_raw.copy()
    df[f"sma{fast}"]  = df["close"].rolling(fast).mean()
    df[f"sma{slow}"]  = df["close"].rolling(slow).mean()
    df["rsi14"]       = rsi(df["close"], 14)
    df["mfi14"]       = mfi(df, 14)
    df.dropna(inplace=True)

    sma_cross = df[f"sma{fast}"] > df[f"sma{slow}"]
    mom_ok    = (df["rsi14"] > rsi_th) & (df["mfi14"] > mfi_th)

    if confirm:
        # Signal actif seulement si croisement ET croisement J-1 aussi valide
        sma_prev = sma_cross.shift(1).fillna(False)
        df["signal"] = np.where(sma_cross & sma_prev & mom_ok, 1, 0)
    else:
        df["signal"] = np.where(sma_cross & mom_ok, 1, 0)

    return df


VARIANTS = {
    "SMA16/19 (baseline)":   dict(fast=16,  slow=19,  confirm=False),
    "SMA20/50 (A)":          dict(fast=20,  slow=50,  confirm=False),
    "SMA16/19+confirm (B)":  dict(fast=16,  slow=19,  confirm=True),
    "SMA20/50+confirm (C)":  dict(fast=20,  slow=50,  confirm=True),
    "SMA30/60 (D)":          dict(fast=30,  slow=60,  confirm=False),
}


# ═══════════════════════════════════════════════════════════════════════════════
# ETAPE 1 — MATRICE ATR FULL-SAMPLE (sanity check)
# ═══════════════════════════════════════════════════════════════════════════════

def run_atr_matrix(df_raw, asset_name, variant_name, fast, slow, confirm):
    df = build_signal_variant(df_raw, fast, slow, confirm)
    df = apply_regime_filter(df, asset_name)

    results = []
    for m in MULTIPLIERS:
        df_r, tr = run_strict_backtest(df, atr_multiplier=m)
        k = compute_metrics(df_r, tr)
        results.append((m, k))
    return results


def print_atr_matrix_table(asset_name, all_variant_results):
    W = 100
    print(f"\n{'='*W}")
    print(f"  MATRICE ATR FULL-SAMPLE — {asset_name}  (filtre regime actif)")
    print(f"{'='*W}")
    print(f"  {'Variante':<24} {'ATR':>4} | {'Sharpe':>6} {'PF':>5} {'DD':>7} {'Tr':>4} {'WR':>5} {'CAGR':>6} | B&H")
    print(f"  {'─'*95}")

    for vname, variant_results in all_variant_results:
        bh_shown = False
        for m, k in variant_results:
            tag = " [GO]  " if k["sharpe"] >= 0.5 and k["pf"] >= 1.2 else "       "
            bh_str = f"{k['bh']:>+6.1f}%" if not bh_shown else "       "
            bh_shown = True
            print(
                f"  {vname if m == MULTIPLIERS[0] else '':24} {m:>4} | "
                f"{k['sharpe']:>6.3f} {k['pf']:>5.2f} {k['maxdd']:>6.1f}% "
                f"{k['trades']:>4} {k['wr']:>4.0f}% {k['cagr']:>+5.1f}% | "
                f"{bh_str}{tag}"
            )
        print(f"  {'─'*95}")


# ═══════════════════════════════════════════════════════════════════════════════
# ETAPE 2 — WFO PAR VARIANTE
# ═══════════════════════════════════════════════════════════════════════════════

def optimize_is_variant(df_is):
    best_m  = 2.5
    best_sh = -np.inf
    for m in MULTIPLIERS:
        df_r, tr = run_strict_backtest(df_is, atr_multiplier=m)
        k = compute_metrics(df_r, tr)
        if k["pf"] >= 1.1 and k["trades"] >= 5 and k["sharpe"] > best_sh:
            best_sh = k["sharpe"]
            best_m  = m
    return best_m, round(best_sh, 3)


def run_wfo_variant(df_raw, asset_name, variant_name,
                    fast, slow, confirm, n_folds=3, oos_days=180):
    df     = build_signal_variant(df_raw, fast, slow, confirm)
    df_f   = apply_regime_filter(df, asset_name)
    folds  = get_regime_folds(df_f, n_folds=n_folds, oos_days=oos_days)

    if not folds:
        return None

    pct_sig = df_f["signal"].mean() * 100
    oos_sharpes, oos_pfs, oos_dds, ratios, all_trades = [], [], [], [], []
    opt_atrs, all_trade_rows = [], []

    for idx, (df_is, df_oos) in enumerate(folds):
        best_atr, sh_is = optimize_is_variant(df_is)
        opt_atrs.append(best_atr)

        warmup   = df_is.iloc[-28:]
        df_warm  = pd.concat([warmup, df_oos])
        df_r, _  = run_strict_backtest(df_warm, atr_multiplier=best_atr)
        df_oos_r = df_r.iloc[len(warmup):].copy()

        _, tr_df = run_backtest_with_trades(df_oos, atr_multiplier=best_atr)
        _, tr_list = run_strict_backtest(df_oos, atr_multiplier=best_atr)
        k = compute_metrics(df_oos_r, tr_list)

        ratio = round(k["sharpe"] / sh_is, 2) if sh_is > 0 else 0.0
        oos_sharpes.append(k["sharpe"])
        oos_pfs.append(k["pf"])
        oos_dds.append(k["maxdd"])
        ratios.append(ratio)
        all_trades.append(k["trades"])
        if not tr_df.empty:
            tr_df["fold"] = idx + 1
            all_trade_rows.append(tr_df)

    mean_sh    = round(float(np.mean(oos_sharpes)), 3)
    mean_pf    = round(float(np.mean(oos_pfs)), 2)
    mean_dd    = round(float(np.mean(oos_dds)), 1)
    mean_ratio = round(float(np.mean(ratios)), 2)
    total_t    = sum(all_trades)
    consist    = sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes) * 100
    drift_ok   = len(set(opt_atrs)) == 1

    # PF global sur tous les trades OOS
    if all_trade_rows:
        all_tr_df = pd.concat(all_trade_rows, ignore_index=True)
        wins_pnl  = all_tr_df[all_tr_df["result"] == "WIN"]["pnl_net"]
        loss_pnl  = all_tr_df[all_tr_df["result"] == "LOSS"]["pnl_net"].abs()
        oos_pf_global = (wins_pnl.sum() / loss_pnl.sum()
                         if loss_pnl.sum() > 0 else 99.0)
        oos_pf_global = round(float(oos_pf_global), 3)
    else:
        oos_pf_global = 0.0

    return dict(
        asset=asset_name, variant=variant_name,
        fast=fast, slow=slow, confirm=confirm,
        mean_sh=mean_sh, mean_pf=mean_pf, mean_dd=mean_dd,
        mean_ratio=mean_ratio, consist=consist, total_trades=total_t,
        oos_pf_global=oos_pf_global, opt_atrs=opt_atrs,
        drift_ok=drift_ok, pct_sig=round(pct_sig, 1),
        oos_sharpes=oos_sharpes,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ETAPE 3 — TABLEAU COMPARATIF
# ═══════════════════════════════════════════════════════════════════════════════

def print_comparison(results):
    W = 112
    print(f"\n\n{'#'*W}")
    print(f"  COMPARATIF WFO OOS — Toutes variantes  (filtre regime + OOS 180j)")
    print(f"{'#'*W}")
    hdr = (
        f"  {'Actif':<8} {'Variante':<22} {'Sig%':>5}"
        f" | {'Sh OOS':>6} {'PF OOS':>6} {'PF Glob':>7}"
        f" | {'DD OOS':>7} {'Trades':>6}"
        f" | {'Consist':>7} {'Ratio':>5} {'Drift':>5}"
        f" | Verdict"
    )
    print(hdr)
    print(f"  {'─'*(W-2)}")

    baseline_sh = {}
    for r in results:
        if "baseline" in r["variant"]:
            baseline_sh[r["asset"]] = r["mean_sh"]

    for r in results:
        is_prod = (r["mean_sh"] >= 0.5 and r["oos_pf_global"] >= 1.2
                   and r["mean_dd"] > -30 and r["mean_ratio"] >= 0.35)
        is_pos  = r["mean_sh"] > 0 and r["oos_pf_global"] >= 1.0
        verdict = (
            "[GO]  " if is_prod else
            "[+]   " if is_pos  else
            "[--]  "
        )

        base_sh = baseline_sh.get(r["asset"], 0)
        delta   = r["mean_sh"] - base_sh
        delta_s = f"{delta:>+.3f}" if "baseline" not in r["variant"] else "  ref "

        drift_s = "OK " if r["drift_ok"] else "!  "
        sep = "  <-- MEILLEUR" if is_prod else ""

        row = (
            f"  {r['asset']:<8} {r['variant']:<22} {r['pct_sig']:>4.1f}%"
            f" | {r['mean_sh']:>6.3f} {r['mean_pf']:>6.2f} {r['oos_pf_global']:>7.3f}"
            f" | {r['mean_dd']:>6.1f}% {r['total_trades']:>6}"
            f" | {r['consist']:>6.0f}% {r['mean_ratio']:>5.2f} {drift_s:>5}"
            f" | {verdict} (delta:{delta_s}){sep}"
        )
        print(row)
        if r["variant"] == list(VARIANTS.keys())[-1] or \
           results[results.index(r)+1]["asset"] != r["asset"] \
           if results.index(r) < len(results)-1 else True:
            pass

    print(f"{'#'*W}")
    print(f"\n  LEGENDE")
    print(f"  PF OOS   = moyenne des PF par fold  (peut etre distordu par peu de trades)")
    print(f"  PF Glob  = PF calcule sur tous les trades OOS combines  (metrique cle)")
    print(f"  [GO]   = Sh>=0.5 ET PF Glob>=1.2 ET DD>-30% ET Ratio>=0.35")
    print(f"  [+]    = Sh>0 ET PF Glob>=1.0  (edge faible mais positif)")
    print(f"  [--]   = pas d'edge detectable")
    print(f"{'#'*W}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    print("\nChargement donnees daily BTC + SOL...")
    df_btc = load_binance("BTCUSDT", days=1095)
    df_sol = load_binance("SOLUSDT", days=1095)
    print(f"  BTC: {len(df_btc)} barres  |  SOL: {len(df_sol)} barres")

    ASSETS = [("BTCUSDT", df_btc), ("SOLUSDT", df_sol)]

    # ── Etape 1 : Matrice ATR full-sample par variante ────────────────────────
    for asset_name, df_raw in ASSETS:
        all_var_res = []
        for vname, vcfg in VARIANTS.items():
            res = run_atr_matrix(df_raw, asset_name, vname, **vcfg)
            all_var_res.append((vname, res))
        print_atr_matrix_table(asset_name, all_var_res)

    # ── Etape 2 : WFO 3 folds OOS 180j par variante ──────────────────────────
    print(f"\n\n{'='*80}")
    print(f"  LANCEMENT WFO PAR VARIANTE  (3 folds x 180j OOS, filtre regime)")
    print(f"{'='*80}")

    all_results = []
    for asset_name, df_raw in ASSETS:
        print(f"\n  -- {asset_name} --")
        for vname, vcfg in VARIANTS.items():
            print(f"     {vname}...", end="", flush=True)
            r = run_wfo_variant(df_raw, asset_name, vname, **vcfg)
            if r:
                all_results.append(r)
                print(f"  Sh={r['mean_sh']:>+.3f}  PF_glob={r['oos_pf_global']:.3f}  Tr={r['total_trades']}")
            else:
                print("  skip")

    # ── Etape 3 : Tableau comparatif ─────────────────────────────────────────
    if all_results:
        print_comparison(all_results)
