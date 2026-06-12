"""
detector.py — RegimeDetector multi-asset-class
  Trois regimes : trend | range | high_vol
  Seuils adaptatifs selon la classe d'actif (crypto / commodity / forex)

Usage :
  from detector import RegimeDetector
  rd = RegimeDetector()
  df = rd.detect(df, asset_class="crypto")   # ajoute colonne "regime"
"""
import numpy as np
import pandas as pd


# ── Seuils par classe d'actif ─────────────────────────────────
# atr_pct_pctile : quantile du rolling ATR% qui definit "volatil"
# adx_trend      : seuil ADX au-dessus duquel on est en tendance
# adx_range      : seuil ADX en-dessous duquel on est en range
_CLASS_PARAMS = {
    "crypto": {
        "atr_pct_pctile": 0.85,   # percentile rolling — en 4H: 504 bars ≈ 84 jours
        "adx_trend":      28,     # hausse: 22->28  (eviter faux trends en 30m/4H)
        "adx_range":      22,     # hausse: 18->22
        "atr_roll":       504,    # 504×4H = 2016h ≈ 84 jours (au lieu de 5j en 30m)
    },
    "commodity": {
        "atr_pct_pctile": 0.80,
        "adx_trend":      25,     # hausse: 20->25
        "adx_range":      20,     # hausse: 15->20
        "atr_roll":       252,    # 252×4H ≈ 42 jours
    },
    "forex": {
        "atr_pct_pctile": 0.80,
        "adx_trend":      25,
        "adx_range":      20,
        "atr_roll":       252,
    },
}
_DEFAULT_PARAMS = _CLASS_PARAMS["crypto"]


class RegimeDetector:
    """
    Detecte le regime de marche barre par barre.

    Logique :
      1. ATR% > percentile(85eme, rolling 252) -> high_vol
      2. ADX > adx_trend                        -> trend
      3. Sinon                                   -> range
    """

    def detect(self, df: pd.DataFrame, asset_class: str = "crypto") -> pd.DataFrame:
        p   = _CLASS_PARAMS.get(asset_class, _DEFAULT_PARAMS)
        out = df.copy()

        out["atr"]     = self._atr(out)
        out["atr_pct"] = out["atr"] / out["close"]
        out["adx"]     = self._adx(out)

        # Seuil volatilite : percentile rolling sur p["atr_roll"] barres
        out["atr_pct_thresh"] = (
            out["atr_pct"]
            .rolling(p["atr_roll"], min_periods=30)
            .quantile(p["atr_pct_pctile"])
        )

        out["regime"] = "range"
        out.loc[out["adx"] > p["adx_trend"], "regime"] = "trend"
        out.loc[out["atr_pct"] > out["atr_pct_thresh"], "regime"] = "high_vol"

        return out

    # ── Indicateurs bruts ─────────────────────────────────────
    @staticmethod
    def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        h  = df["high"]
        l  = df["low"]
        pc = df["close"].shift(1)
        tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
        return tr.ewm(span=period, adjust=False).mean()

    @staticmethod
    def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        h  = df["high"]
        l  = df["low"]
        ph = h.shift(1)
        pl = l.shift(1)

        dm_p = np.where((h - ph) > (pl - l), np.maximum(h - ph, 0), 0)
        dm_m = np.where((pl - l) > (h - ph), np.maximum(pl - l, 0), 0)

        dm_p = pd.Series(dm_p, index=df.index).ewm(span=period, adjust=False).mean()
        dm_m = pd.Series(dm_m, index=df.index).ewm(span=period, adjust=False).mean()

        atr  = RegimeDetector._atr(df, period)
        atr  = atr.replace(0, np.nan)
        di_p = 100 * dm_p / atr
        di_m = 100 * dm_m / atr
        dx   = (100 * (di_p - di_m).abs() / (di_p + di_m).replace(0, np.nan))
        adx  = dx.ewm(span=period, adjust=False).mean()
        return adx.fillna(0)

    # ── Distribution des regimes sur une periode ──────────────
    @staticmethod
    def regime_stats(df: pd.DataFrame) -> dict:
        counts = df["regime"].value_counts()
        total  = len(df)
        return {r: round(counts.get(r, 0) / total * 100, 1)
                for r in ["trend", "range", "high_vol"]}
