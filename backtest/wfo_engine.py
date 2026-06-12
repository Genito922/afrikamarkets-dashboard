"""
WFO Engine — Walk-Forward Optimization institutionnel
SMA16/19 + RSI>50 + MFI>50 + ATR Trailing Stop (Wilder)
Entree/Sortie stricte a l'Open de la barre N+1 (zero look-ahead)
"""
import os, sys, warnings
import numpy as np
import pandas as pd
import yfinance as yf
from binance.client import Client
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")

client = Client(
    os.environ.get("BINANCE_API_KEY", ""),
    os.environ.get("BINANCE_SECRET_KEY", ""),
)

# ─── Data Loaders ────────────────────────────────────────────────────────────

def load_binance(symbol, days=1095, interval="1d"):
    bars, end = [], datetime.utcnow()
    start = end - timedelta(days=days)
    # Fenetre de fetch : 60j pour daily, 10j pour 4H (evite la limite de 1000 barres)
    fetch_window = timedelta(days=60) if interval == "1d" else timedelta(days=10)
    while start < end:
        b = client.futures_historical_klines(
            symbol=symbol, interval=interval,
            start_str=str(start),
            end_str=str(min(start + fetch_window, end)),
            limit=1000,
        )
        if not b:
            break
        bars += b
        start = min(start + fetch_window, end)
    df = pd.DataFrame(bars, columns=[
        "ts", "open", "high", "low", "close", "volume",
        "ct", "qv", "trades", "tbb", "tbq", "ignore",
    ]).drop_duplicates("ts")
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c])
    return df.set_index("ts").sort_index()[["open", "high", "low", "close", "volume"]]


def load_yfinance(ticker, days=1095):
    start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    df = yf.download(ticker, start=start, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df.index.name = "ts"
    return df[["open", "high", "low", "close", "volume"]].dropna()


# ─── Indicators ──────────────────────────────────────────────────────────────

def rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    return 100 - (100 / (1 + gain / loss.replace(0, np.nan)))


def mfi(df, period=14):
    tp  = (df["high"] + df["low"] + df["close"]) / 3
    mf  = tp * df["volume"]
    pos = mf.where(tp.diff() > 0, 0).rolling(period).sum()
    neg = mf.where(tp.diff() < 0, 0).rolling(period).sum()
    return 100 - (100 / (1 + pos / neg.replace(0, np.nan)))


def wilder_atr(df, period=14):
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift(1)).abs()
    lc = (df["low"]  - df["close"].shift(1)).abs()
    return (
        pd.concat([hl, hc, lc], axis=1)
        .max(axis=1)
        .ewm(alpha=1 / period, adjust=False)
        .mean()
    )


def build_signal(df):
    df = df.copy()
    df["s16"]   = df["close"].rolling(16).mean()
    df["s19"]   = df["close"].rolling(19).mean()
    df["rsi14"] = rsi(df["close"], 14)
    df["mfi14"] = mfi(df, 14)
    df.dropna(inplace=True)
    df["signal"] = np.where(
        (df.s16 > df.s19) & (df.rsi14 > 50) & (df.mfi14 > 50), 1, 0
    )
    return df


# ─── Strict Backtest Engine ──────────────────────────────────────────────────

def run_strict_backtest(df_input, atr_multiplier=2.5, fee=0.0004):
    df = df_input.copy()
    df["atr14"] = wilder_atr(df)

    closes  = df["close"].values
    opens   = df["open"].values
    atrs    = df["atr14"].values
    signals = df["signal"].values
    n = len(df)

    strat_returns = np.zeros(n)
    trade_rets    = []
    position = 0
    entry_price = highest = stop = 0.0
    exit_flag = False

    for i in range(1, n):
        if exit_flag:
            gross = (opens[i] - entry_price) / entry_price
            trade_rets.append(gross - 2 * fee)
            position = 0
            exit_flag = False
            continue

        if position == 1:
            highest = max(highest, closes[i])
            stop    = highest - atr_multiplier * atrs[i]
            if closes[i] < stop or signals[i] <= 0:
                exit_flag = True
            strat_returns[i] = closes[i] / closes[i - 1] - 1
        elif position == 0 and signals[i - 1] == 1:
            entry_price = opens[i] * (1 + fee)
            highest     = closes[i]
            stop        = highest - atr_multiplier * atrs[i]
            position    = 1

    df["strat_returns"] = strat_returns
    return df, trade_rets


