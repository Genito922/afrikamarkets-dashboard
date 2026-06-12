"""
Backtest SMA Triple — multi-actifs
Metriques : CAGR, Sharpe, Max Drawdown, Win Rate, Profit Factor
Pagination Binance : jusqu'a 10 000 bougies par actif
"""
import os
import time
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from binance.client import Client

# ── Config ─────────────────────────────────────────────────────
SYMBOLS      = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "XAUUSDT"]
INTERVAL     = "30m"
DAYS_BACK    = 365 * 3  # 3 ans
SMA_S        = 16
SMA_M        = 246
SMA_L        = 361
LEVERAGE     = 1
CAPITAL_INIT = 1000
TAKER_FEE    = 0.0004
MAX_CANDLES  = 55_000   # 3 ans × 48 bougies/jour = ~52 560
PAGE_SIZE    = 1500     # limite max Binance par requete
WF_FOLDS     = 3        # walk-forward : nb de folds
WF_TRAIN_PCT = 0.70     # 70% train / 30% test par fold

API_KEY    = os.environ.get("BINANCE_API_KEY", "")
API_SECRET = os.environ.get("BINANCE_SECRET_KEY", "")

COLS = [
    "timestamp","open","high","low","close","volume",
    "close_time","quote_vol","trades",
    "taker_buy_base","taker_buy_quote","ignore"
]


# ── Download avec pagination ────────────────────────────────────
def _fetch_page(client, symbol: str, interval: str, start: datetime, limit: int) -> list:
    """Une page avec retry exponentiel sur erreur rate-limit ou reseau."""
    MAX_RETRIES = 6
    for attempt in range(MAX_RETRIES):
        try:
            return client.futures_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=str(start),
                limit=limit,
            )
        except Exception as e:
            code = getattr(e, "status_code", None) or getattr(e, "code", None)
            # -1003 = rate limit, 429/418 = IP ban temporaire
            if attempt == MAX_RETRIES - 1:
                raise
            wait = 2 ** attempt          # 1s, 2s, 4s, 8s, 16s, 32s
            if code in (-1003, 429, 418):
                wait = max(wait, 10)     # ban IP : attente minimum 10s
            print(f"\n    retry {attempt+1}/{MAX_RETRIES} ({wait}s) — {e}", flush=True)
            time.sleep(wait)
    return []


def download_data(symbol: str) -> pd.DataFrame:
    client = Client(API_KEY, API_SECRET, testnet=False)
    start_dt = datetime.utcnow() - timedelta(days=DAYS_BACK)
    all_bars = []
    current_start = start_dt
    page_num = 0

    print(f"  {symbol} : telechargement...", end="", flush=True)
    while len(all_bars) < MAX_CANDLES:
        bars = _fetch_page(client, symbol, INTERVAL, current_start, PAGE_SIZE)
        if not bars:
            break
        # deduplication immédiate pour éviter boucle infinie si même ts renvoyé
        if all_bars and bars[0][0] <= all_bars[-1][0]:
            bars = [b for b in bars if b[0] > all_bars[-1][0]]
            if not bars:
                break
        all_bars.extend(bars)
        page_num += 1
        last_ts = bars[-1][0]
        current_start = datetime.utcfromtimestamp(last_ts / 1000) + timedelta(seconds=1)
        if len(bars) < PAGE_SIZE:
            break
        # Progression toutes les 10 pages
        if page_num % 10 == 0:
            print(f" {len(all_bars):,}", end="", flush=True)
        time.sleep(0.2)   # ~5 req/s, safe sous la limite de 1200/min

    df = pd.DataFrame(all_bars, columns=COLS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df[~df.index.duplicated(keep="first")]
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col])
    print(f" => {len(df):,} bougies")
    return df


# ── Signaux ─────────────────────────────────────────────────────
def compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["sma_s"] = df["close"].rolling(SMA_S).mean()
    df["sma_m"] = df["close"].rolling(SMA_M).mean()
    df["sma_l"] = df["close"].rolling(SMA_L).mean()
    df.dropna(inplace=True)
    df["signal"] = 0
    df.loc[(df.sma_s > df.sma_m) & (df.sma_m > df.sma_l), "signal"] =  1
    df.loc[(df.sma_s < df.sma_m) & (df.sma_m < df.sma_l), "signal"] = -1
    df["position"] = df["signal"].shift(1).fillna(0)
    return df


