"""
loader.py — Chargement unifie multi-source
  - Binance Futures (crypto) : pagination robuste avec retry
  - yfinance (gold, forex)   : GC=F, EURUSD=X, etc.

Usage :
  from loader import load, REGISTRY
  df = load("BTCUSDT",  days=365*3)
  df = load("XAUUSD",   days=365*3)
  df = load("EURUSD",   days=365*3)
"""
import os
import time
from datetime import datetime, timedelta

import pandas as pd

# ── Registre des actifs ────────────────────────────────────────
# symbol : {"source": "binance"|"yfinance", "class": "crypto"|"commodity"|"forex", "yf_ticker": ...}
REGISTRY: dict[str, dict] = {
    # Crypto Binance Futures
    "BTCUSDT":  {"source": "binance",  "class": "crypto"},
    "ETHUSDT":  {"source": "binance",  "class": "crypto"},
    "SOLUSDT":  {"source": "binance",  "class": "crypto"},
    "XRPUSDT":  {"source": "binance",  "class": "crypto"},
    "DOGEUSDT": {"source": "binance",  "class": "crypto"},
    "BNBUSDT":  {"source": "binance",  "class": "crypto"},
    # Commodities via yfinance
    "XAUUSD":   {"source": "yfinance", "class": "commodity", "yf_ticker": "GC=F"},
    "XAGUSD":   {"source": "yfinance", "class": "commodity", "yf_ticker": "SI=F"},
    "WTIUSD":   {"source": "yfinance", "class": "commodity", "yf_ticker": "CL=F"},
    # Forex via yfinance
    "EURUSD":   {"source": "yfinance", "class": "forex",     "yf_ticker": "EURUSD=X"},
    "GBPUSD":   {"source": "yfinance", "class": "forex",     "yf_ticker": "GBPUSD=X"},
    "USDJPY":   {"source": "yfinance", "class": "forex",     "yf_ticker": "USDJPY=X"},
}

# ── Intervalles yfinance equivalents ──────────────────────────
_YF_INTERVAL = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "4h": "1h",   # 4h n'existe pas, fallback 1h
    "1d": "1d", "1w": "1wk",
}

_API_KEY    = os.environ.get("BINANCE_API_KEY", "")
_API_SECRET = os.environ.get("BINANCE_SECRET_KEY", "")
_PAGE_SIZE  = 1500
_MAX_PAGES  = 40      # 40 × 1500 = 60 000 bougies max


# ── Retry helper ──────────────────────────────────────────────
def _fetch_binance_page(client, symbol: str, interval: str, start: datetime, limit: int) -> list:
    for attempt in range(6):
        try:
            return client.futures_historical_klines(
                symbol=symbol, interval=interval,
                start_str=str(start), limit=limit,
            )
        except Exception as e:
            code = getattr(e, "status_code", None) or getattr(e, "code", None)
            if attempt == 5:
                raise
            wait = max(2 ** attempt, 10 if code in (-1003, 429, 418) else 1)
            print(f"\n    [retry {attempt+1}/5 — {wait}s] {e}", flush=True)
            time.sleep(wait)
    return []


# ── Binance loader ────────────────────────────────────────────
def _load_binance(symbol: str, interval: str, days: int) -> pd.DataFrame:
    from binance.client import Client
    client     = Client(_API_KEY, _API_SECRET, testnet=False)
    cols       = ["timestamp","open","high","low","close","volume",
                  "close_time","quote_vol","trades","tbb","tbq","ignore"]
    all_bars   = []
    start      = datetime.utcnow() - timedelta(days=days)
    pages      = 0

    print(f"  [{symbol}] Binance Futures ({days}j, {interval})...", end="", flush=True)
    while pages < _MAX_PAGES:
        bars = _fetch_binance_page(client, symbol, interval, start, _PAGE_SIZE)
        if not bars:
            break
        if all_bars and bars[0][0] <= all_bars[-1][0]:
            bars = [b for b in bars if b[0] > all_bars[-1][0]]
            if not bars:
                break
        all_bars.extend(bars)
        pages += 1
        start = datetime.utcfromtimestamp(bars[-1][0] / 1000) + timedelta(seconds=1)
        if len(bars) < _PAGE_SIZE:
            break
        if pages % 10 == 0:
            print(f" {len(all_bars):,}", end="", flush=True)
        time.sleep(0.2)

    df = pd.DataFrame(all_bars, columns=cols)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df[~df.index.duplicated(keep="first")]
    for col in ["open","high","low","close","volume"]:
        df[col] = pd.to_numeric(df[col])
    print(f" => {len(df):,} bougies")
    return df[["open","high","low","close","volume"]]


# ── yfinance intraday limits (days) ──────────────────────────
_YF_MAX_DAYS = {
    "1m": 7, "5m": 60, "15m": 60, "30m": 60,
    "1h": 730, "1d": 9999, "1wk": 9999,
}


# ── yfinance loader ───────────────────────────────────────────
def _load_yfinance(symbol: str, interval: str, days: int) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("pip install yfinance")

    meta      = REGISTRY[symbol]
    ticker    = meta.get("yf_ticker", symbol)
    yf_iv     = _YF_INTERVAL.get(interval, "1d")
    end       = datetime.utcnow()

    # yfinance limite les données intraday — clamper pour eviter retour vide
    max_days  = _YF_MAX_DAYS.get(yf_iv, days)
    effective = min(days, max_days)
    if effective < days:
        print(f"  [{symbol}] yfinance: {yf_iv} limite a {max_days}j (demande: {days}j)", flush=True)
    start     = end - timedelta(days=effective)

    print(f"  [{symbol}] yfinance ({ticker}, {effective}j, {yf_iv})...", end="", flush=True)
    raw = yf.download(ticker, start=start, end=end, interval=yf_iv,
                      auto_adjust=True, progress=False)
    if raw.empty:
        raise ValueError(f"yfinance: aucune donnee pour {ticker}")

    raw.index = pd.to_datetime(raw.index)
    raw.index.name = "timestamp"
    # yfinance >=0.2.x peut retourner un MultiIndex (Price, Ticker) — aplatir
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw.columns = [c.lower() for c in raw.columns]
    df = raw[["open","high","low","close","volume"]].copy()
    df = df[~df.index.duplicated(keep="first")].dropna(subset=["close"])
    print(f" => {len(df):,} bougies")
    return df


# ── Point d'entree public ─────────────────────────────────────
def load(symbol: str, interval: str = "30m", days: int = 365) -> pd.DataFrame:
    """
    Charge les OHLCV pour n'importe quel symbol du REGISTRY.
    Retourne un DataFrame index datetime avec colonnes open/high/low/close/volume.
    """
    if symbol not in REGISTRY:
        raise KeyError(f"{symbol} non present dans REGISTRY. Ajouter-le d'abord.")
    meta = REGISTRY[symbol]
    if meta["source"] == "binance":
        return _load_binance(symbol, interval, days)
    else:
        return _load_yfinance(symbol, interval, days)


def asset_class(symbol: str) -> str:
    return REGISTRY.get(symbol, {}).get("class", "crypto")
