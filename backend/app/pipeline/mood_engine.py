"""
BRVM Market Mood Engine — Sentiment aggregator multi-signal niveau 2

Régimes de marché détectés :
  trending_up    — tendance haussière établie (7j)
  trending_down  — tendance baissière établie (7j)
  volatile       — volatilité élevée, signaux contradictoires
  sideways       — consolidation, faible directionnalité
  low_liquidity  — volumes anormalement faibles (<40% moyenne 10j)

Signaux intégrés (pondération dynamique selon régime) :
  1. BRVM Composite variation     (poids: 2-3 selon régime)
  2. BRVM 30 variation            (blue chips)
  3. Breadth ratio titres         (avance/recul/stable)
  4. Volume relatif 5j            (qualité du signal)
  5. USD/XOF proxy depuis cache   (signal macro externe)
  6. Secteur leader               (driver sectoriel)
"""
import json
import logging
import math
import statistics
from datetime import date, timedelta

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.market_models import BrvmAction, BrvmIndex, IntlMarketCache

logger = logging.getLogger(__name__)


# ── Libellés ─────────────────────────────────────────────────

REGIME_META = {
    "trending_up":    {"label": "Tendance haussière",  "color": "#22c55e", "icon": "📈"},
    "trending_down":  {"label": "Tendance baissière",  "color": "#ef4444", "icon": "📉"},
    "volatile":       {"label": "Marché volatile",     "color": "#f59e0b", "icon": "⚡"},
    "sideways":       {"label": "Consolidation",       "color": "#6b7280", "icon": "↔"},
    "low_liquidity":  {"label": "Faible liquidité",    "color": "#8b5cf6", "icon": "🔇"},
}

MOOD_META = {
    4:  {"label": "Très haussier",       "color": "#00CC66"},
    3:  {"label": "Haussier",            "color": "#22c55e"},
    2:  {"label": "Légèrement haussier", "color": "#84cc16"},
    1:  {"label": "Positif",             "color": "#a3e635"},
    0:  {"label": "Neutre",              "color": "#6b7280"},
    -1: {"label": "Légèrement négatif",  "color": "#f59e0b"},
    -2: {"label": "Prudent",             "color": "#fb923c"},
    -3: {"label": "Baissier",            "color": "#ef4444"},
    -4: {"label": "Très baissier",       "color": "#dc2626"},
}


def _mood_meta(score: int) -> dict:
    clamped = max(-4, min(4, score))
    return MOOD_META.get(clamped, MOOD_META[0])


# ── Détection régime ──────────────────────────────────────────

def _detect_regime(
    variations_7d: list[float],
    breadth_ratio: float,
    volume_ratio: float,
) -> str:
    """
    Classifie le régime de marché à partir des données 7 jours.

    volume_ratio = volume_today / avg_volume_5j
    breadth_ratio = nb_up / total_titres
    """
    if not variations_7d:
        return "sideways"

    # Liquidité anormalement faible
    if volume_ratio < 0.4:
        return "low_liquidity"

    try:
        vol = statistics.stdev(variations_7d) if len(variations_7d) >= 2 else 0
    except statistics.StatisticsError:
        vol = 0

    avg = sum(variations_7d) / len(variations_7d)

    # Marché volatile : dispersion élevée
    if vol > 1.5:
        return "volatile"

    # Tendances établies
    if avg > 0.25 and breadth_ratio > 0.55:
        return "trending_up"
    if avg < -0.25 and breadth_ratio < 0.40:
        return "trending_down"

    return "sideways"


# ── Pondérations dynamiques par régime ───────────────────────

WEIGHTS = {
    # (composite_w, breadth_w, brvm30_w, volume_bonus, macro_w)
    "trending_up":   (3, 2, 1, 1, 1),
    "trending_down": (3, 2, 1, 1, 1),
    "volatile":      (1, 2, 1, 0, 1),  # breadth plus fiable en volatilité
    "sideways":      (2, 1, 2, 0, 2),  # macro & blue chips plus pertinents
    "low_liquidity": (1, 1, 1, 0, 2),  # signaux faibles, macro domine
}