# ── Backtest ────────────────────────────────────────────────────
def run_backtest(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["returns"]   = df["close"].pct_change()
    df["strat_ret"] = df["position"] * df["returns"] * LEVERAGE
    df["trade"]     = df["position"].diff().abs()
    df["fee_cost"]  = df["trade"] * TAKER_FEE
    df["net_ret"]   = df["strat_ret"] - df["fee_cost"]
    df["equity"]    = CAPITAL_INIT * (1 + df["net_ret"]).cumprod()
    df["buy_hold"]  = CAPITAL_INIT * (1 + df["returns"]).cumprod()
    return df


# ── Trade log entry→exit ─────────────────────────────────────────
def build_trade_log(df: pd.DataFrame) -> pd.DataFrame:
    trades = []
    in_pos = False
    entry_price = entry_date = side = 0
    for date, row in df.iterrows():
        p = row["position"]
        if not in_pos and p != 0:
            in_pos      = True
            entry_price = row["close"]
            entry_date  = date
            side        = p
        elif in_pos and p != side:
            exit_price = row["close"]
            raw_pnl    = (exit_price - entry_price) / entry_price * side
            net_pnl    = raw_pnl - 2 * TAKER_FEE
            trades.append({
                "entry_date":   entry_date,
                "exit_date":    date,
                "side":         "LONG" if side == 1 else "SHORT",
                "entry_price":  entry_price,
                "exit_price":   exit_price,
                "pnl_pct":      net_pnl,
                "hold_candles": (df.index.get_loc(date) - df.index.get_loc(entry_date)),
            })
            if p != 0:
                entry_price = row["close"]
                entry_date  = date
                side        = p
            else:
                in_pos = False
    return pd.DataFrame(trades)


# ── Metriques ───────────────────────────────────────────────────
def compute_metrics(df: pd.DataFrame):
    equity = df["equity"].dropna()

    # CAGR — duree reelle
    n_years = (equity.index[-1] - equity.index[0]).total_seconds() / (365.25 * 24 * 3600)
    n_years = max(n_years, 1 / 365)
    cagr    = (equity.iloc[-1] / CAPITAL_INIT) ** (1 / n_years) - 1

    # Sharpe — equity.pct_change() + annualisation auto-detectee
    eq_ret = equity.pct_change().dropna()
    if len(eq_ret) > 1 and eq_ret.std() > 0:
        median_sec       = pd.Series(equity.index.asi8).diff().median() / 1e9
        candles_per_year = (365.25 * 24 * 3600) / max(median_sec, 1)
        sharpe = (eq_ret.mean() / eq_ret.std()) * np.sqrt(candles_per_year)
    else:
        sharpe = 0

    # Max Drawdown
    rolling_max = equity.cummax()
    max_dd      = ((equity - rolling_max) / rolling_max).min()

    # Win Rate / Profit Factor — trades entry→exit reels
    trades_df = build_trade_log(df)
    nb        = len(trades_df)
    if nb > 0:
        pnls         = trades_df["pnl_pct"]
        win_rate     = (pnls > 0).mean()
        gross_profit = pnls[pnls > 0].sum()
        gross_loss   = abs(pnls[pnls < 0].sum())
        pf           = gross_profit / max(gross_loss, 1e-10)
        avg_hold     = trades_df["hold_candles"].mean()
    else:
        win_rate = pf = avg_hold = 0

    return {
        "capital_final":    round(equity.iloc[-1], 2),
        "pnl_pct":          round((equity.iloc[-1] / CAPITAL_INIT - 1) * 100, 2),
        "cagr_pct":         round(cagr * 100, 2),
        "sharpe":           round(sharpe, 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "win_rate_pct":     round(win_rate * 100, 2),
        "profit_factor":    round(pf, 3),
        "nb_trades":        nb,
        "avg_hold_candles": round(avg_hold, 1),
        "n_years_actual":   round(n_years, 4),
        "buy_hold_pct":     round((df["buy_hold"].iloc[-1] / CAPITAL_INIT - 1) * 100, 2),
    }, trades_df


# ── Graphique equity ────────────────────────────────────────────
def plot_single(df: pd.DataFrame, metrics: dict, symbol: str):
    fig, axes = plt.subplots(3, 1, figsize=(14, 9), facecolor="#0D0D1F")
    for ax in axes:
        ax.set_facecolor("#0D0D1F")
        ax.tick_params(colors="#9CA3AF")
        for sp in ax.spines.values():
            sp.set_color("#374151")

    fig.suptitle(
        f"{symbol}  SMA {SMA_S}/{SMA_M}/{SMA_L}  |  "
        f"PnL: {metrics['pnl_pct']:+.1f}%  "
        f"Sharpe: {metrics['sharpe']:.2f}  "
        f"MaxDD: {metrics['max_drawdown_pct']:.1f}%  "
        f"PF: {metrics['profit_factor']:.2f}  "
        f"Trades: {metrics['nb_trades']}",
        fontsize=11, color="white"
    )

    axes[0].plot(df.index, df["equity"],   label="SMA", color="#C9A84C", lw=1.4)
    axes[0].plot(df.index, df["buy_hold"], label="B&H", color="#3B82F6", lw=1, alpha=0.7)
    axes[0].axhline(CAPITAL_INIT, color="#4B5563", lw=0.7, linestyle="--")
    axes[0].set_ylabel("Capital ($)", color="#9CA3AF")
    axes[0].legend(facecolor="#1F2937", labelcolor="white", fontsize=9)
    axes[0].grid(alpha=0.15, color="#374151")

    rolling_max = df["equity"].cummax()
    dd = (df["equity"] - rolling_max) / rolling_max * 100
    axes[1].fill_between(df.index, dd, 0, color="#EF4444", alpha=0.55)
    axes[1].set_ylabel("Drawdown (%)", color="#9CA3AF")
    axes[1].grid(alpha=0.15, color="#374151")

    axes[2].fill_between(df.index, df["position"], 0,
        where=df["position"] > 0, color="#22C55E", alpha=0.6, label="LONG")
    axes[2].fill_between(df.index, df["position"], 0,
        where=df["position"] < 0, color="#EF4444", alpha=0.6, label="SHORT")
    axes[2].set_ylabel("Position", color="#9CA3AF")
    axes[2].legend(facecolor="#1F2937", labelcolor="white", fontsize=9)
    axes[2].grid(alpha=0.15, color="#374151")

    plt.tight_layout()
    fname = f"backtest/results_{symbol}.png"
    plt.savefig(fname, dpi=130, facecolor="#0D0D1F")
    plt.close()
    print(f"  Graphique : {fname}")


# ── Walk-forward validation ─────────────────────────────────────
def walk_forward(df: pd.DataFrame, symbol: str) -> list:
    """
    Coupe df en WF_FOLDS folds glissants.
    Chaque fold : train (70%) suivi de test (30%) sans overlap.
    Retourne la liste des metriques OOS (out-of-sample).
    """
    n      = len(df)
    fold_sz = n // WF_FOLDS
    folds  = []

    for i in range(WF_FOLDS):
        start = i * fold_sz
        end   = start + fold_sz if i < WF_FOLDS - 1 else n
        chunk = df.iloc[start:end].copy()
        split = int(len(chunk) * WF_TRAIN_PCT)

        train = chunk.iloc[:split]
        test  = chunk.iloc[split:]

        if len(test) < SMA_L + 20:
            continue

        # IS (in-sample)
        train_bt      = run_backtest(train)
        m_is, _       = compute_metrics(train_bt)

        # OOS (out-of-sample)
        test_bt       = run_backtest(test)
        m_oos, tlog   = compute_metrics(test_bt)

        # ratio OOS/IS Sharpe : < 0.5 = overfit signal
        ratio = (m_oos["sharpe"] / m_is["sharpe"]) if m_is["sharpe"] != 0 else 0

        folds.append({
            "fold":        i + 1,
            "is_start":    train.index[0].strftime("%Y-%m"),
            "is_end":      train.index[-1].strftime("%Y-%m"),
            "oos_start":   test.index[0].strftime("%Y-%m"),
            "oos_end":     test.index[-1].strftime("%Y-%m"),
            "is_sharpe":   m_is["sharpe"],
            "oos_sharpe":  m_oos["sharpe"],
            "oos_pnl":     m_oos["pnl_pct"],
            "oos_pf":      m_oos["profit_factor"],
            "oos_dd":      m_oos["max_drawdown_pct"],
            "oos_trades":  m_oos["nb_trades"],
            "oos_wr":      m_oos["win_rate_pct"],
            "oos_is_ratio": round(ratio, 3),
        })

    return folds


def print_walkforward(folds: list, symbol: str):
    if not folds:
        print("  Walk-forward : donnees insuffisantes")
        return

    print(f"\n  WALK-FORWARD {symbol} ({WF_FOLDS} folds, train {int(WF_TRAIN_PCT*100)}% / test {int((1-WF_TRAIN_PCT)*100)}%)")
    hdr = f"  {'Fold':>4}  {'IS':>13}  {'OOS':>13}  {'IS Sh':>7}  {'OOS Sh':>7}  {'OOS PnL':>8}  {'PF':>6}  {'DD%':>6}  {'Trades':>7}  {'Ratio':>7}"
    print(hdr)
    print("  " + "-" * 90)
    for f in folds:
        flag = " OVERFIT" if f["oos_is_ratio"] < 0.5 and f["is_sharpe"] > 0.5 else ""
        print(
            f"  {f['fold']:>4}  "
            f"{f['is_start']}→{f['is_end']}  "
            f"{f['oos_start']}→{f['oos_end']}  "
            f"{f['is_sharpe']:>7.3f}  "
            f"{f['oos_sharpe']:>7.3f}  "
            f"{f['oos_pnl']:>+8.1f}%  "
            f"{f['oos_pf']:>6.3f}  "
            f"{f['oos_dd']:>6.1f}  "
            f"{f['oos_trades']:>7}  "
            f"{f['oos_is_ratio']:>7.3f}"
            f"{flag}"
        )

    avg_oos_sharpe = np.mean([f["oos_sharpe"] for f in folds])
    avg_oos_pf     = np.mean([f["oos_pf"]     for f in folds])
    overfit_count  = sum(1 for f in folds if f["oos_is_ratio"] < 0.5 and f["is_sharpe"] > 0.5)
    print(f"\n  Moyenne OOS  Sharpe: {avg_oos_sharpe:.3f} | PF: {avg_oos_pf:.3f} | Overfits: {overfit_count}/{len(folds)}")

    if avg_oos_sharpe > 0.8 and avg_oos_pf > 1.3 and overfit_count == 0:
        print("  VERDICT : strategie robuste — candidat paper trading")
    elif avg_oos_sharpe > 0.5 and avg_oos_pf > 1.1:
        print("  VERDICT : edge faible — continuer validation avant paper trading")
    else:
        print("  VERDICT : pas d'edge OOS confirme — ne pas deployer")


# ── Tableau comparatif final ────────────────────────────────────
def print_summary(results: list):
    cols = ["symbol","pnl_pct","cagr_pct","sharpe","max_drawdown_pct",
            "win_rate_pct","profit_factor","nb_trades","buy_hold_pct"]
    print("\n" + "="*90)
    print("COMPARATIF MULTI-ACTIFS — SMA {}/{}/{}".format(SMA_S, SMA_M, SMA_L))
    print("="*90)
    hdr = f"{'Symbol':<12} {'PnL%':>7} {'CAGR%':>8} {'Sharpe':>7} {'MaxDD%':>8} {'WR%':>6} {'PF':>6} {'Trades':>7} {'B&H%':>8}"
    print(hdr)
    print("-"*90)
    for r in results:
        m = r["metrics"]
        verdict = "OK" if m["profit_factor"] > 1.2 and m["sharpe"] > 0.5 and m["nb_trades"] >= 10 else "--"
        print(
            f"{r['symbol']:<12} "
            f"{m['pnl_pct']:>+7.1f} "
            f"{m['cagr_pct']:>8.1f} "
            f"{m['sharpe']:>7.3f} "
            f"{m['max_drawdown_pct']:>8.1f} "
            f"{m['win_rate_pct']:>6.1f} "
            f"{m['profit_factor']:>6.3f} "
            f"{m['nb_trades']:>7} "
            f"{m['buy_hold_pct']:>+8.1f}  {verdict}"
        )
    print("="*90)
    print("OK = PF>1.2 + Sharpe>0.5 + Trades>=10 | -- = criteres non atteints")


# ── Main ────────────────────────────────────────────────────────
def main():
    print("="*60)
    print(f"BACKTEST MULTI-ACTIFS  SMA {SMA_S}/{SMA_M}/{SMA_L}  {INTERVAL}")
    print(f"Capital ${CAPITAL_INIT} | Levier x{LEVERAGE} | Frais {TAKER_FEE*100:.2f}% | {DAYS_BACK}j (~{DAYS_BACK//365} ans)")
    print("="*60)

    results = []
    for symbol in SYMBOLS:
        print(f"\n--- {symbol} ---")
        try:
            df = download_data(symbol)
            df = compute_signals(df)
            n_valid = len(df)
            print(f"  Apres dropna : {n_valid:,} bougies")
            if n_valid < SMA_L + 10:
                print(f"  SKIP : donnees insuffisantes ({n_valid} < {SMA_L+10})")
                continue

            long_  = (df.signal == 1).sum()
            short_ = (df.signal == -1).sum()
            print(f"  Signaux : LONG={long_:,} SHORT={short_:,} NEUTRE={(df.signal==0).sum():,}")

            df          = run_backtest(df)
            m, trades_df = compute_metrics(df)

            print(f"  PnL: {m['pnl_pct']:+.2f}% | Sharpe: {m['sharpe']:.3f} | "
                  f"MaxDD: {m['max_drawdown_pct']:.1f}% | PF: {m['profit_factor']:.3f} | "
                  f"Trades: {m['nb_trades']} | n_years: {m['n_years_actual']:.3f}")

            if not trades_df.empty:
                trades_df.to_csv(f"backtest/trades_{symbol}.csv", index=False)

            # Walk-forward
            folds = walk_forward(df, symbol)
            print_walkforward(folds, symbol)

            plot_single(df, m, symbol)
            df[["close","sma_s","sma_m","sma_l","signal","position","equity","net_ret"]]\
                .to_csv(f"backtest/results_{symbol}.csv")

            results.append({"symbol": symbol, "metrics": m, "wf_folds": folds})

        except Exception as e:
            print(f"  ERREUR {symbol}: {e}")

    if results:
        print_summary(results)


if __name__ == "__main__":
    main()
