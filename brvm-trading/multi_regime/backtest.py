"""
backtest.py — Moteur de backtest + walk-forward
  Fonctions pures : pas d'etat global, compatibles avec tout pipeline.

Usage :
  from backtest import run_backtest, compute_metrics, WalkForward
"""
import numpy as np
import pandas as pd


TAKER_FEE = 0.0004   # 0.04 % Binance Futures

# ── Simulation equity ─────────────────────────────────────────
def run_backtest(df: pd.DataFrame, capital: float = 1000,
                 leverage: float = 1, fee: float = TAKER_FEE) -> pd.DataFrame:
    """
    Requiert df avec colonnes : close, position.
    Retourne df enrichi : returns, strat_ret, fee_cost, net_ret, equity, buy_hold.
    """
    out = df.copy()
    out["returns"]   = out["close"].pct_change()
    out["strat_ret"] = out["position"] * out["returns"] * leverage
    out["trade"]     = out["position"].diff().abs()
    out["fee_cost"]  = out["trade"] * fee
    out["net_ret"]   = out["strat_ret"] - out["fee_cost"]
    out["equity"]    = capital * (1 + out["net_ret"]).cumprod()
    out["buy_hold"]  = capital * (1 + out["returns"]).cumprod()
    return out


# ── Trade log entry->exit ─────────────────────────────────────
def build_trade_log(df: pd.DataFrame, fee: float = TAKER_FEE) -> pd.DataFrame:
    trades = []
    in_pos = False
    entry_price = entry_date = side = 0
    for date, row in df.iterrows():
        p = row["position"]
        if not in_pos and p != 0:
            in_pos = True; entry_price = row["close"]; entry_date = date; side = p
        elif in_pos and p != side:
            exit_price = row["close"]
            raw_pnl    = (exit_price - entry_price) / entry_price * side
            net_pnl    = raw_pnl - 2 * fee
            trades.append({
                "entry_date":   entry_date,
                "exit_date":    date,
                "side":         "LONG" if side == 1 else "SHORT",
                "entry_price":  entry_price,
                "exit_price":   exit_price,
                "pnl_pct":      net_pnl,
                "hold_candles": df.index.get_loc(date) - df.index.get_loc(entry_date),
            })
            if p != 0:
                entry_price = row["close"]; entry_date = date; side = p
            else:
                in_pos = False
    return pd.DataFrame(trades)


