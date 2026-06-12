"""
Production Paper Trading Engine v1
====================================
Architecture :
  Binance WebSocket (klines) -> Indicator Engine -> Regime Detector v2
  -> Adaptive Score -> Signal -> Paper Executor -> SQLite/PostgreSQL
  -> Telegram alerts -> Kill-switch auto

Usage :
  python brvm-trading/paper/paper_engine_v1.py

Variables d'environnement (.env ou OS) :
  BINANCE_API_KEY    - cles Binance (lecture seule suffisante)
  BINANCE_SECRET_KEY
  TELEGRAM_TOKEN     - bot token
  TELEGRAM_CHAT_ID   - chat ID
  DATABASE_URL       - postgresql://... (optionnel, fallback SQLite)
  PAPER_ASSETS       - BTC-USDT,ETH-USDT,SOL-USDT,XRP-USDT (optionnel)
  PAPER_INTERVAL     - 5m (defaut)
  PAPER_CAPITAL      - 10000 (defaut)
"""
import os
import sys
import json
import time
import logging
import sqlite3
import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np
import pandas as pd

# ── Logging ───────────────────────────────────────────────────
LOG_DIR = Path("brvm-trading/paper/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "paper_engine.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("PaperEngine")

# ── Config ────────────────────────────────────────────────────
API_KEY    = os.environ.get("BINANCE_API_KEY", "")
API_SECRET = os.environ.get("BINANCE_SECRET_KEY", "")
TG_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TG_CHAT    = os.environ.get("TELEGRAM_CHAT_ID", "")
DB_URL     = os.environ.get("DATABASE_URL", "")

ASSETS_RAW = os.environ.get(
    "PAPER_ASSETS", "BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT"
).split(",")

INTERVAL     = os.environ.get("PAPER_INTERVAL", "5m")
CAPITAL_INIT = float(os.environ.get("PAPER_CAPITAL", "10000"))

SLIPPAGE     = 0.0003    # 0.03% slippage realiste
TAKER_FEE    = 0.0004    # 0.04% Binance Futures

# Phase 1 : BTC/ETH | Phase 2 : +SOL/XRP | Phase 3 : full
PHASE_SCHEDULE = {
    1: ["BTCUSDT", "ETHUSDT"],
    2: ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"],
    3: ASSETS_RAW,
}
ACTIVE_PHASE = int(os.environ.get("PAPER_PHASE", "1"))
ACTIVE_ASSETS = PHASE_SCHEDULE.get(ACTIVE_PHASE, PHASE_SCHEDULE[1])

# Asset profile (base_thresh, max_dd)
PROFILES = {
    "BTCUSDT":  {"tier": "C", "base_thresh": 5, "max_dd": 0.15},
    "ETHUSDT":  {"tier": "C", "base_thresh": 5, "max_dd": 0.15},
    "SOLUSDT":  {"tier": "A", "base_thresh": 4, "max_dd": 0.25},
    "XRPUSDT":  {"tier": "A", "base_thresh": 4, "max_dd": 0.25},
    "BNBUSDT":  {"tier": "B", "base_thresh": 4, "max_dd": 0.20},
    "ADAUSDT":  {"tier": "B", "base_thresh": 4, "max_dd": 0.20},
    "AVAXUSDT": {"tier": "B", "base_thresh": 4, "max_dd": 0.20},
    "DOGEUSDT": {"tier": "D", "base_thresh": 6, "max_dd": 0.12},
}

# Kill-switch global
PORTFOLIO_MAX_DD = 0.10    # coupe tout si portefeuille DD > 10%
ASSET_MAX_DD     = 0.08    # coupe asset si DD > 8%

# Candles buffer minimum avant de generer un signal
MIN_CANDLES = 250

# SMA optimaux issus du backtest v2
SMA_CONFIG = {
    "BTCUSDT":  (10, 19, 246),
    "ETHUSDT":  (16, 38, 246),
    "SOLUSDT":  (10, 38, 200),
    "XRPUSDT":  (16, 50, 200),
    "BNBUSDT":  (16, 38, 200),
    "ADAUSDT":  (10, 19, 246),
    "AVAXUSDT": (20, 38, 100),
    "DOGEUSDT": (20, 50, 200),
}

DB_PATH = Path("brvm-trading/paper/paper_trades.db")


# ── Base de donnees ───────────────────────────────────────────
class Database:
    """SQLite avec schema compatible PostgreSQL."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS trades (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        asset       TEXT    NOT NULL,
        side        TEXT    NOT NULL,
        entry_time  TEXT    NOT NULL,
        exit_time   TEXT,
        entry_price REAL    NOT NULL,
        exit_price  REAL,
        quantity    REAL    NOT NULL,
        pnl_pct     REAL,
        pnl_usd     REAL,
        fees_usd    REAL,
        regime      TEXT,
        score       REAL,
        slippage    REAL,
        status      TEXT    DEFAULT 'OPEN',
        created_at  TEXT    DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS signals (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        asset       TEXT    NOT NULL,
        ts          TEXT    NOT NULL,
        price       REAL    NOT NULL,
        score       REAL    NOT NULL,
        regime      TEXT    NOT NULL,
        threshold   INTEGER NOT NULL,
        signal      INTEGER NOT NULL,
        created_at  TEXT    DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS portfolio_snapshots (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        ts          TEXT    NOT NULL,
        equity      REAL    NOT NULL,
        pnl_pct     REAL    NOT NULL,
        drawdown    REAL    NOT NULL,
        open_trades INTEGER NOT NULL,
        created_at  TEXT    DEFAULT (datetime('now'))
    );
    """

    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self):
        with self._conn() as c:
            c.executescript(self.SCHEMA)
        log.info(f"DB initialise : {self.path}")

    def log_signal(self, asset, ts, price, score, regime, threshold, signal):
        with self._conn() as c:
            c.execute("""
                INSERT INTO signals (asset, ts, price, score, regime, threshold, signal)
                VALUES (?,?,?,?,?,?,?)
            """, (asset, ts, price, score, regime, threshold, signal))

    def open_trade(self, asset, side, entry_time, entry_price,
                   quantity, regime, score, slippage) -> int:
        with self._conn() as c:
            cur = c.execute("""
                INSERT INTO trades (asset, side, entry_time, entry_price,
                                    quantity, regime, score, slippage, status)
                VALUES (?,?,?,?,?,?,?,?,'OPEN')
            """, (asset, side, entry_time, entry_price, quantity, regime, score, slippage))
            return cur.lastrowid

    def close_trade(self, trade_id, exit_time, exit_price, pnl_pct, pnl_usd, fees_usd):
        with self._conn() as c:
            c.execute("""
                UPDATE trades
                SET exit_time=?, exit_price=?, pnl_pct=?, pnl_usd=?,
                    fees_usd=?, status='CLOSED'
                WHERE id=?
            """, (exit_time, exit_price, pnl_pct, pnl_usd, fees_usd, trade_id))

    def log_snapshot(self, equity, pnl_pct, drawdown, open_trades):
        ts = datetime.now(timezone.utc).isoformat()
        with self._conn() as c:
            c.execute("""
                INSERT INTO portfolio_snapshots (ts, equity, pnl_pct, drawdown, open_trades)
                VALUES (?,?,?,?,?)
            """, (ts, equity, pnl_pct, drawdown, open_trades))

    def get_open_trades(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM trades WHERE status='OPEN'").fetchall()
            return [dict(r) for r in rows]

    def get_all_trades(self) -> pd.DataFrame:
        with self._conn() as c:
            return pd.read_sql("SELECT * FROM trades ORDER BY entry_time DESC", c)

    def get_snapshots(self) -> pd.DataFrame:
        with self._conn() as c:
            return pd.read_sql("SELECT * FROM portfolio_snapshots ORDER BY ts", c)


# ── Indicateurs ───────────────────────────────────────────────
def _ema(s: pd.Series, p: int) -> float:
    """EMA sur la derniere valeur d'une Series."""
    if len(s) < p:
        return float("nan")
    return float(s.ewm(span=p, adjust=False, min_periods=p).mean().iloc[-1])

def _sma(s: pd.Series, p: int) -> float:
    if len(s) < p:
        return float("nan")
    return float(s.rolling(p).mean().iloc[-1])

def _rsi_last(s: pd.Series, p: int = 14) -> float:
    if len(s) < p + 1:
        return 50.0
    d = s.diff()
    g = d.clip(lower=0).ewm(com=p - 1, min_periods=p).mean()
    l = (-d.clip(upper=0)).ewm(com=p - 1, min_periods=p).mean()
    rs = g / l.replace(0, np.nan)
    return float(100 - 100 / (1 + rs.iloc[-1]))

def _mfi_last(closes, highs, lows, volumes, p: int = 14) -> float:
    if len(closes) < p + 1:
        return 50.0
    df = pd.DataFrame({"c": closes, "h": highs, "l": lows, "v": volumes})
    tp  = (df.h + df.l + df.c) / 3
    mf  = tp * df.v
    pos = mf.where(tp > tp.shift(1), 0).rolling(p, min_periods=1).sum()
    neg = mf.where(tp < tp.shift(1), 0).rolling(p, min_periods=1).sum()
    r   = (100 - 100 / (1 + pos / neg.replace(0, np.nan))).iloc[-1]
    return float(r) if not np.isnan(r) else 50.0

def _macd_hist_last(s: pd.Series, fast=12, slow=26, sig=9) -> float:
    if len(s) < slow + sig:
        return 0.0
    m  = s.ewm(span=fast, adjust=False).mean() - s.ewm(span=slow, adjust=False).mean()
    h  = m - m.ewm(span=sig, adjust=False).mean()
    return float(h.iloc[-1])

def _atr_last(highs, lows, closes, p: int = 14) -> float:
    if len(closes) < p + 1:
        return float(closes[-1]) * 0.02
    h = pd.Series(highs); l = pd.Series(lows); c = pd.Series(closes)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return float(tr.ewm(span=p, adjust=False, min_periods=p).mean().iloc[-1])


# ── Regime Detector v2 (last bar) ─────────────────────────────
class RegimeDetectorLive:
    """Version live (une seule barre a la fois)."""
    THRESH = {"trend": 3, "neutral": 4, "high_vol": 5, "range": 4}

    def detect(self, closes: list, highs: list, lows: list,
               vol_window: int = 252, slope_window: int = 10) -> tuple[str, int]:
        if len(closes) < 210:
            return "neutral", 4

        s    = pd.Series(closes)
        atr  = pd.Series([_atr_last(highs[max(0,i-20):i+1],
                                     lows[max(0,i-20):i+1],
                                     closes[max(0,i-20):i+1])
                          for i in range(len(closes))])
        atr_pct = atr / s

        e200   = s.ewm(span=200, adjust=False, min_periods=200).mean()
        slope  = e200.pct_change(slope_window).iloc[-1]

        # Percentile glissant
        win    = min(vol_window, len(atr_pct) - 1)
        hist   = atr_pct.iloc[-win:]
        cur    = atr_pct.iloc[-1]
        pctile = float((hist < cur).mean())    # rang actuel dans historique

        is_high_vol = pctile > 0.85
        is_flat     = abs(slope) < 0.003 if not np.isnan(slope) else True
        is_up       = slope > 0.003 if not np.isnan(slope) else False
        vol_rank    = pctile

        if is_up and not is_high_vol:
            regime = "trend"
        elif is_high_vol:
            regime = "high_vol"
        elif is_flat and vol_rank < 0.4:
            regime = "range"
        else:
            regime = "neutral"

        return regime, self.THRESH[regime]


# ── Score composite (last bar) ────────────────────────────────
def compute_score_live(closes, highs, lows, volumes,
                       sma_s=16, sma_m=19, sma_l=246) -> float:
    s = pd.Series(closes)
    if len(s) < sma_l:
        return 0.0

    score = 0.0

    r = _rsi_last(s)
    score += 2 if r < 30 else 1 if r < 45 else -2 if r > 70 else -1 if r > 55 else 0

    m = _mfi_last(closes, highs, lows, volumes)
    score += 2 if m < 20 else -2 if m > 80 else 0

    ms = _sma(s, sma_s); mm = _sma(s, sma_m); ml = _sma(s, sma_l)
    if not np.isnan(ms) and not np.isnan(mm):
        score += 1 if ms > mm else -1
    if not np.isnan(mm) and not np.isnan(ml):
        score += 1 if mm > ml else -1

    mh = _macd_hist_last(s)
    score += 1 if mh > 0 else -1

    e9  = _ema(s, 9);  e50 = _ema(s, 50);  e200 = _ema(s, 200)
    if not np.isnan(e9) and not np.isnan(e50):
        score += 1 if e9 > e50 else -1
    if not np.isnan(e50) and not np.isnan(e200):
        score += 1 if e50 > e200 else -1

    return score


# ── Paper Executor ─────────────────────────────────────────────
@dataclass
class OpenTrade:
    db_id:      int
    asset:      str
    side:       int          # +1 LONG / -1 SHORT
    entry_time: str
    entry_price: float
    quantity:   float        # en USD notional
    regime:     str
    score:      float
    peak_price: float = 0.0  # pour trailing stop

class PaperExecutor:
    """Simule ouverture / fermeture de positions avec slippage + fees."""

    def __init__(self, db: Database, capital: float,
                 risk_per_trade: float = 0.01):
        self.db             = db
        self.capital        = capital
        self.equity         = capital
        self.peak_equity    = capital
        self.risk_per_trade = risk_per_trade
        self.open_trades:   dict[str, OpenTrade] = {}
        self.closed_pnl:    list[float] = []

    @property
    def drawdown(self) -> float:
        if self.peak_equity <= 0:
            return 0.0
        return (self.equity - self.peak_equity) / self.peak_equity

    def _qty(self, price: float, atr: float) -> float:
        """Taille ATR-based (risque fixe)."""
        dollar_risk = self.equity * self.risk_per_trade
        stop_dist   = max(atr * 2, price * 0.001)
        qty         = dollar_risk / stop_dist
        max_qty     = self.equity * 0.30 / price
        return min(qty, max_qty)

    def open(self, asset: str, signal: int, price: float, atr: float,
             regime: str, score: float, ts: str):

        # Ne pas ré-ouvrir si deja une position sur cet asset
        if asset in self.open_trades:
            return

        slip     = price * SLIPPAGE * (-1 if signal == 1 else 1)
        exec_px  = price + slip
        qty      = self._qty(exec_px, atr)
        notional = qty * exec_px
        fee      = notional * TAKER_FEE

        self.equity -= fee
        db_id = self.db.open_trade(
            asset, "LONG" if signal == 1 else "SHORT",
            ts, exec_px, qty, regime, score, slip
        )
        self.open_trades[asset] = OpenTrade(
            db_id=db_id, asset=asset, side=signal,
            entry_time=ts, entry_price=exec_px,
            quantity=qty, regime=regime, score=score,
            peak_price=exec_px,
        )
        log.info(f"[OPEN] {asset} {'LONG' if signal==1 else 'SHORT'} "
                 f"@ {exec_px:.4f} | qty={qty:.4f} | regime={regime} | score={score:.1f}")

    def close(self, asset: str, price: float, ts: str, reason: str = "signal"):
        if asset not in self.open_trades:
            return

        trade    = self.open_trades.pop(asset)
        slip     = price * SLIPPAGE * (1 if trade.side == 1 else -1)
        exec_px  = price + slip

        raw_pnl  = (exec_px - trade.entry_price) / trade.entry_price * trade.side
        fee      = trade.quantity * exec_px * TAKER_FEE
        net_pnl  = raw_pnl - 2 * TAKER_FEE - SLIPPAGE * 2
        pnl_usd  = net_pnl * trade.quantity * trade.entry_price

        self.equity += pnl_usd - fee
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity

        self.closed_pnl.append(net_pnl)
        self.db.close_trade(trade.db_id, ts, exec_px, net_pnl, pnl_usd, fee)

        sign = "+" if pnl_usd >= 0 else ""
        log.info(f"[CLOSE] {asset} @ {exec_px:.4f} | "
                 f"PnL: {sign}{pnl_usd:.2f}$ ({sign}{net_pnl*100:.2f}%) | "
                 f"reason={reason} | equity=${self.equity:.2f}")

    def maybe_close_dd(self, asset: str, current_price: float, ts: str):
        """Coupe la position si DD asset > seuil."""
        if asset not in self.open_trades:
            return
        trade  = self.open_trades[asset]
        dd_raw = (current_price - trade.entry_price) / trade.entry_price * trade.side
        if dd_raw < -ASSET_MAX_DD:
            log.warning(f"[CB] {asset} asset drawdown {dd_raw*100:.1f}% > limit")
            self.close(asset, current_price, ts, reason="circuit_breaker")

    def metrics(self) -> dict:
        pnls = self.closed_pnl
        if not pnls:
            return {"equity": self.equity, "pnl_pct": 0, "sharpe": 0,
                    "win_rate": 0, "profit_factor": 0, "nb_trades": 0,
                    "drawdown": self.drawdown}
        arr  = np.array(pnls)
        wr   = float((arr > 0).mean())
        gains  = arr[arr > 0].sum()
        losses = abs(arr[arr < 0].sum())
        pf     = gains / max(losses, 1e-10)
        sh     = (arr.mean() / arr.std()) * np.sqrt(252) if arr.std() > 0 else 0
        return {
            "equity":        round(self.equity, 2),
            "pnl_pct":       round((self.equity / CAPITAL_INIT - 1) * 100, 2),
            "sharpe":        round(sh, 3),
            "win_rate":      round(wr * 100, 1),
            "profit_factor": round(pf, 3),
            "nb_trades":     len(pnls),
            "drawdown":      round(self.drawdown * 100, 2),
        }


# ── Telegram ──────────────────────────────────────────────────
def telegram(msg: str):
    if not TG_TOKEN or not TG_CHAT:
        return
    try:
        import requests as req
        req.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "Markdown"},
            timeout=5,
        )
    except Exception as e:
        log.warning(f"Telegram error: {e}")


