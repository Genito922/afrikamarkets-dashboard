"""
strategies.py — Strategies de trading modulaires
  - SMATrend        : SMA triple crossover (trend following)
  - MeanReversion   : RSI + Bollinger (mean reversion)
  - RiskOff         : flat — utilise en regime high_vol

Chaque strategie expose :
  .generate(df) -> df avec colonne "signal" (-1 / 0 / 1)
                  et colonne "position" (signal decale d'1 barre)
"""
import pandas as pd
import numpy as np


class SMATrend:
    """
    Triple SMA crossover.
    Signal LONG  : sma_s > sma_m > sma_l
    Signal SHORT : sma_s < sma_m < sma_l
    """
    def __init__(self, sma_s: int = 16, sma_m: int = 246, sma_l: int = 361):
        self.sma_s = sma_s
        self.sma_m = sma_m
        self.sma_l = sma_l

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["sma_s"] = out["close"].rolling(self.sma_s).mean()
        out["sma_m"] = out["close"].rolling(self.sma_m).mean()
        out["sma_l"] = out["close"].rolling(self.sma_l).mean()
        out.dropna(subset=["sma_s","sma_m","sma_l"], inplace=True)

        out["signal"] = 0
        # Filtre macro : n'entre en LONG que si prix > tendance lourde (sma_l)
        # Evite les faux signaux quand les MAs sont positives mais le prix a deja retrace
        out.loc[
            (out.sma_s > out.sma_m) & (out.sma_m > out.sma_l) & (out.close > out.sma_l),
            "signal"
        ] =  1
        out.loc[
            (out.sma_s < out.sma_m) & (out.sma_m < out.sma_l) & (out.close < out.sma_l),
            "signal"
        ] = -1
        out["position"] = out["signal"].shift(1).fillna(0)
        return out

    def __repr__(self):
        return f"SMATrend({self.sma_s}/{self.sma_m}/{self.sma_l})"


class MeanReversion:
    """
    RSI mean reversion + confirmation Bollinger.
    Signal LONG  : RSI < os AND price < lower_band
    Signal SHORT : RSI > ob AND price > upper_band
    Position fermee quand RSI revient vers 50.
    """
    def __init__(self, rsi_period: int = 14, ob: int = 65, os: int = 35,
                 bb_period: int = 20, bb_std: float = 2.0):
        self.rsi_period = rsi_period
        self.ob         = ob
        self.os         = os
        self.bb_period  = bb_period
        self.bb_std     = bb_std

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["rsi"]    = self._rsi(out["close"])
        out["bb_mid"] = out["close"].rolling(self.bb_period).mean()
        out["bb_std"] = out["close"].rolling(self.bb_period).std()
        out["bb_up"]  = out["bb_mid"] + self.bb_std * out["bb_std"]
        out["bb_lo"]  = out["bb_mid"] - self.bb_std * out["bb_std"]
        out.dropna(subset=["rsi","bb_mid"], inplace=True)

        out["signal"] = 0
        # Long : oversold + sous bande basse
        out.loc[(out.rsi < self.os) & (out.close < out.bb_lo), "signal"] =  1
        # Short : overbought + sur bande haute
        out.loc[(out.rsi > self.ob) & (out.close > out.bb_up), "signal"] = -1
        out["position"] = out["signal"].shift(1).fillna(0)
        return out

    def _rsi(self, series: pd.Series) -> pd.Series:
        delta = series.diff()
        gain  = delta.clip(lower=0).ewm(span=self.rsi_period, adjust=False).mean()
        loss  = (-delta.clip(upper=0)).ewm(span=self.rsi_period, adjust=False).mean()
        rs    = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def __repr__(self):
        return f"MeanReversion(RSI{self.rsi_period}, OB{self.ob}/OS{self.os})"


class RiskOff:
    """Strategie neutre — flat sur tous les bars (regime high_vol)."""

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["signal"]   = 0
        out["position"] = 0
        return out

    def __repr__(self):
        return "RiskOff(flat)"


# ── Router : regime -> strategie ───────────────────────────────
class StrategyRouter:
    """
    Selectionne la strategie a appliquer selon le regime et la classe d'actif.

    Matrice par defaut :
      regime      | crypto       | commodity    | forex
      trend       | SMATrend     | SMATrend     | SMATrend
      range       | MeanReversion| MeanReversion| MeanReversion
      high_vol    | RiskOff      | RiskOff      | RiskOff
    """

    def __init__(self,
                 sma_s: int = 16, sma_m: int = 246, sma_l: int = 361,
                 rsi_ob: int = 65, rsi_os: int = 35):
        self._trend = SMATrend(sma_s, sma_m, sma_l)
        self._mr    = MeanReversion(ob=rsi_ob, os=rsi_os)
        self._flat  = RiskOff()

    def get(self, regime: str, asset_class: str = "crypto"):
        if regime == "high_vol":
            return self._flat
        if regime == "trend":
            return self._trend
        # range
        return self._mr

    def apply_regime_aware(self, df: pd.DataFrame, asset_class: str = "crypto") -> pd.DataFrame:
        """
        Applique la bonne strategie segment par segment selon df["regime"].
        Requiert que df contienne deja la colonne "regime" (sortie de RegimeDetector).
        """
        if "regime" not in df.columns:
            raise ValueError("df doit contenir la colonne 'regime' (RegimeDetector.detect)")

        segments = []
        for regime, grp in df.groupby("regime", sort=False):
            strat  = self.get(regime, asset_class)
            result = strat.generate(grp)
            segments.append(result)

        out = pd.concat(segments).sort_index()
        # Re-shifter les positions apres concat pour eviter lookahead
        out["position"] = out["signal"].shift(1).fillna(0)
        return out