# ── Metriques ─────────────────────────────────────────────────
def compute_metrics(df: pd.DataFrame, capital: float = 1000) -> tuple[dict, pd.DataFrame]:
    equity = df["equity"].dropna()

    # CAGR — duree reelle
    n_years = (equity.index[-1] - equity.index[0]).total_seconds() / (365.25 * 24 * 3600)
    n_years = max(n_years, 1 / 365)
    cagr    = (equity.iloc[-1] / capital) ** (1 / n_years) - 1

    # Sharpe — equity.pct_change() + annualisation auto
    eq_ret = equity.pct_change().dropna()
    if len(eq_ret) > 1 and eq_ret.std() > 0:
        med_sec = pd.Series(equity.index.asi8).diff().median() / 1e9
        cpy     = (365.25 * 24 * 3600) / max(med_sec, 1)
        sharpe  = (eq_ret.mean() / eq_ret.std()) * np.sqrt(cpy)
    else:
        sharpe  = 0

    # Max Drawdown
    roll_max = equity.cummax()
    max_dd   = ((equity - roll_max) / roll_max).min()

    # Trades entry->exit
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

    metrics = {
        "capital_final":    round(equity.iloc[-1], 2),
        "pnl_pct":          round((equity.iloc[-1] / capital - 1) * 100, 2),
        "cagr_pct":         round(cagr * 100, 2),
        "sharpe":           round(sharpe, 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "win_rate_pct":     round(win_rate * 100, 2),
        "profit_factor":    round(pf, 3),
        "nb_trades":        nb,
        "avg_hold_candles": round(avg_hold, 1),
        "n_years":          round(n_years, 3),
        "buy_hold_pct":     round((df["buy_hold"].iloc[-1] / capital - 1) * 100, 2),
    }
    return metrics, trades_df


# ── Walk-forward ──────────────────────────────────────────────
class WalkForward:
    """
    Walk-forward validation avec N folds glissants.

    Chaque fold decoupe le dataset en :
      train  : WF_TRAIN_PCT % du fold
      test   : reste (OOS)

    Usage :
      wf = WalkForward(n_folds=3, train_pct=0.70)
      results = wf.run(df_with_signals, capital=1000)
    """

    def __init__(self, n_folds: int = 3, train_pct: float = 0.70,
                 min_oos_bars: int = 400):
        self.n_folds      = n_folds
        self.train_pct    = train_pct
        self.min_oos_bars = min_oos_bars

    def run(self, df: pd.DataFrame, capital: float = 1000) -> list[dict]:
        """
        df doit contenir colonnes close + position (deja generees par une strategie).
        """
        n       = len(df)
        fold_sz = n // self.n_folds
        folds   = []

        for i in range(self.n_folds):
            start = i * fold_sz
            end   = start + fold_sz if i < self.n_folds - 1 else n
            chunk = df.iloc[start:end].copy()
            split = int(len(chunk) * self.train_pct)
            train = chunk.iloc[:split]
            oos   = chunk.iloc[split:]

            if len(oos) < self.min_oos_bars:
                continue

            bt_is  = run_backtest(train,  capital)
            bt_oos = run_backtest(oos,    capital)

            m_is,  _  = compute_metrics(bt_is,  capital)
            m_oos, tl = compute_metrics(bt_oos, capital)

            ratio = (m_oos["sharpe"] / m_is["sharpe"]) if m_is["sharpe"] != 0 else 0

            folds.append({
                "fold":          i + 1,
                "is_start":      train.index[0].strftime("%Y-%m"),
                "is_end":        train.index[-1].strftime("%Y-%m"),
                "oos_start":     oos.index[0].strftime("%Y-%m"),
                "oos_end":       oos.index[-1].strftime("%Y-%m"),
                "is_bars":       len(train),
                "oos_bars":      len(oos),
                "is_sharpe":     m_is["sharpe"],
                "oos_sharpe":    m_oos["sharpe"],
                "oos_pnl":       m_oos["pnl_pct"],
                "oos_pf":        m_oos["profit_factor"],
                "oos_dd":        m_oos["max_drawdown_pct"],
                "oos_trades":    m_oos["nb_trades"],
                "oos_wr":        m_oos["win_rate_pct"],
                "oos_is_ratio":  round(ratio, 3),
                "overfit":       ratio < 0.5 and m_is["sharpe"] > 0.5,
            })

        return folds

    # ── Affichage ─────────────────────────────────────────────
    @staticmethod
    def print_folds(folds: list[dict], symbol: str = ""):
        if not folds:
            print("  Walk-forward : donnees insuffisantes")
            return
        label = f"WALK-FORWARD {symbol}" if symbol else "WALK-FORWARD"
        print(f"\n  {label}  ({len(folds)} folds)")
        hdr = ("  " + f"{'Fold':>4}  {'IS':>13}  {'OOS':>13}  "
               f"{'IS Sh':>7}  {'OOS Sh':>7}  {'OOS PnL':>8}  "
               f"{'PF':>6}  {'DD%':>6}  {'Trades':>7}  {'Ratio':>7}")
        print(hdr)
        print("  " + "-" * 86)
        for f in folds:
            flag = "  OVERFIT" if f["overfit"] else ""
            print(
                f"  {f['fold']:>4}  "
                f"{f['is_start']}->{f['is_end']}  "
                f"{f['oos_start']}->{f['oos_end']}  "
                f"{f['is_sharpe']:>7.3f}  "
                f"{f['oos_sharpe']:>7.3f}  "
                f"{f['oos_pnl']:>+8.1f}%  "
                f"{f['oos_pf']:>6.3f}  "
                f"{f['oos_dd']:>6.1f}  "
                f"{f['oos_trades']:>7}  "
                f"{f['oos_is_ratio']:>7.3f}"
                f"{flag}"
            )
        avg_sh = np.mean([f["oos_sharpe"] for f in folds])
        avg_pf = np.mean([f["oos_pf"]     for f in folds])
        n_of   = sum(f["overfit"]           for f in folds)
        sh_std = np.std([f["oos_sharpe"]    for f in folds])
        print(f"\n  OOS moyen  Sharpe: {avg_sh:.3f} (std {sh_std:.3f}) | "
              f"PF: {avg_pf:.3f} | Overfits: {n_of}/{len(folds)}")
        WalkForward._verdict(avg_sh, avg_pf, n_of, sh_std, len(folds))

    @staticmethod
    def _verdict(avg_sh: float, avg_pf: float,
                 n_overfit: int, sh_std: float, n_folds: int):
        stable  = sh_std < 0.4
        robust  = avg_sh >= 0.8 and avg_pf >= 1.3 and n_overfit == 0 and stable
        ok      = avg_sh >= 0.5 and avg_pf >= 1.1 and n_overfit <= 1
        if robust:
            print("  VERDICT : ROBUSTE — candidat paper trading")
        elif ok:
            print("  VERDICT : EDGE FAIBLE — validation supplementaire recommandee")
        else:
            print("  VERDICT : PAS D'EDGE OOS CONFIRME — ne pas deployer")

    @staticmethod
    def summary(all_results: list[dict]) -> dict:
        """Aggrege les resultats de tous les folds pour un actif."""
        if not all_results:
            return {}
        return {
            "avg_oos_sharpe": round(np.mean([f["oos_sharpe"] for f in all_results]), 3),
            "std_oos_sharpe": round(np.std([f["oos_sharpe"]  for f in all_results]), 3),
            "avg_oos_pf":     round(np.mean([f["oos_pf"]     for f in all_results]), 3),
            "avg_oos_dd":     round(np.mean([f["oos_dd"]     for f in all_results]), 2),
            "n_overfit":      sum(f["overfit"]                for f in all_results),
            "n_folds":        len(all_results),
        }