# ── Candle Buffer ─────────────────────────────────────────────
class CandleBuffer:
    """Buffer OHLCV glissant par asset."""
    def __init__(self, maxlen: int = 400):
        self.opens   = deque(maxlen=maxlen)
        self.highs   = deque(maxlen=maxlen)
        self.lows    = deque(maxlen=maxlen)
        self.closes  = deque(maxlen=maxlen)
        self.volumes = deque(maxlen=maxlen)
        self.times   = deque(maxlen=maxlen)

    def push(self, o, h, l, c, v, t):
        self.opens.append(float(o))
        self.highs.append(float(h))
        self.lows.append(float(l))
        self.closes.append(float(c))
        self.volumes.append(float(v))
        self.times.append(t)

    def __len__(self):
        return len(self.closes)


# ── Engine Principal ──────────────────────────────────────────
class PaperTradingEngine:

    def __init__(self):
        self.db       = Database()
        self.executor = PaperExecutor(self.db, CAPITAL_INIT)
        self.buffers: dict[str, CandleBuffer] = {a: CandleBuffer() for a in ACTIVE_ASSETS}
        self.regime_det = RegimeDetectorLive()
        self.killed     = False
        self.start_time = datetime.now(timezone.utc)
        self._load_history()

    def _load_history(self):
        """Charge les dernieres bougies via l'API REST pour amorcer les buffers."""
        try:
            from binance.client import Client
            client = Client(API_KEY, API_SECRET)
            for asset in ACTIVE_ASSETS:
                log.info(f"Chargement historique {asset}...")
                klines = client.get_klines(
                    symbol=asset, interval=INTERVAL, limit=400
                )
                buf = self.buffers[asset]
                for k in klines[:-1]:   # exclure la bougie courante (non fermee)
                    buf.push(k[1], k[2], k[3], k[4], k[5],
                             datetime.fromtimestamp(k[0]/1000, tz=timezone.utc).isoformat())
                log.info(f"  {asset} : {len(buf)} bougies chargees")
        except Exception as e:
            log.error(f"Erreur chargement historique : {e}")

    def _on_candle_close(self, asset: str, o, h, l, c, v, ts: str):
        """Traitement d'une bougie fermee."""
        buf = self.buffers[asset]
        buf.push(o, h, l, c, v, ts)

        if len(buf) < MIN_CANDLES:
            return

        closes  = list(buf.closes)
        highs   = list(buf.highs)
        lows    = list(buf.lows)
        volumes = list(buf.volumes)

        # Regime + seuil
        regime, threshold = self.regime_det.detect(closes, highs, lows)

        # Score composite
        sma_s, sma_m, sma_l = SMA_CONFIG.get(asset, (16, 19, 246))
        score = compute_score_live(closes, highs, lows, volumes, sma_s, sma_m, sma_l)

        # Signal
        signal = 1 if score >= threshold else -1 if score <= -threshold else 0

        price = float(c)
        atr   = _atr_last(highs[-20:], lows[-20:], closes[-20:])

        # Log signal
        self.db.log_signal(asset, ts, price, score, regime, threshold, signal)

        # Circuit breaker asset
        self.executor.maybe_close_dd(asset, price, ts)

        # Circuit breaker global
        if self.executor.drawdown < -PORTFOLIO_MAX_DD:
            if not self.killed:
                self.killed = True
                msg = (f"KILL-SWITCH ACTIVE\n"
                       f"Portfolio drawdown {self.executor.drawdown*100:.1f}%\n"
                       f"Toutes positions fermees.")
                log.critical(msg)
                telegram(f"*{msg}")
                for a in list(self.executor.open_trades.keys()):
                    self.executor.close(a, price, ts, reason="kill_switch")
            return

        # Execution paper
        current_pos = self.executor.open_trades.get(asset)
        current_side = current_pos.side if current_pos else 0

        if signal != 0 and signal != current_side:
            # Ferme la position existante si inverse
            if current_pos:
                self.executor.close(asset, price, ts, reason="signal_reverse")
                m = self.executor.metrics()
                telegram(
                    f"*CLOSE {asset}*\n"
                    f"Prix : {price:.4f}\n"
                    f"Equity : ${m['equity']:,.0f}\n"
                    f"PnL total : {m['pnl_pct']:+.1f}%"
                )

            # Ouvre nouvelle position
            self.executor.open(asset, signal, price, atr, regime, score, ts)
            m = self.executor.metrics()
            telegram(
                f"*{'LONG' if signal==1 else 'SHORT'} {asset}*\n"
                f"Prix : {price:.4f}\n"
                f"Score : {score:.1f} | Regime : {regime}\n"
                f"Equity : ${m['equity']:,.0f}"
            )

        elif signal == 0 and current_pos:
            self.executor.close(asset, price, ts, reason="signal_neutral")

        # Snapshot portfolio
        m = self.executor.metrics()
        self.db.log_snapshot(
            m["equity"], m["pnl_pct"], m["drawdown"],
            len(self.executor.open_trades)
        )

        # Log console periodique
        open_str = ", ".join(
            f"{a}={'L' if t.side==1 else 'S'}"
            for a, t in self.executor.open_trades.items()
        ) or "aucune"
        log.info(
            f"[{asset}] prix={price:.4f} score={score:.1f} regime={regime} "
            f"signal={'LONG' if signal==1 else 'SHORT' if signal==-1 else 'FLAT'} "
            f"| Equity=${m['equity']:,.0f} DD={m['drawdown']:.1f}% | Pos: {open_str}"
        )

    def run_websocket(self):
        """WebSocket Binance avec reconnexion automatique."""
        from binance import ThreadedWebsocketManager

        def handle_msg(msg, asset):
            try:
                if msg.get("e") != "kline":
                    return
                k = msg["k"]
                if not k["x"]:    # bougie pas encore fermee
                    return
                ts = datetime.fromtimestamp(k["T"] / 1000, tz=timezone.utc).isoformat()
                self._on_candle_close(
                    asset, k["o"], k["h"], k["l"], k["c"], k["v"], ts
                )
            except Exception as e:
                log.error(f"Erreur traitement message {asset}: {e}")

        while not self.killed:
            try:
                log.info(f"Connexion WebSocket Binance | assets: {ACTIVE_ASSETS}")
                twm = ThreadedWebsocketManager(api_key=API_KEY, api_secret=API_SECRET)
                twm.start()

                for asset in ACTIVE_ASSETS:
                    twm.start_kline_socket(
                        callback=lambda msg, a=asset: handle_msg(msg, a),
                        symbol=asset,
                        interval=INTERVAL,
                    )

                telegram(
                    f"*Paper Engine v1 DEMARRE*\n"
                    f"Phase {ACTIVE_PHASE} | Assets: {', '.join(ACTIVE_ASSETS)}\n"
                    f"Capital: ${CAPITAL_INIT:,} | Interval: {INTERVAL}"
                )

                # Heartbeat toutes les heures
                while not self.killed:
                    time.sleep(3600)
                    m = self.executor.metrics()
                    uptime = (datetime.now(timezone.utc) - self.start_time)
                    telegram(
                        f"*Rapport horaire*\n"
                        f"Uptime: {str(uptime).split('.')[0]}\n"
                        f"Equity: ${m['equity']:,.0f} ({m['pnl_pct']:+.1f}%)\n"
                        f"Sharpe: {m['sharpe']:.2f} | WinRate: {m['win_rate']:.1f}%\n"
                        f"DD: {m['drawdown']:.1f}% | Trades: {m['nb_trades']}"
                    )

                twm.stop()

            except Exception as e:
                log.error(f"WebSocket crash: {e} | Reconnexion dans 30s...")
                time.sleep(30)

    def run(self):
        log.info("=" * 60)
        log.info("PAPER TRADING ENGINE v1")
        log.info(f"Phase {ACTIVE_PHASE} | Assets: {ACTIVE_ASSETS}")
        log.info(f"Capital: ${CAPITAL_INIT:,} | Interval: {INTERVAL}")
        log.info(f"Slippage: {SLIPPAGE*100:.2f}% | Fee: {TAKER_FEE*100:.2f}%")
        log.info(f"Kill-switch: portfolio DD > {PORTFOLIO_MAX_DD*100:.0f}%")
        log.info("=" * 60)
        self.run_websocket()


# ── Entrypoint ────────────────────────────────────────────────
if __name__ == "__main__":
    engine = PaperTradingEngine()
    engine.run()
