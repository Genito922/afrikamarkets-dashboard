"""
Analysis Router — Afrika Markets Intelligence
GET /analysis/{sym}          → indicateurs techniques complets (MA/RSI/MFI + croisements)
GET /analysis/{sym}/signals  → signal global pondéré
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import date, timedelta
import math

from backend.app.core.database import get_db
from backend.app.models.market_models import BrvmAction

router = APIRouter(prefix="/analysis", tags=["analysis"])


# ── Calculs techniques ────────────────────────────────────────

def _ma(prices: list[float], period: int) -> list[float | None]:
    result = []
    for i in range(len(prices)):
        window = prices[max(0, i - period + 1): i + 1]
        result.append(sum(window) / len(window))
    return result


def _rsi(prices: list[float], period: int = 14) -> list[float | None]:
    if len(prices) < 2:
        return [None] * len(prices)
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]

    alpha = 1.0 / period
    avg_g, avg_l = 0.0, 0.0
    rsi_vals = [None]              # premier prix : pas de delta → None

    for i in range(len(gains)):    # ← range(len(gains)) pour retourner n éléments
        avg_g = alpha * gains[i] + (1 - alpha) * avg_g
        avg_l = alpha * losses[i] + (1 - alpha) * avg_l
        if avg_l == 0:
            rsi_vals.append(100.0)
        else:
            rs = avg_g / avg_l
            rsi_vals.append(round(100 - 100 / (1 + rs), 2))

    return rsi_vals                # len == len(prices) ✓


def _mfi(prices: list[float], opens: list[float], volumes: list[float], period: int = 14) -> list[float | None]:
    n = len(prices)
    highs  = [max(prices[i], opens[i]) for i in range(n)]
    lows   = [min(prices[i], opens[i]) for i in range(n)]
    tps    = [(highs[i] + lows[i] + prices[i]) / 3.0 for i in range(n)]
    raw_mf = [tps[i] * volumes[i] for i in range(n)]

    result = [None] * n
    for i in range(period, n):
        pos_sum = sum(raw_mf[j] for j in range(i - period, i) if j > 0 and tps[j] > tps[j - 1])
        neg_sum = sum(raw_mf[j] for j in range(i - period, i) if j > 0 and tps[j] < tps[j - 1])
        if neg_sum == 0:
            result[i] = 100.0
        elif pos_sum == 0:
            result[i] = 0.0
        else:
            mfr = pos_sum / neg_sum
            result[i] = round(100 - 100 / (1 + mfr), 2)
    return result


def _crossings(fast: list[float | None], slow: list[float | None]) -> dict:
    golden, death = [], []
    for i in range(1, len(fast)):
        f_prev, f_curr = fast[i - 1], fast[i]
        s_prev, s_curr = slow[i - 1], slow[i]
        if None in (f_prev, f_curr, s_prev, s_curr):
            continue
        if (f_prev - s_prev) < 0 and (f_curr - s_curr) >= 0:
            golden.append(i)
        elif (f_prev - s_prev) > 0 and (f_curr - s_curr) <= 0:
            death.append(i)
    return {"golden": golden, "death": death}


def _signal(rsi_v, mfi_v, ma16, ma19, ma246, ma361) -> dict:
    score = 0
    reasons = []
    r = rsi_v or 50
    m = mfi_v or 50

    if r < 30:   score += 2; reasons.append("RSI survendu (<30)")
    elif r < 45: score += 1; reasons.append("RSI zone basse (<45)")
    elif r > 70: score -= 2; reasons.append("RSI suracheté (>70)")
    elif r > 55: score -= 1; reasons.append("RSI zone haute (>55)")

    if m < 20:   score += 2; reasons.append("MFI survendu (<20)")
    elif m > 80: score -= 2; reasons.append("MFI suracheté (>80)")

    if all(x is not None for x in [ma16, ma19, ma246, ma361]):
        if ma16 > ma19 > ma246 > ma361:
            score += 3; reasons.append("Alignement haussier MA16>19>246>361")
        elif ma16 < ma19 < ma246 < ma361:
            score -= 3; reasons.append("Alignement baissier MA16<19<246<361")
        if ma16 > ma19:
            score += 1; reasons.append("MA16 au-dessus MA19 (court terme haussier)")
        else:
            score -= 1; reasons.append("MA16 en-dessous MA19 (court terme baissier)")
        if ma19 > ma246:
            score += 1
        else:
            score -= 1

    if score >= 3:    label, color = "Achat fort",  "#00CC66"
    elif score >= 1:  label, color = "Achat modéré","#FFD700"
    elif score == 0:  label, color = "Neutre",       "#888888"
    elif score >= -2: label, color = "Vente modérée","#FF6B35"
    else:             label, color = "Vente forte",  "#FF4444"

    return {"label": label, "color": color, "score": score, "reasons": reasons}


# ── Endpoints ────────────────────────────────────────────────

@router.get("/{sym}")
async def get_analysis(
    sym: str,
    days: int = Query(default=180, ge=30, le=365),
    rsi_period: int = Query(default=14, ge=5, le=30),
    mfi_period: int = Query(default=14, ge=5, le=30),
    db: AsyncSession = Depends(get_db),
):
    """Indicateurs techniques complets : MA 16/19/246/361 · RSI · MFI · Croisements · Signal."""
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(BrvmAction)
        .where(BrvmAction.symbole == sym.upper(), BrvmAction.date >= since)
        .order_by(BrvmAction.date)
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Aucune donnée pour {sym.upper()}")

    prices  = [r.cours       or 0.0 for r in rows]
    opens   = [r.cours_ouv   or r.cours or 0.0 for r in rows]
    volumes = [float(r.volume or 0) for r in rows]
    dates   = [str(r.date) for r in rows]
    n       = len(prices)

    ma16_vals  = _ma(prices, 16)
    ma19_vals  = _ma(prices, 19)
    ma246_vals = _ma(prices, min(246, n))
    ma361_vals = _ma(prices, min(361, n))
    rsi_vals   = _rsi(prices, rsi_period)
    mfi_vals   = _mfi(prices, opens, volumes, mfi_period)

    data = []
    for i in range(n):
        data.append({
            "date":     dates[i],
            "cours":    round(prices[i], 2),
            "volume":   volumes[i],
            "ma16":     round(ma16_vals[i], 2) if ma16_vals[i] else None,
            "ma19":     round(ma19_vals[i], 2) if ma19_vals[i] else None,
            "ma246":    round(ma246_vals[i], 2) if ma246_vals[i] else None,
            "ma361":    round(ma361_vals[i], 2) if ma361_vals[i] else None,
            "rsi":      rsi_vals[i],
            "mfi":      mfi_vals[i],
        })

    last = data[-1]
    sig  = _signal(last["rsi"], last["mfi"], last["ma16"], last["ma19"], last["ma246"], last["ma361"])

    crossings = {
        "ma16_ma19":   _crossings(ma16_vals, ma19_vals),
        "ma19_ma246":  _crossings(ma19_vals, ma246_vals),
        "ma19_ma361":  _crossings(ma19_vals, ma361_vals),
        "ma246_ma361": _crossings(ma246_vals, ma361_vals),
    }
    # Convertir index → dates pour le frontend
    def idx_to_dates(cross_dict):
        return {
            "golden": [dates[i] for i in cross_dict["golden"] if i < n],
            "death":  [dates[i] for i in cross_dict["death"]  if i < n],
        }

    return {
        "symbole":   sym.upper(),
        "days":      days,
        "count":     n,
        "data":      data,
        "last":      {**last, **sig},
        "crossings": {k: idx_to_dates(v) for k, v in crossings.items()},
    }


@router.get("/{sym}/signals")
async def get_signals(
    sym: str,
    db: AsyncSession = Depends(get_db),
):
    """Signal global rapide pour un titre (derniers 60 jours)."""
    since = date.today() - timedelta(days=60)
    result = await db.execute(
        select(BrvmAction)
        .where(BrvmAction.symbole == sym.upper(), BrvmAction.date >= since)
        .order_by(BrvmAction.date)
    )
    rows = result.scalars().all()

    # Fallback : chercher au moins la dernière cotation
    if not rows:
        latest = await db.execute(
            select(BrvmAction)
            .where(BrvmAction.symbole == sym.upper())
            .order_by(desc(BrvmAction.date))
            .limit(1)
        )
        row = latest.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail=f"Titre {sym.upper()} introuvable")
        variation = row.variation or 0
        if variation > 3:    label, color = "Hausse forte",     "#00CC66"
        elif variation > 0:  label, color = "Légère hausse",    "#4ade80"
        elif variation == 0: label, color = "Stable",           "#888888"
        elif variation > -3: label, color = "Légère baisse",    "#FF6B35"
        else:                label, color = "Baisse forte",     "#FF4444"
        return {"symbole": sym.upper(), "signal": label, "color": color, "score": 0,
                "reasons": [], "cours": row.cours, "variation": row.variation}

    prices  = [r.cours or 0.0 for r in rows]
    opens   = [r.cours_ouv or r.cours or 0.0 for r in rows]
    volumes = [float(r.volume or 0) for r in rows]
    n = len(prices)

    ma16  = _ma(prices, min(16,  n))[-1]
    ma19  = _ma(prices, min(19,  n))[-1]
    ma246 = _ma(prices, min(246, n))[-1]
    ma361 = _ma(prices, min(361, n))[-1]
    rsi   = _rsi(prices)[-1]
    mfi   = _mfi(prices, opens, volumes)[-1]

    sig = _signal(rsi, mfi, ma16, ma19, ma246, ma361)
    last_row = rows[-1]
    return {
        "symbole":   sym.upper(),
        "signal":    sig["label"],
        "color":     sig["color"],
        "score":     sig["score"],
        "reasons":   sig["reasons"],
        "cours":     last_row.cours,
        "variation": last_row.variation,
        "rsi":       rsi,
        "mfi":       mfi,
        "ma16":      ma16,
        "ma19":      ma19,
        "ma246":     ma246,
        "ma361":     ma361,
    }