# ── Drivers sectoriels ────────────────────────────────────────

async def _sector_drivers(session: AsyncSession) -> dict:
    """Top secteurs en hausse / baisse du jour."""
    latest = await session.execute(
        select(BrvmAction.date).order_by(desc(BrvmAction.date)).limit(1)
    )
    d = latest.scalar_one_or_none()
    if not d:
        return {"top": [], "flop": []}

    rows = (await session.execute(
        select(BrvmAction).where(BrvmAction.date == d)
    )).scalars().all()

    secs: dict[str, list[float]] = {}
    for r in rows:
        s = r.secteur or "Autre"
        secs.setdefault(s, []).append(r.variation or 0)

    agg = [
        {"secteur": s, "variation_moy": round(sum(v)/len(v), 2), "nb": len(v)}
        for s, v in secs.items() if len(v) >= 2
    ]
    agg.sort(key=lambda x: x["variation_moy"], reverse=True)
    return {
        "top":  [a for a in agg if a["variation_moy"] > 0][:3],
        "flop": [a for a in agg[::-1] if a["variation_moy"] < 0][:2],
        "all":  agg,
    }


# ── Signal macro : USD/XOF via cache EURUSD ──────────────────

async def _macro_signal(session: AsyncSession) -> dict | None:
    """
    Lit le cache EURUSD=X → calcule USD/XOF ≈ 655.957 / EURUSD.
    Retourne signal macro si variation notable.
    """
    try:
        row = await session.get(IntlMarketCache, "EURUSD=X")
        if not row:
            return None
        data = json.loads(row.data_json)
        prices = [d["cours"] for d in data.get("data", [])[-5:]]
        if len(prices) < 2:
            return None
        change_pct = (prices[-1] - prices[-2]) / prices[-2] * 100
        usd_xof = round(655.957 / prices[-1], 1)
        return {
            "eurusd":   round(prices[-1], 4),
            "usd_xof":  usd_xof,
            "change_pct": round(change_pct, 3),
            "signal":   1 if change_pct > 0.3 else (-1 if change_pct < -0.3 else 0),
        }
    except Exception:
        return None


# ── Texte d'interprétation naturel ────────────────────────────

def _build_interpretation(
    regime: str,
    score: int,
    composite_var: float | None,
    breadth: dict,
    volume_ratio: float,
    sector_drivers: dict,
    macro: dict | None,
) -> str:
    """Génère un paragraphe d'interprétation contextualisé."""
    lines = []
    label = _mood_meta(score)["label"]

    # Phrase d'accroche
    regime_meta = REGIME_META[regime]
    lines.append(
        f"Le marché BRVM est en **{regime_meta['label'].lower()}** ({label.lower()})."
    )

    # Drivers sectoriels
    top = sector_drivers.get("top", [])
    flop = sector_drivers.get("flop", [])
    if top:
        sectors_up = " · ".join(f"{s['secteur']} +{s['variation_moy']}%" for s in top[:2])
        lines.append(f"Secteurs porteurs : {sectors_up}.")
    if flop:
        sectors_down = " · ".join(f"{s['secteur']} {s['variation_moy']}%" for s in flop[:1])
        lines.append(f"Pression sur : {sectors_down}.")

    # Breadth
    ratio = breadth.get("ratio", 0.5)
    nb_up = breadth.get("nb_up", 0)
    total = breadth.get("total", 1)
    if ratio > 0.65:
        lines.append(f"Marché large positif : {nb_up}/{total} titres progressent.")
    elif ratio < 0.35:
        lines.append(f"Marché large négatif : seuls {nb_up}/{total} titres en hausse.")
    else:
        lines.append(f"Marché partagé ({nb_up}/{total} titres en hausse).")

    # Volume
    if volume_ratio < 0.5:
        lines.append("⚠ Volume faible — signal fragile, attendre confirmation.")
    elif volume_ratio > 1.5:
        lines.append("Volume élevé — mouvement soutenu par les échanges.")

    # Signal macro
    if macro:
        if abs(macro["change_pct"]) > 0.3:
            direction = "appréciation" if macro["change_pct"] > 0 else "dépréciation"
            lines.append(
                f"USD/XOF à {macro['usd_xof']} ({direction} EUR/USD de {abs(macro['change_pct']):.2f}%)."
            )

    # Conclusion selon régime
    if regime == "low_liquidity":
        lines.append("Prudence : la faible liquidité amplifie les mouvements de cours.")
    elif regime == "volatile":
        lines.append("Volatilité élevée — les niveaux de support/résistance sont clés.")
    elif regime == "trending_up" and score >= 2:
        lines.append("Tendance soutenue — momentum favorable aux positions longues.")
    elif regime == "trending_down" and score <= -2:
        lines.append("Tendance négative confirmée — gérer les expositions avec rigueur.")

    return " ".join(lines)