def compute_metrics(df, trade_rets, capital=1000):
    rets  = df["strat_returns"].fillna(0)
    bh    = df["close"].pct_change().fillna(0)
    eq    = capital * (1 + rets).cumprod()
    bh_eq = capital * (1 + bh).cumprod()

    sharpe = (rets.mean() / rets.std() * np.sqrt(252)) if rets.std() > 0 else 0
    years  = max(len(df) / 365, 0.01)
    cagr   = ((eq.iloc[-1] / capital) ** (1 / years) - 1) * 100
    maxdd  = ((eq - eq.cummax()) / eq.cummax()).min() * 100
    pnl    = (eq.iloc[-1] / capital - 1) * 100
    bh_pnl = (bh_eq.iloc[-1] / capital - 1) * 100

    if not trade_rets:
        return dict(sharpe=0, pf=0, maxdd=maxdd, trades=0,
                    wr=0, avg_t=0, cagr=0, pnl=pnl, bh=bh_pnl)

    trades = np.array(trade_rets)
    wins   = trades[trades > 0]
    losses = trades[trades < 0]
    pf     = (wins.sum() / abs(losses.sum())) if losses.sum() != 0 else 99.0

    return dict(
        sharpe=round(sharpe, 3),
        pf    =round(pf, 2),
        maxdd =round(maxdd, 1),
        trades=len(trades),
        wr    =round(len(wins) / len(trades) * 100, 1) if trades.size else 0,
        avg_t =round(trades.mean() * 100, 3) if trades.size else 0,
        cagr  =round(cagr, 1),
        pnl   =round(pnl, 1),
        bh    =round(bh_pnl, 1),
    )


# ─── WFO Fold Generator  (fenetres glissantes ancrage fixe) ──────────────────

def get_wfo_folds(df, n_folds=3, is_ratio=0.7):
    """
    Ancrage fixe (anchored WFO) :
      - IS commence toujours en 0, grandit a chaque fold
      - OOS = fenetre fixe qui suit IS
    Cela evite le data snooping: chaque OOS est vu une seule fois.
    """
    total     = len(df)
    oos_size  = int(total * (1 - is_ratio) / n_folds)
    folds     = []
    for fold in range(n_folds):
        end_is  = int(total * is_ratio) + fold * oos_size
        end_oos = end_is + oos_size
        if end_oos > total:
            break
        folds.append((df.iloc[0:end_is], df.iloc[end_is:end_oos]))
    return folds


# ─── IS Optimizer ────────────────────────────────────────────────────────────

MULTIPLIERS = [1.5, 2.0, 2.5, 3.0, 3.5]


def optimize_is(df_is):
    best_m  = 2.5
    best_sh = -np.inf
    for m in MULTIPLIERS:
        df_r, tr = run_strict_backtest(df_is, atr_multiplier=m)
        k = compute_metrics(df_r, tr)
        if k["pf"] >= 1.2 and k["sharpe"] > best_sh:
            best_sh = k["sharpe"]
            best_m  = m
    return best_m, round(best_sh, 3)


# ─── WFO Runner ──────────────────────────────────────────────────────────────

W = 100

