"""
Market Data Router — Afrika Markets Intelligence
GET /market/actions
GET /market/actions/{symbole}/history
GET /market/indices
GET /market/summary
GET /market/mood     → humeur BRVM temps réel (bull/neutre/bear)
POST /market/scrape  (déclenchement manuel)
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import date, timedelta

from backend.app.core.database import get_db
from backend.app.models.market_models import BrvmAction, BrvmIndex, BrvmMarketSummary

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/actions")
async def get_actions_latest(db: AsyncSession = Depends(get_db)):
    """Derniers cours de toutes les actions (date la plus récente en base)."""
    latest_row = await db.execute(
        select(BrvmAction.date).order_by(desc(BrvmAction.date)).limit(1)
    )
    latest_date = latest_row.scalar_one_or_none()
    if not latest_date:
        return {"date": None, "data": []}

    result = await db.execute(
        select(BrvmAction).where(BrvmAction.date == latest_date)
    )
    actions = result.scalars().all()
    return {
        "date": str(latest_date),
        "count": len(actions),
        "data": [
            {
                "symbole":      a.symbole,
                "nom":          a.nom,
                "secteur":      a.secteur,
                "cours":        a.cours,
                "cours_veille": a.cours_veille,
                "cours_ouv":    a.cours_ouv,
                "variation":    a.variation,
                "volume":       a.volume,
            }
            for a in actions
        ],
    }


@router.get("/actions/{symbole}/history")
async def get_action_history(
    symbole: str,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Historique OHLCV d'une action sur N jours (max 365)."""
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(BrvmAction)
        .where(BrvmAction.symbole == symbole.upper(), BrvmAction.date >= since)
        .order_by(BrvmAction.date)
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Aucune donnée pour {symbole.upper()}")
    return {
        "symbole": symbole.upper(),
        "days":    days,
        "count":   len(rows),
        "data": [
            {
                "date":         str(r.date),
                "cours":        r.cours,
                "cours_veille": r.cours_veille,
                "cours_ouv":    r.cours_ouv,
                "variation":    r.variation,
                "volume":       r.volume,
            }
            for r in rows
        ],
    }


@router.get("/indices")
async def get_indices_latest(db: AsyncSession = Depends(get_db)):
    """Derniers indices BRVM (marché + sectoriels)."""
    latest_row = await db.execute(
        select(BrvmIndex.date).order_by(desc(BrvmIndex.date)).limit(1)
    )
    latest_date = latest_row.scalar_one_or_none()
    if not latest_date:
        return {"date": None, "marche": [], "sectoriel": []}

    result = await db.execute(
        select(BrvmIndex).where(BrvmIndex.date == latest_date)
    )
    indices = result.scalars().all()
    out: dict = {"date": str(latest_date), "marche": [], "sectoriel": []}
    for idx in indices:
        entry = {
            "nom":          idx.nom,
            "cloture":      idx.cloture,
            "cloture_prec": idx.cloture_prec,
            "variation":    idx.variation,
            "var_ytd":      idx.var_ytd,
        }
        out[idx.type].append(entry)
    return out


@router.get("/summary")
async def get_market_summary(db: AsyncSession = Depends(get_db)):
    """Résumé global du marché (capitalisation, transactions)."""
    result = await db.execute(
        select(BrvmMarketSummary).order_by(desc(BrvmMarketSummary.date)).limit(1)
    )
    summary = result.scalar_one_or_none()
    if not summary:
        return {"date": None, "data": {}}
    return {
        "date": str(summary.date),
        "data": {
            "Capitalisation Actions":          summary.cap_actions_raw,
            "Capitalisation des obligations":  summary.cap_obligations_raw,
            "Valeur des transactions":         summary.transactions_raw,
        },
    }


