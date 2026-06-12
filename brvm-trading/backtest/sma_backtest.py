"""
Backtest SMA Triple — MATICUSDT Futures
Métriques : CAGR, Sharpe, Max Drawdown, Win Rate, Profit Factor
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from binance.client import Client

# ── Config ────────────────────────────────────────────────────
SYMBOL       = "MATICUSDT"
INTERVAL     = Client.KLINE_INTERVAL_1MINUTE
DAYS_BACK    = 90        # 3 mois de données
SMA_S        = 19
SMA_M        = 38
SMA_L        = 361
LEVERAGE     = 1         # Sans levier pour le backtest initial
CAPITAL_INIT = 1000      # $1000 USDT
TAKER_FEE    = 0.0004    # 0.04% Binance Futures taker
MAKER_FEE    = 0.0002    # 0.02% Binance Futures maker

API_KEY    = os.environ.get("BINANCE_API_KEY", "")
API_SECRET = os.environ.get("BINANCE_SECRET_KEY", "")


def download_data(symbol, interval, days):
    print(f"Téléchargement {symbol} {interval} ({days} jours)...")
    client = Client(API_KEY, API_SECRET, testnet=False)
    now  = datetime.utcnow()
    past = str(now - timedelta(days=days))
    bars = client.futures_historical_klines(
        symbol=symbol, interval=interval,
        start_str=past, limit=1000
    )
    df = pd.DataFrame(bars, columns=[
        "timestamp","open","high","low","close","volume",
        "close_time","quote_vol","trades",
        "taker_buy_base","taker_buy_quote","ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    for col in ["open","high","low","close","volume"]:
        df[col] = pd.to_numeric(df[col])
    print(f"{len(df):,} bougies téléchargées")
    return df


def compute_signals(df, sma_s, sma_m, sma_l):
    df = df.copy()
    df["sma_s"] = df["close"].rolling(sma_s).mean()
    df["sma_m"] = df["close"].rolling(sma_m).mean()
    df["sma_l"] = df["close"].rolling(sma_l).mean()
    df.dropna(inplace=True)

    df["signal"] = 0
    df.loc[(df.sma_s > df.sma_m) & (df.sma_m > df.sma_l), "signal"] =  1
    df.loc[(df.sma_s < df.sma_m) & (df.sma_m < df.sma_l), "signal"] = -1
    df["position"] = df["signal"].shift(1).fillna(0)

    print(f"Signaux — LONG:{(df.signal==1).sum():,} | SHORT:{(df.signal==-1).sum():,} | NEUTRE:{(df.signal==0).sum():,}")
    return df


def run_backtest(df, capital, leverage, fee):
    df = df.copy()
    df["returns"]   = df["close"].pct_change()
    df["strat_ret"] = df["position"] * df["returns"] * leverage
    df["trade"]     = df["position"].diff().abs()
    df["fee_cost"]  = df["trade"] * fee
    df["net_ret"]   = df["strat_ret"] - df["fee_cost"]
    df["equity"]    = capital * (1 + df["net_ret"]).cumprod()
    df["buy_hold"]  = capital * (1 + df["returns"]).cumprod()
    return df


def build_trade_log(df) -> pd.DataFrame:
    """
    Construit un vrai journal de trades entry→exit.
    Chaque ligne = un trade complet avec son PnL reel.
    """
    trades = []
    in_pos = False
    entry_price = entry_date = side = 0

    for date, row in df.iterrows():
        p = row["position"]
        if not in_pos and p != 0:
            in_pos = True
            entry_price = row["close"]
            entry_date  = date
            side        = p
        elif in_pos and p != side:
            exit_price = row["close"]
            raw_pnl    = (exit_price - entry_price) / entry_price * side
            net_pnl    = raw_pnl - 2 * TAKER_FEE   # frais entree + sortie
            trades.append({
                "entry_date":  entry_date,
                "exit_date":   date,
                "side":        "LONG" if side == 1 else "SHORT",
                "entry_price": entry_price,
                "exit_price":  exit_price,
                "pnl_pct":     net_pnl,
                "hold_candles": (df.index.get_loc(date) - df.index.get_loc(entry_date)),
            })
            if p != 0:
                entry_price = row["close"]
                entry_date  = date
                side        = p
            else:
                in_pos = False

    return pd.DataFrame(trades)


def compute_metrics(df, capital):
    equity = df["equity"].dropna()

    # ── Bug 1 corrigé : CAGR via durée réelle (pas len/1440) ──
    n_years = (equity.index[-1] - equity.index[0]).total_seconds() / (365.25 * 24 * 3600)
    n_years = max(n_years, 1 / 365)
    cagr    = (equity.iloc[-1] / capital) ** (1 / n_years) - 1

    # ── Bug 2 corrigé : Sharpe sur equity.pct_change() ────────
    # + annualisation auto-détectée depuis la fréquence réelle
    eq_ret  = equity.pct_change().dropna()
    if len(eq_ret) > 1:
        median_sec        = pd.Series(equity.index.asi8).diff().median() / 1e9
        candles_per_year  = (365.25 * 24 * 3600) / max(median_sec, 1)
        sharpe = (eq_ret.mean() / eq_ret.std()) * np.sqrt(candles_per_year) if eq_ret.std() > 0 else 0
    else:
        sharpe = 0

    # Max Drawdown
    rolling_max = equity.cummax()
    max_dd      = ((equity - rolling_max) / rolling_max).min()

    # ── Bug 3 corrigé : Win Rate / PF sur trades entry→exit ───
    trades_df     = build_trade_log(df)
    nb_trades     = len(trades_df)

    if nb_trades > 0:
        pnls          = trades_df["pnl_pct"]
        win_rate      = (pnls > 0).mean()
        gross_profit  = pnls[pnls > 0].sum()
        gross_loss    = abs(pnls[pnls < 0].sum())
        profit_factor = gross_profit / max(gross_loss, 1e-10)
        avg_hold      = trades_df["hold_candles"].mean()
    else:
        win_rate = profit_factor = avg_hold = 0

    return {
        "capital_final":   round(equity.iloc[-1], 2),
        "pnl_usd":         round(equity.iloc[-1] - capital, 2),
        "pnl_pct":         round((equity.iloc[-1] / capital - 1) * 100, 2),
        "cagr_pct":        round(cagr * 100, 2),
        "sharpe":          round(sharpe, 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "win_rate_pct":    round(win_rate * 100, 2),
        "profit_factor":   round(profit_factor, 3),
        "nb_trades":       nb_trades,
        "avg_hold_candles": round(avg_hold, 1),
        "n_years_actual":  round(n_years, 4),
    }, trades_df


def plot_results(df, metrics, symbol, sma_s, sma_m, sma_l):
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))
    fig.suptitle(
        f"Backtest {symbol} — SMA {sma_s}/{sma_m}/{sma_l}\n"
        f"PnL: {metrics['pnl_pct']:+.1f}% | Sharpe: {metrics['sharpe']:.2f} | "
        f"MaxDD: {metrics['max_drawdown_pct']:.1f}% | WinRate: {metrics['win_rate_pct']:.1f}%",
        fontsize=13
    )

    axes[0].plot(df.index, df["equity"],   label="Stratégie SMA", color="#C9A84C", lw=1.5)
    axes[0].plot(df.index, df["buy_hold"], label="Buy & Hold",    color="#3498DB", lw=1, alpha=0.7)
    axes[0].axhline(CAPITAL_INIT, color="gray", linestyle="--", lw=0.8)
    axes[0].set_ylabel("Capital ($)")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    rolling_max = df["equity"].cummax()
    drawdown    = (df["equity"] - rolling_max) / rolling_max * 100
    axes[1].fill_between(df.index, drawdown, 0, color="#E74C3C", alpha=0.6)
    axes[1].set_ylabel("Drawdown (%)")
    axes[1].grid(True, alpha=0.3)

    axes[2].fill_between(df.index, df["position"], 0,
        where=df["position"] > 0, color="#2ECC71", alpha=0.6, label="LONG")
    axes[2].fill_between(df.index, df["position"], 0,
        where=df["position"] < 0, color="#E74C3C", alpha=0.6, label="SHORT")
    axes[2].set_ylabel("Position")
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("backtest/results.png", dpi=150)
    plt.show()
    print("Graphique sauvegardé : backtest/results.png")


def main():
    print("=" * 60)
    print(f"BACKTEST — {SYMBOL} SMA {SMA_S}/{SMA_M}/{SMA_L}")
    print(f"Capital: ${CAPITAL_INIT} | Levier: x{LEVERAGE} | Frais: {TAKER_FEE*100:.2f}%")
    print("=" * 60)

    df      = download_data(SYMBOL, INTERVAL, DAYS_BACK)
    df      = compute_signals(df, SMA_S, SMA_M, SMA_L)
    df               = run_backtest(df, CAPITAL_INIT, LEVERAGE, TAKER_FEE)
    metrics, trades_df = compute_metrics(df, CAPITAL_INIT)

    print("\nRESULTATS BACKTEST")
    print("-" * 40)
    for k, v in metrics.items():
        unit = "%" if "pct" in k or "rate" in k or "drawdown" in k or "cagr" in k else ""
        print(f"  {k:<20} : {v}{unit}")

    print("\nINTERPRETATION")
    print("-" * 40)
    if metrics["sharpe"] > 1.5:
        print("  Sharpe > 1.5 — strategie potentiellement viable")
    elif metrics["sharpe"] > 0.5:
        print("  Sharpe 0.5-1.5 — strategie faible, a ameliorer")
    else:
        print("  Sharpe < 0.5 — strategie non viable en l'etat")

    if metrics["max_drawdown_pct"] < -20:
        print(f"  Drawdown {metrics['max_drawdown_pct']}% — risque eleve avec levier")
    else:
        print(f"  Drawdown {metrics['max_drawdown_pct']}% — acceptable")

    if metrics["profit_factor"] > 1.5:
        print(f"  Profit Factor {metrics['profit_factor']} — edge statistique confirme")
    else:
        print(f"  Profit Factor {metrics['profit_factor']} — pas d'edge significatif")

    plot_results(df, metrics, SYMBOL, SMA_S, SMA_M, SMA_L)

    df[["close","sma_s","sma_m","sma_l","signal","position","equity","net_ret"]]\
        .to_csv("backtest/results.csv")
    print("Resultats exportes : backtest/results.csv")

    if not trades_df.empty:
        trades_df.to_csv("backtest/trades_log.csv", index=False)
        print(f"Trade log exporte : backtest/trades_log.csv ({len(trades_df)} trades)")


if __name__ == "__main__":
    main()