def run_wfo(df_full, asset_name, n_folds=3, is_ratio=0.7):
    folds = get_wfo_folds(df_full, n_folds=n_folds, is_ratio=is_ratio)
    if not folds:
        print(f"[SKIP] {asset_name} -- pas assez de barres pour {n_folds} folds")
        return None

    print("\n" + "=" * W)
    label = (
        f"  WALK-FORWARD -- {asset_name}"
        f"   ({len(df_full)} barres | {n_folds} folds ancres"
        f" | IS={int(is_ratio*100)}% / OOS={int((1-is_ratio)*100)}%)"
    )
    print(label)
    print("=" * W)
    hdr = (
        f"  {'Fold':>4} | {'Periode OOS':>23}"
        f" | {'IS bars':>7} | {'OOS bars':>8}"
        f" | {'Opt ATR':>7} | {'IS Sh':>6}"
        f" | {'OOS Sh':>6} | {'OOS PF':>6}"
        f" | {'OOS DD':>7} | {'Trades':>6} | {'Ratio':>5}"
    )
    print(hdr)
    print("  " + "-" * (W - 2))

    oos_sharpes, oos_pfs, oos_dds, ratios, all_trades = [], [], [], [], []
    opt_atrs = []

    for idx, (df_is, df_oos) in enumerate(folds):
        start_oos = df_oos.index[0].strftime("%Y-%m-%d")
        end_oos   = df_oos.index[-1].strftime("%Y-%m-%d")

        best_atr, sh_is = optimize_is(df_is)
        opt_atrs.append(best_atr)

        # Warm-up : 28 dernieres barres IS pour l'ATR de Wilder
        warmup   = df_is.iloc[-28:]
        df_warm  = pd.concat([warmup, df_oos])
        df_r, _  = run_strict_backtest(df_warm, atr_multiplier=best_atr)
        df_oos_r = df_r.iloc[len(warmup):].copy()

        # Trades OOS recalcules sur fenetre propre
        _, tr_oos = run_strict_backtest(df_oos, atr_multiplier=best_atr)
        k = compute_metrics(df_oos_r, tr_oos)

        ratio = round(k["sharpe"] / sh_is, 2) if sh_is > 0 else 0.0
        oos_sharpes.append(k["sharpe"])
        oos_pfs.append(k["pf"])
        oos_dds.append(k["maxdd"])
        ratios.append(ratio)
        all_trades.append(k["trades"])

        flag = " <-- GO" if k["sharpe"] >= 0.5 and k["pf"] >= 1.2 else ""
        line = (
            f"  {idx+1:>4} | {start_oos} -> {end_oos}"
            f" | {len(df_is):>7} | {len(df_oos):>8}"
            f" | {best_atr:>7} | {sh_is:>6.3f}"
            f" | {k['sharpe']:>6.3f} | {k['pf']:>6.2f}"
            f" | {k['maxdd']:>6.1f}% | {k['trades']:>6} | {ratio:>5.2f}{flag}"
        )
        print(line)

    print("  " + "-" * (W - 2))

    mean_sh    = round(float(np.mean(oos_sharpes)), 3)
    mean_pf    = round(float(np.mean(oos_pfs)), 2)
    mean_dd    = round(float(np.mean(oos_dds)), 1)
    mean_ratio = round(float(np.mean(ratios)), 2)
    total_t    = sum(all_trades)
    consistency = sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes) * 100

    # Derive des parametres
    unique_atrs = len(set(opt_atrs))
    drift_msg   = "stable" if unique_atrs == 1 else f"derive ({unique_atrs} valeurs: {opt_atrs})"

    synth = (
        f"  {'SYNTHESE':>4} | {'Moyenne OOS':>23}"
        f" | {' ':>7} | {' ':>8}"
        f" | {' ':>7} | {' ':>6}"
        f" | {mean_sh:>6.3f} | {mean_pf:>6.2f}"
        f" | {mean_dd:>6.1f}% | {total_t:>6} | {mean_ratio:>5.2f}"
    )
    print(synth)
    print()
    print(f"  Consistance (folds OOS Sharpe > 0) : {consistency:.0f}%")
    print(f"  Ratio robustesse moyen OOS/IS       : {mean_ratio:.2f}  (seuil: >= 0.50)")
    print(f"  Derive parametrique ATR             : {drift_msg}")

    is_prod = mean_sh >= 0.8 and mean_pf >= 1.3 and mean_dd > -30 and mean_ratio >= 0.5
    is_go   = mean_sh >= 0.5 and mean_pf >= 1.2 and mean_ratio >= 0.4
    verdict = (
        "[PROD] ROBUSTE -- Paper Trading valide"  if is_prod else
        "[GO]   Operationnel -- A surveiller en forward" if is_go else
        "[SKIP] Sur-optimisation probable -- Ne pas deployer"
    )
    print(f"\n  VERDICT : {verdict}")
    print("=" * W)

    return dict(
        asset=asset_name, mean_sh=mean_sh, mean_pf=mean_pf,
        mean_dd=mean_dd, mean_ratio=mean_ratio,
        consistency=consistency, drift=drift_msg, verdict=verdict,
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    assets = [
        ("BTCUSDT",   lambda: load_binance("BTCUSDT")),
        ("ETHUSDT",   lambda: load_binance("ETHUSDT")),
        ("SOLUSDT",   lambda: load_binance("SOLUSDT")),
        ("GC=F (Or)", lambda: load_yfinance("GC=F")),
    ]

    summary = []
    for name, loader in assets:
        try:
            df_raw = loader()
            if df_raw.empty or len(df_raw) < 100:
                print(f"\n[SKIP] {name} -- donnees insuffisantes ({len(df_raw)} barres)")
                continue
            df = build_signal(df_raw)
            r  = run_wfo(df, name, n_folds=3, is_ratio=0.7)
            if r:
                summary.append(r)
        except Exception as e:
            print(f"\n[ERROR] {name}: {e}")

    # ─── Recap final ──────────────────────────────────────────────────────────
    if summary:
        print("\n\n" + "#" * W)
        print("  RECAP GLOBAL WFO -- SMA16/19 + RSI>50 + MFI>50 + ATR Trailing Stop")
        print("#" * W)
        hdr2 = (
            f"  {'Actif':<14} | {'Sharpe OOS':>10} | {'PF OOS':>6}"
            f" | {'MaxDD OOS':>9} | {'Ratio':>5} | {'Consist.':>8} | {'Derive ATR':<20} | Verdict"
        )
        print(hdr2)
        print("  " + "-" * (W - 2))
        for r in summary:
            row = (
                f"  {r['asset']:<14} | {r['mean_sh']:>10.3f} | {r['mean_pf']:>6.2f}"
                f" | {r['mean_dd']:>8.1f}% | {r['mean_ratio']:>5.2f}"
                f" | {r['consistency']:>7.0f}% | {r['drift']:<20} | {r['verdict']}"
            )
            print(row)
        print("#" * W)