@router.get("/top5")
async def get_top5(db: AsyncSession = Depends(get_db)):
    """Top 5 hausses et baisses du jour."""
    latest_row = await db.execute(
        select(BrvmAction.date).order_by(desc(BrvmAction.date)).limit(1)
    )
    latest_date = latest_row.scalar_one_or_none()
    if not latest_date:
        return {"date": None, "top5": [], "flop5": []}

    result = await db.execute(
        select(BrvmAction).where(BrvmAction.date == latest_date)
    )
    actions = result.scalars().all()
    sorted_asc  = sorted(actions, key=lambda a: a.variation or 0)
    sorted_desc = sorted(actions, key=lambda a: a.variation or 0, reverse=True)

    def fmt(a):
        return {"symbole": a.symbole, "nom": a.nom, "secteur": a.secteur,
                "cours": a.cours, "variation": a.variation, "volume": a.volume}

    return {
        "date":  str(latest_date),
        "top5":  [fmt(a) for a in sorted_desc[:5]],
        "flop5": [fmt(a) for a in sorted_asc[:5]],
    }


@router.get("/sectors")
async def get_sectors(db: AsyncSession = Depends(get_db)):
    """Performance sectorielle agrégée (indices sectoriels + stats actions)."""
    from backend.app.models.market_models import BrvmIndex

    # Indices sectoriels
    latest_idx = await db.execute(
        select(BrvmIndex.date).order_by(desc(BrvmIndex.date)).limit(1)
    )
    latest_idx_date = latest_idx.scalar_one_or_none()
    sector_indices = []
    if latest_idx_date:
        idx_res = await db.execute(
            select(BrvmIndex).where(BrvmIndex.date == latest_idx_date, BrvmIndex.type == "sectoriel")
        )
        for idx in idx_res.scalars().all():
            sector_indices.append({
                "nom": idx.nom.replace("BRVM - ", "").replace("BRVM – ", "").replace("BRVM-", ""),
                "cloture": idx.cloture, "variation": idx.variation, "var_ytd": idx.var_ytd,
            })

    # Stats par secteur depuis les actions
    latest_act = await db.execute(
        select(BrvmAction.date).order_by(desc(BrvmAction.date)).limit(1)
    )
    latest_act_date = latest_act.scalar_one_or_none()
    sector_stats: dict = {}
    if latest_act_date:
        act_res = await db.execute(
            select(BrvmAction).where(BrvmAction.date == latest_act_date)
        )
        for a in act_res.scalars().all():
            sec = a.secteur or "Autre"
            if sec not in sector_stats:
                sector_stats[sec] = {"secteur": sec, "nb_titres": 0, "volume_total": 0, "variations": []}
            sector_stats[sec]["nb_titres"] += 1
            sector_stats[sec]["volume_total"] += a.volume or 0
            sector_stats[sec]["variations"].append(a.variation or 0)

    aggregated = []
    for sec, d in sector_stats.items():
        vl = d["variations"]
        aggregated.append({
            "secteur": sec,
            "nb_titres": d["nb_titres"],
            "volume_total": d["volume_total"],
            "variation_moy": round(sum(vl) / len(vl), 2) if vl else 0,
            "nb_up":   sum(1 for v in vl if v > 0),
            "nb_down": sum(1 for v in vl if v < 0),
        })

    return {"date": str(latest_act_date) if latest_act_date else None,
            "sector_indices": sector_indices, "sector_stats": aggregated}


