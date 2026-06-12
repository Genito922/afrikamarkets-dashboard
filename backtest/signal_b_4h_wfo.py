"""
Signal B 4H — WFO final
Signal  : SMA16/19 + RSI>50 + MFI>50 + double confirmation (2 bougies 4H = 8h)
Regime  : EMA200 Daily (BTC) / EMA246 Daily (SOL) forwardfillee sur 4H
          Shift(1) sur la colonne daily -> zero look-ahead garanti
OOS     : 1080 barres 4H = 180 jours
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
from backtest.audit_and_4h_wfo import (
    get_4h_folds, optimize_is_4h, run_backtest_with_trades,
)

# ─── Regime quotidien projete sur 4H ─────────────────────────────────────────

DAILY_REGIME = {
    "BTCUSDT": {"ema_span": 200, "bull_band": 1.05},
    "SOLUSDT": {"ema_span": 246, "bull_band": 0.95},
}


def attach_daily_regime(df_4h, df_daily, asset_name):
    """
    Calcule la EMA du jour D sur les closes daily,
    decale d'un jour (shift 1) pour eviter le look-ahead,
    puis forward-fill sur l'index 4H.
    """
    cfg = DAILY_REGIME[asset_name]
    d   = df_daily.copy()

    col = f"ema{cfg['ema_span']}_d"
    d[col]   = d["close"].ewm(span=cfg["ema_span"], adjust=False).mean()
    d[col]   = d[col].shift(1)          # utilise la valeur de J-1 pour J
    d["regime_allowed_d"] = (d["close"].shift(1) > d[col] * cfg["bull_band"]).astype(int)

    # Aligne sur l'index 4H en forward-fill (dernier regime daily connu)
    regime_4h = d["regime_allowed_d"].reindex(df_4h.index, method="ffill").fillna(0)
    return regime_4h.astype(int)


# ─── Construction du Signal B 4H ─────────────────────────────────────────────

def build_signal_b_4h(df_4h, df_daily, asset_name):
    """
    Applique sur les bougies 4H :
      - SMA16/19 double confirmation (bougie N ET N-1)
      - RSI14 > 50  (N ET N-1)
      - MFI14 > 50  (N ET N-1)
      - Filtre regime daily forwardfill
    """
    df = df_4h.copy()

    df["s16"]   = df["close"].rolling(16).mean()
    df["s19"]   = df["close"].rolling(19).mean()
    df["rsi14"] = rsi(df["close"], 14)
    df["mfi14"] = mfi(df, 14)
    df.dropna(inplace=True)

    # Regime daily projete
    df["regime_allowed"] = attach_daily_regime(df, df_daily, asset_name)

    # Signal brut a cette bougie
    cond_now  = (df.s16 > df.s19) & (df.rsi14 > 50) & (df.mfi14 > 50)
    # Meme condition sur la bougie precedente (J-1 en 4H = 4h avant)
    cond_prev = (
        (df.s16.shift(1) > df.s19.shift(1)) &
        (df.rsi14.shift(1) > 50) &
        (df.mfi14.shift(1) > 50)
    )

    df["signal"] = np.where(
        cond_now & cond_prev & (df["regime_allowed"] == 1), 1, 0
    )
    return df


# ─── WFO 4H Signal B ─────────────────────────────────────────────────────────

def run_signal_b_4h_wfo(df_4h, df_daily, asset_name,
                         n_folds=3, oos_bars=1080):
    df_sig = build_signal_b_4h(df_4h, df_daily, asset_name)
    folds  = get_4h_folds(df_sig, n_folds=n_folds, oos_bars=oos_bars)

    pct_raw    = ((df_sig.s16 > df_sig.s19) & (df_sig.rsi14 > 50) & (df_sig.mfi14 > 50)).mean() * 100
    pct_sig    = df_sig["signal"].mean() * 100
    pct_regime = df_sig["regime_allowed"].mean() * 100
    oos_days   = oos_bars // 6
    cfg        = DAILY_REGIME[asset_name]

    W = 112
    print(f"\n{'='*W}")
    print(
        f"  SIGNAL B 4H WFO -- {asset_name}"
        f"   ({len(df_sig)} barres 4H = {len(df_sig)//6}j"
        f" | EMA{cfg['ema_span']}d shift-1 x{cfg['bull_band']}"
        f" | OOS={oos_bars}b={oos_days}j | {n_folds} folds)"
    )
    print(f"{'='*W}")
    print(
        f"  Regime Daily actif : {pct_regime:.1f}%  |"
        f"  Signal brut 4H : {pct_raw:.1f}%  -->"
        f"  Signal B filtre : {pct_sig:.1f}%"
        f"  (reduction : {pct_raw - pct_sig:.1f}pts)"
    )
    print(f"{'─'*W}")

    if not folds:
        print(f"  [SKIP] historique insuffisant pour {n_folds} folds x {oos_bars} barres")
        print(f"{'='*W}")
        return None

    hdr = (
        f"  {'Fold':>4} | {'Periode OOS':>23}"
        f" | {'IS bars':>8} | {'OOS bars':>8}"
        f" | {'ATR':>5} | {'IS Sh':>6}"
        f" | {'OOS Sh':>6} | {'PF':>5}"
        f" | {'DD':>7} | {'Tr':>4}"
        f" | {'WR':>5} | {'AvgTr':>6} | {'Ratio':>5}"
    )
    print(hdr)
    print(f"  {'─'*108}")

    oos_sharpes, oos_pfs, oos_dds = [], [], []
    ratios, all_trades, opt_atrs   = [], [], []
    all_trade_rows                 = []

    for idx, (df_is, df_oos) in enumerate(folds):
        s_oos = df_oos.index[0].strftime("%Y-%m-%d")
        e_oos = df_oos.index[-1].strftime("%Y-%m-%d")

        best_atr, sh_is = optimize_is_4h(df_is)
        opt_atrs.append(best_atr)

        # Warm-up ATR Wilder : 28 jours * 6 bougies = 168 barres
        warmup   = df_is.iloc[-168:]
        df_warm  = pd.concat([warmup, df_oos])
        df_r, _  = run_strict_backtest(df_warm, atr_multiplier=best_atr)
        df_oos_r = df_r.iloc[len(warmup):].copy()

        _, tr_list  = run_strict_backtest(df_oos, atr_multiplier=best_atr)
        _, trade_df = run_backtest_with_trades(df_oos, atr_multiplier=best_atr)
        k = compute_metrics(df_oos_r, tr_list)

        ratio = round(k["sharpe"] / sh_is, 2) if sh_is > 0 else 0.0
        oos_sharpes.append(k["sharpe"])
        oos_pfs.append(k["pf"])
        oos_dds.append(k["maxdd"])
        ratios.append(ratio)
        all_trades.append(k["trades"])

        if not trade_df.empty:
            trade_df["fold"] = idx + 1
            all_trade_rows.append(trade_df)

        tag = " [PROD]" if k["sharpe"] >= 0.7 and k["pf"] >= 1.25 else \
              " [GO]  " if k["sharpe"] >= 0.5 and k["pf"] >= 1.15 else \
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

    print(f"  {'─'*108}")

    mean_sh    = round(float(np.mean(oos_sharpes)), 3)
    mean_pf    = round(float(np.mean(oos_pfs)), 2)
    mean_dd    = round(float(np.mean(oos_dds)), 1)
    mean_ratio = round(float(np.mean(ratios)), 2)
    total_t    = sum(all_trades)
    consist    = sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes) * 100
    drift_str  = f"stable ({opt_atrs[0]})" if len(set(opt_atrs)) == 1 else f"derive {opt_atrs}"

    # PF global sur tous les trades OOS combines
    if all_trade_rows:
        all_tr = pd.concat(all_trade_rows, ignore_index=True)
        wins   = all_tr[all_tr["result"] == "WIN"]["pnl_net"]
        losses = all_tr[all_tr["result"] == "LOSS"]["pnl_net"].abs()
        pf_g   = round(float(wins.sum() / losses.sum()), 3) if losses.sum() > 0 else 99.0
        avg_win  = round(float(wins.mean()), 2) if len(wins) > 0 else 0.0
        avg_loss = round(float(losses.mean()), 2) if len(losses) > 0 else 0.0
        wr_g   = round(len(wins) / len(all_tr) * 100, 1)
    else:
        pf_g = avg_win = avg_loss = wr_g = 0.0

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
    print(f"  PF GLOBAL (tous trades OOS) : {pf_g:.3f}"
          f"   WR global : {wr_g:.1f}%"
          f"   Avg WIN : +{avg_win:.2f}%   Avg LOSS : -{avg_loss:.2f}%")
    print(f"  Consistance OOS Sharpe > 0  : {consist:.0f}%")
    print(f"  Ratio robustesse OOS/IS     : {mean_ratio:.2f}  (seuil >= 0.50)")
    print(f"  Derive ATR                  : {drift_str}")

    is_prod = mean_sh >= 0.7 and pf_g >= 1.2 and mean_dd > -30 and mean_ratio >= 0.4
    is_go   = mean_sh >= 0.4 and pf_g >= 1.1 and mean_ratio >= 0.25
    is_pos  = mean_sh > 0 and pf_g >= 1.0 and consist >= 33
    verdict = (
        "[PROD] Paper Trading valide -- deployer en live monitor"  if is_prod else
        "[GO]   Edge confirme        -- paper trading 60 jours"    if is_go   else
        "[+]    Edge faible positif  -- continuer observation"     if is_pos  else
        "[SKIP] Pas d'edge           -- ne pas deployer"
    )
    print(f"\n  VERDICT : {verdict}")
    print(f"{'='*W}")

    return dict(
        asset=asset_name, mean_sh=mean_sh, mean_pf=mean_pf,
        mean_dd=mean_dd, mean_ratio=mean_ratio, consist=consist,
        total_trades=total_t, pf_global=pf_g, wr_global=wr_g,
        avg_win=avg_win, avg_loss=avg_loss,
        drift=drift_str, opt_atrs=opt_atrs, verdict=verdict,
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("\nChargement des donnees (Daily + 4H)...")
    btc_d = load_binance("BTCUSDT", days=1095, interval="1d")
    sol_d = load_binance("SOLUSDT", days=1095, interval="1d")
    btc_4 = load_binance("BTCUSDT", days=1095, interval="4h")
    sol_4 = load_binance("SOLUSDT", days=1095, interval="4h")

    print(f"  BTC : {len(btc_d)} barres daily  |  {len(btc_4)} barres 4H")
    print(f"  SOL : {len(sol_d)} barres daily  |  {len(sol_4)} barres 4H")

    results = []
    for name, df4, dfd in [("BTCUSDT", btc_4, btc_d), ("SOLUSDT", sol_4, sol_d)]:
        r = run_signal_b_4h_wfo(df4, dfd, name, n_folds=3, oos_bars=1080)
        if r:
            results.append(r)

    # ─── Recap final ──────────────────────────────────────────────────────────
    if results:
        W = 112
        print(f"\n\n{'#'*W}")
        print(f"  RECAP FINAL  |  Signal B 4H  |  SMA16/19 double confirm + EMA Daily regime")
        print(f"{'#'*W}")
        hdr = (
            f"  {'Actif':<10} | {'Sh OOS':>6} | {'PF glob':>7}"
            f" | {'WR glob':>7} | {'Avg WIN':>7} | {'Avg LOSS':>8}"
            f" | {'DD OOS':>7} | {'Trades':>6} | {'Ratio':>5} | {'ATR':>12} | Verdict"
        )
        print(hdr)
        print(f"  {'─'*(W-2)}")
        for r in results:
            row = (
                f"  {r['asset']:<10} | {r['mean_sh']:>6.3f} | {r['pf_global']:>7.3f}"
                f" | {r['wr_global']:>6.1f}% | {r['avg_win']:>+6.2f}% | -{r['avg_loss']:>6.2f}%"
                f" | {r['mean_dd']:>6.1f}% | {r['total_trades']:>6}"
                f" | {r['mean_ratio']:>5.2f} | {str(r['opt_atrs']):>12} | {r['verdict']}"
            )
            print(row)

        # Comparaison avec baseline
        print(f"\n  PROGRESSION vs baseline daily SMA16/19 sans confirmation")
        print(f"  {'─'*70}")
        baseline = {"BTCUSDT": (0.896, -0.322), "SOLUSDT": (0.855, -0.124)}
        for r in results:
            base_pf, base_sh = baseline.get(r["asset"], (0, 0))
            print(
                f"  {r['asset']:<10}  PF:  {base_pf:.3f} --> {r['pf_global']:.3f}"
                f"  ({r['pf_global'] - base_pf:>+.3f})"
                f"    Sharpe: {base_sh:>+.3f} --> {r['mean_sh']:>+.3f}"
                f"  ({r['mean_sh'] - base_sh:>+.3f})"
            )
        print(f"{'#'*W}")
