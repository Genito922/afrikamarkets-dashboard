"""
allocator.py — Allocation de capital multi-actifs
  Deux modes :
    1. RegimeBased  : poids selon le regime detecte (trend > range > high_vol)
    2. RiskParity   : poids inversement proportionnels a la volatilite realisee

Usage :
  from allocator import RegimeAllocator, RiskParityAllocator
  weights = RegimeAllocator().compute(regimes)          # {"BTCUSDT": 0.35, ...}
  weights = RiskParityAllocator().compute(vols)         # {"BTCUSDT": 0.28, ...}
"""
import numpy as np
import pandas as pd


# ── Poids de base par regime ───────────────────────────────────
_REGIME_WEIGHTS = {
    "trend":    0.40,
    "range":    0.20,
    "high_vol": 0.05,
}

# Max position par actif (evite la concentration)
MAX_WEIGHT = 0.40
MIN_WEIGHT = 0.02


def _normalize(weights: dict) -> dict:
    total = sum(weights.values())
    if total == 0:
        n = len(weights)
        return {k: 1 / n for k in weights}
    return {k: min(v / total, MAX_WEIGHT) for k, v in weights.items()}


class RegimeAllocator:
    """
    Alloue le capital selon le regime de chaque actif.
    Les actifs en tendance recevront plus de capital.
    """

    def compute(self, regimes: dict[str, str]) -> dict[str, float]:
        """
        regimes : {"BTCUSDT": "trend", "ETHUSDT": "range", ...}
        Retourne des poids normalises somme = 1.
        """
        raw = {sym: _REGIME_WEIGHTS.get(reg, 0.10) for sym, reg in regimes.items()}
        return _normalize(raw)


class RiskParityAllocator:
    """
    Ponderation inversement proportionnelle a la volatilite annualisee.
    Les actifs moins volatils recoivent plus de poids.
    """

    def compute(self, vols: dict[str, float]) -> dict[str, float]:
        """
        vols : {"BTCUSDT": 0.62, "XAUUSD": 0.14, ...}  (vol annualisee decimale)
        """
        inv = {sym: 1 / max(v, 1e-6) for sym, v in vols.items()}
        return _normalize(inv)

    @staticmethod
    def realized_vol(equity_series: pd.Series, candles_per_year: float = 17520) -> float:
        """Vol annualisee depuis la serie equity (ou close)."""
        ret = equity_series.pct_change().dropna()
        return float(ret.std() * np.sqrt(candles_per_year)) if len(ret) > 1 else 1.0


class HybridAllocator:
    """
    Combine regime + risk parity :
    poids_final = (regime_weight + riskparity_weight) / 2

    Usage :
      alloc = HybridAllocator()
      w = alloc.compute(regimes, vols)
    """

    def __init__(self):
        self._regime = RegimeAllocator()
        self._rp     = RiskParityAllocator()

    def compute(self, regimes: dict[str, str],
                vols: dict[str, float]) -> dict[str, float]:
        w_regime = self._regime.compute(regimes)
        w_rp     = self._rp.compute(vols)
        combined = {
            sym: (w_regime.get(sym, 0) + w_rp.get(sym, 0)) / 2
            for sym in regimes
        }
        return _normalize(combined)


def print_weights(weights: dict[str, float], label: str = "Allocation"):
    print(f"\n{label}")
    print("-" * 35)
    for sym, w in sorted(weights.items(), key=lambda x: -x[1]):
        bar = "#" * int(w * 30)
        print(f"  {sym:<12} {w*100:5.1f}%  {bar}")
    print(f"  {'TOTAL':<12} {sum(weights.values())*100:.1f}%")