@router.get("/mood")
async def get_market_mood(db: AsyncSession = Depends(get_db)):
    """
    Humeur du marché BRVM — synthèse temps réel.
    Score -4..+4 calculé sur :
      • variation BRVM Composite (principal indice)
      • breadth : ratio titres en hausse / total
      • volume relatif vs moyenne 5j
    Retourne : mood / score / color / label / context / breadth
    """
    from sqlalchemy import func as sa_func

    score   = 0
    reasons = []
    breadth = {"nb_up": 0, "nb_down": 0, "nb_stable": 0, "ratio": 0.5}
    composite_var = None
    brvm30_var    = None

    # ── 1. Variation BRVM Composite ───────────────────────────
    latest_idx = await db.execute(
        select(BrvmIndex.date).order_by(desc(BrvmIndex.date)).limit(1)
    )
    latest_idx_date = latest_idx.scalar_one_or_none()
    if latest_idx_date:
        idx_res = await db.execute(
            select(BrvmIndex).where(BrvmIndex.date == latest_idx_date, BrvmIndex.type == "marche")
        )
        for idx in idx_res.scalars().all():
            nom_lower = idx.nom.lower()
            if "composite" in nom_lower:
                composite_var = idx.variation
                if composite_var is not None:
                    if composite_var > 1.0:
                        score += 2; reasons.append(f"BRVM Composite +{composite_var:.2f}% (fort rebond)")
                    elif composite_var > 0:
                        score += 1; reasons.append(f"BRVM Composite +{composite_var:.2f}% (légère hausse)")
                    elif composite_var < -1.0:
                        score -= 2; reasons.append(f"BRVM Composite {composite_var:.2f}% (forte baisse)")
                    elif composite_var < 0:
                        score -= 1; reasons.append(f"BRVM Composite {composite_var:.2f}% (légère baisse)")
            elif "30" in nom_lower or "brvm 30" in nom_lower.replace("-", " "):
                brvm30_var = idx.variation

    # ── 2. Breadth — proportion titres en hausse ─────────────
    latest_act = await db.execute(
        select(BrvmAction.date).order_by(desc(BrvmAction.date)).limit(1)
    )
    latest_act_date = latest_act.scalar_one_or_none()
    if latest_act_date:
        act_res = await db.execute(
            select(BrvmAction).where(BrvmAction.date == latest_act_date)
        )
        actions = act_res.scalars().all()
        nb_up   = sum(1 for a in actions if (a.variation or 0) > 0.1)
        nb_down = sum(1 for a in actions if (a.variation or 0) < -0.1)
        nb_stab = len(actions) - nb_up - nb_down
        total   = len(actions) or 1
        ratio   = nb_up / total
        breadth = {"nb_up": nb_up, "nb_down": nb_down, "nb_stable": nb_stab,
                   "ratio": round(ratio, 2), "total": total}

        if ratio > 0.60:
            score += 1; reasons.append(f"{nb_up}/{total} titres en hausse (marché large haussier)")
        elif ratio < 0.35:
            score -= 1; reasons.append(f"{nb_down}/{total} titres en baisse (marché large baissier)")
        else:
            reasons.append(f"Marché partagé ({nb_up} ↑ / {nb_down} ↓)")

    # ── 3. Signal BRVM 30 (momentum blue chips) ───────────────
    if brvm30_var is not None:
        if brvm30_var > 0.5:
            score += 1; reasons.append(f"BRVM 30 +{brvm30_var:.2f}% (blue chips haussières)")
        elif brvm30_var < -0.5:
            score -= 1; reasons.append(f"BRVM 30 {brvm30_var:.2f}% (pression sur les blue chips)")

    # ── Label + couleur ───────────────────────────────────────
    if score >= 3:
        mood, color, label = "bull",       "#00CC66", "Marché haussier"
    elif score >= 1:
        mood, color, label = "bull_mild",  "#22c55e", "Légèrement haussier"
    elif score == 0:
        mood, color, label = "neutral",    "#6b7280", "Marché neutre"
    elif score >= -2:
        mood, color, label = "bear_mild",  "#f59e0b", "Légèrement baissier"
    else:
        mood, color, label = "bear",       "#ef4444", "Marché baissier"

    # Contexte macro synthétique
    macro_context = (
        "Marché solide — momentum positif sur l'ensemble des secteurs." if score >= 3 else
        "Tendance positive mais sélective — arbitrages sectoriels en cours." if score >= 1 else
        "Consolidation — équilibre acheteurs / vendeurs, attente de catalyseur." if score == 0 else
        "Pression vendeuse — prudence sur les positions nouvelles." if score >= -2 else
        "Correction significative — surveiller supports clés et liquidité."
    )

    return {
        "mood":            mood,
        "score":           score,
        "color":           color,
        "label":           label,
        "composite_var":   composite_var,
        "brvm30_var":      brvm30_var,
        "breadth":         breadth,
        "reasons":         reasons,
        "macro_context":   macro_context,
        "data_date":       str(latest_act_date) if latest_act_date else None,
        "no_data":         latest_act_date is None,
    }


@router.post("/scrape")
async def trigger_scrape_manual():
    """Déclenche un scraping immédiat (usage admin / dev)."""
    from backend.app.pipeline.jobs import job_scrape_market
    await job_scrape_market()
    return {"status": "ok", "message": "Scraping déclenché"}