# ── Fonction principale ───────────────────────────────────────

async def compute_market_mood(session: AsyncSession) -> dict:
    """
    Point d'entrée principal — retourne l'analyse complète du marché BRVM.
    Temps d'exécution typique : 80–150 ms (4 requêtes DB légères).
    """
    # ── 1. Indices BRVM (date la plus récente) ─────────────
    latest_idx = (await session.execute(
        select(BrvmIndex.date).order_by(desc(BrvmIndex.date)).limit(1)
    )).scalar_one_or_none()

    composite_var: float | None = None
    brvm30_var:    float | None = None

    if latest_idx:
        for idx in (await session.execute(
            select(BrvmIndex).where(BrvmIndex.date == latest_idx, BrvmIndex.type == "marche")
        )).scalars().all():
            nom_l = idx.nom.lower()
            if "composite" in nom_l:
                composite_var = idx.variation
            elif "30" in nom_l or "brvm 30" in nom_l.replace("-", " "):
                brvm30_var = idx.variation

    # ── 2. BRVM Composite 7 derniers jours (régime) ────────
    since_7 = date.today() - timedelta(days=14)
    hist = (await session.execute(
        select(BrvmIndex)
        .where(BrvmIndex.nom.ilike("%composite%"), BrvmIndex.date >= since_7)
        .order_by(BrvmIndex.date.desc())
        .limit(7)
    )).scalars().all()
    variations_7d = [h.variation for h in hist if h.variation is not None]

    # ── 3. Breadth + volume ────────────────────────────────
    latest_act = (await session.execute(
        select(BrvmAction.date).order_by(desc(BrvmAction.date)).limit(1)
    )).scalar_one_or_none()

    breadth:      dict   = {"nb_up": 0, "nb_down": 0, "nb_stable": 0, "ratio": 0.5, "total": 0}
    volume_today: float  = 0
    volume_ratio: float  = 1.0

    if latest_act:
        actions = (await session.execute(
            select(BrvmAction).where(BrvmAction.date == latest_act)
        )).scalars().all()

        nb_up   = sum(1 for a in actions if (a.variation or 0) >  0.1)
        nb_down = sum(1 for a in actions if (a.variation or 0) < -0.1)
        nb_stab = len(actions) - nb_up - nb_down
        total   = len(actions) or 1
        breadth = {
            "nb_up": nb_up, "nb_down": nb_down, "nb_stable": nb_stab,
            "ratio": round(nb_up / total, 3), "total": total,
        }
        volume_today = sum(a.volume or 0 for a in actions)

        # Volume moyen 5j
        since_5 = latest_act - timedelta(days=10)
        hist_vol = (await session.execute(
            select(BrvmAction.date, BrvmAction.volume)
            .where(BrvmAction.date >= since_5, BrvmAction.date < latest_act)
            .order_by(desc(BrvmAction.date))
        )).all()
        dates_seen: dict[date, float] = {}
        for row in hist_vol:
            dates_seen[row.date] = dates_seen.get(row.date, 0) + (row.volume or 0)
        if dates_seen:
            avg_vol = sum(dates_seen.values()) / len(dates_seen)
            volume_ratio = volume_today / avg_vol if avg_vol > 0 else 1.0

    # ── 4. Détection régime ────────────────────────────────
    regime = _detect_regime(variations_7d, breadth["ratio"], volume_ratio)
    w_comp, w_bread, w_brvm30, w_vol_bonus, w_macro = WEIGHTS[regime]

    # ── 5. Score dynamique ─────────────────────────────────
    score   = 0
    reasons = []

    # Signal 1 : BRVM Composite
    if composite_var is not None:
        if composite_var > 1.0:
            s = w_comp; reasons.append(f"BRVM Composite +{composite_var:.2f}% (fort rebond)")
        elif composite_var > 0.2:
            s = max(1, w_comp - 1); reasons.append(f"BRVM Composite +{composite_var:.2f}%")
        elif composite_var < -1.0:
            s = -w_comp; reasons.append(f"BRVM Composite {composite_var:.2f}% (forte baisse)")
        elif composite_var < -0.2:
            s = -max(1, w_comp - 1); reasons.append(f"BRVM Composite {composite_var:.2f}%")
        else:
            s = 0; reasons.append(f"BRVM Composite stable ({composite_var:+.2f}%)")
        score += s

    # Signal 2 : Breadth
    ratio = breadth["ratio"]
    if ratio > 0.65:
        score += w_bread; reasons.append(f"Marché large positif ({int(ratio*100)}% titres en hausse)")
    elif ratio > 0.50:
        score += 1; reasons.append(f"Majorité de titres en hausse ({int(ratio*100)}%)")
    elif ratio < 0.30:
        score -= w_bread; reasons.append(f"Marché large négatif ({int((1-ratio)*100)}% titres en baisse)")
    elif ratio < 0.45:
        score -= 1; reasons.append(f"Majorité de titres en baisse ({int((1-ratio)*100)}%)")

    # Signal 3 : BRVM 30
    if brvm30_var is not None:
        if brvm30_var > 0.5:
            score += w_brvm30; reasons.append(f"Blue chips haussières (BRVM 30 +{brvm30_var:.2f}%)")
        elif brvm30_var < -0.5:
            score -= w_brvm30; reasons.append(f"Pression sur les blue chips (BRVM 30 {brvm30_var:.2f}%)")

    # Signal 4 : Volume (bonus/malus qualité signal)
    if volume_ratio > 1.5:
        score += w_vol_bonus; reasons.append("Volume élevé — mouvement confirmé")
    elif volume_ratio < 0.4:
        score = max(-2, min(2, score))  # Plafonne le score en low liquidity

    # ── 6. Signal macro USD/XOF ────────────────────────────
    macro = await _macro_signal(session)
    if macro and w_macro > 0:
        if macro["signal"] > 0:
            score += w_macro; reasons.append(f"EUR/USD +{macro['change_pct']:.2f}% → XOF renforcé")
        elif macro["signal"] < 0:
            score -= w_macro; reasons.append(f"EUR/USD {macro['change_pct']:.2f}% → XOF affaibli")

    # ── 7. Secteurs drivers ────────────────────────────────
    sector_drv = await _sector_drivers(session)

    # ── 8. Interprétation ─────────────────────────────────
    score = max(-4, min(4, score))
    interpretation = _build_interpretation(
        regime, score, composite_var, breadth, volume_ratio, sector_drv, macro
    )
    mood_m = _mood_meta(score)

    return {
        "mood":           _score_to_mood_key(score),
        "score":          score,
        "label":          mood_m["label"],
        "color":          mood_m["color"],
        "regime": {
            "type":       regime,
            "label":      REGIME_META[regime]["label"],
            "color":      REGIME_META[regime]["color"],
            "icon":       REGIME_META[regime]["icon"],
        },
        "composite_var":  composite_var,
        "brvm30_var":     brvm30_var,
        "breadth":        breadth,
        "volume_ratio":   round(volume_ratio, 2),
        "macro":          macro,
        "sector_drivers": sector_drv,
        "reasons":        reasons,
        "interpretation": interpretation,
        "data_date":      str(latest_act) if latest_act else None,
        "no_data":        latest_act is None,
    }


def _score_to_mood_key(score: int) -> str:
    if score >= 3:   return "bull"
    if score >= 1:   return "bull_mild"
    if score == 0:   return "neutral"
    if score >= -2:  return "bear_mild"
    return "bear"
