"""
Pipeline Jobs — scrape BRVM + persist PostgreSQL/SQLite
                pré-fetch marchés internationaux (yfinance) → intl_market_cache
                war room UEMOA (IMF + World Bank + HDX/ACLED) → intl_market_cache
"""
import json
import logging
import math
from datetime import date, datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.market_models import (
    BrvmAction, BrvmIndex, BrvmMarketSummary, IntlMarketCache,
)
from backend.app.pipeline.scraper import fetch_actions, fetch_indices, fetch_marche

logger = logging.getLogger(__name__)

# Tous les tickers à pré-fetcher (même liste que MarchesInternationaux.jsx)
INTL_TICKERS = [
    "CC=F",     "KC=F",     "GC=F",     "CL=F",       # Commodités
    "^GSPC",    "^FCHI",    "GBL=F",    "ZN=F",        # Indices
    "EURUSD=X", "USDCAD=X", "GBPUSD=X", "USDCHF=X",   # Forex
    "BTC-USD",  "ETH-USD",  "BNB-USD",  "XRP-USD",     # Crypto
]


async def job_scrape_market() -> None:
    """Scrape BRVM et upsert toutes les données en base."""
    today = date.today()
    logger.info("[Pipeline] Scraping BRVM — %s", today)

    try:
        df_actions = fetch_actions()
        indices    = fetch_indices()
        marche     = fetch_marche()
    except Exception as exc:
        logger.error("[Pipeline] Scrape échoué : %s", exc)
        return

    async with AsyncSessionLocal() as session:
        try:
            if not df_actions.empty:
                for _, row in df_actions.iterrows():
                    await _upsert_action(session, row, today)

            for type_idx, items in indices.items():
                for item in items:
                    await _upsert_index(session, item, type_idx, today)

            await _upsert_summary(session, marche, today)

            await session.commit()
            logger.info("[Pipeline] OK — %d actions persistées", len(df_actions))

        except Exception as exc:
            await session.rollback()
            logger.error("[Pipeline] Erreur DB : %s", exc)


# ── helpers upsert ────────────────────────────────────────────────────────────

def _str(val) -> str | None:
    """Convertit NaN pandas/float en None, sinon renvoie str."""
    if val is None:
        return None
    try:
        if math.isnan(float(val)):
            return None
    except (TypeError, ValueError):
        pass
    return str(val) if not isinstance(val, str) else val


def _float(val) -> float | None:
    """Convertit NaN en None."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


async def _upsert_action(session: AsyncSession, row, today: date) -> None:
    res = await session.execute(
        select(BrvmAction).where(
            and_(BrvmAction.symbole == row["symbole"], BrvmAction.date == today)
        )
    )
    record = res.scalar_one_or_none()
    if record:
        record.cours        = _float(row["cours"])
        record.cours_veille = _float(row["cours_veille"])
        record.cours_ouv    = _float(row["cours_ouv"])
        record.variation    = _float(row["variation"])
        record.volume       = int(row["volume"]) if row["volume"] else 0
        record.secteur      = _str(row.get("secteur"))
    else:
        session.add(BrvmAction(
            symbole      = str(row["symbole"]),
            nom          = _str(row["nom"]),
            secteur      = _str(row.get("secteur")),
            cours_ouv    = _float(row["cours_ouv"]),
            cours        = _float(row["cours"]),
            cours_veille = _float(row["cours_veille"]),
            variation    = _float(row["variation"]),
            volume       = int(row["volume"]) if row["volume"] else 0,
            date         = today,
        ))


async def _upsert_index(
    session: AsyncSession, item: dict, type_idx: str, today: date
) -> None:
    res = await session.execute(
        select(BrvmIndex).where(
            and_(BrvmIndex.nom == item["nom"], BrvmIndex.date == today)
        )
    )
    record = res.scalar_one_or_none()
    if record:
        record.cloture      = item["cloture"]
        record.cloture_prec = item["cloture_prec"]
        record.variation    = item["variation"]
        record.var_ytd      = item["var_ytd"]
    else:
        session.add(BrvmIndex(
            nom          = item["nom"],
            type         = type_idx,
            cloture_prec = item["cloture_prec"],
            cloture      = item["cloture"],
            variation    = item["variation"],
            var_ytd      = item["var_ytd"],
            date         = today,
        ))


async def _upsert_summary(
    session: AsyncSession, marche: dict, today: date
) -> None:
    res = await session.execute(
        select(BrvmMarketSummary).where(BrvmMarketSummary.date == today)
    )
    record = res.scalar_one_or_none()
    cap_a  = marche.get("Capitalisation Actions")
    cap_o  = marche.get("Capitalisation des obligations")
    trans  = marche.get("Valeur des transactions")
    if record:
        record.cap_actions_raw     = cap_a
        record.cap_obligations_raw = cap_o
        record.transactions_raw    = trans
    else:
        session.add(BrvmMarketSummary(
            cap_actions_raw     = cap_a,
            cap_obligations_raw = cap_o,
            transactions_raw    = trans,
            date                = today,
        ))


# ── Pré-fetch marchés internationaux ─────────────────────────

async def job_prefetch_international() -> None:
    """Pré-fetch yfinance 365j pour tous les tickers internationaux → intl_market_cache."""
    import asyncio
    from backend.app.routers.intel import _yf_fetch, _ma, _rsi, _mfi

    logger.info("[IntlFetch] Démarrage — %d tickers", len(INTL_TICKERS))
    ok, ko = 0, 0

    for ticker in INTL_TICKERS:
        try:
            df = _yf_fetch(ticker, 365)
            if df.empty:
                logger.warning("[IntlFetch] %s — df vide, skip", ticker)
                ko += 1
                await asyncio.sleep(3)
                continue

            df      = df.dropna(subset=["Close"])
            prices  = [float(v) for v in df["Close"]]
            opens   = [float(v) for v in df["Open"]]
            volumes = [float(v) for v in df["Volume"]]
            dates   = [str(d.date()) for d in df.index]
            n       = len(prices)

            if n == 0:
                ko += 1
                await asyncio.sleep(3)
                continue

            ma16  = _ma(prices, min(16, n))
            ma19  = _ma(prices, min(19, n))
            ma246 = _ma(prices, min(246, n))
            ma361 = _ma(prices, min(361, n))
            rsi   = _rsi(prices)
            mfi   = _mfi(prices, opens, volumes)

            data = []
            for i in range(n):
                data.append({
                    "date":   dates[i],
                    "cours":  round(prices[i], 4),
                    "volume": volumes[i],
                    "ma16":   round(ma16[i], 4)  if ma16[i]  is not None else None,
                    "ma19":   round(ma19[i], 4)  if ma19[i]  is not None else None,
                    "ma246":  round(ma246[i], 4) if ma246[i] is not None else None,
                    "ma361":  round(ma361[i], 4) if ma361[i] is not None else None,
                    "rsi":    rsi[i],
                    "mfi":    mfi[i],
                })

            last = data[-1]
            r, m = last["rsi"] or 50, last["mfi"] or 50
            score, reasons = 0, []
            if r < 30:   score += 2; reasons.append("RSI survendu (<30)")
            elif r < 45: score += 1; reasons.append("RSI zone basse (<45)")
            elif r > 70: score -= 2; reasons.append("RSI suracheté (>70)")
            elif r > 55: score -= 1; reasons.append("RSI zone haute (>55)")
            if m < 20:   score += 2; reasons.append("MFI survendu (<20)")
            elif m > 80: score -= 2; reasons.append("MFI suracheté (>80)")
            if all(v is not None for v in [last["ma16"], last["ma19"], last["ma246"], last["ma361"]]):
                if last["ma16"] > last["ma19"]:
                    score += 1; reasons.append("MA16 > MA19 (haussier court terme)")
                else:
                    score -= 1; reasons.append("MA16 < MA19 (baissier court terme)")
                score += 1 if last["ma19"] > last["ma246"] else -1

            if score >= 3:    sig_label, sig_color = "Achat fort",    "#00CC66"
            elif score >= 1:  sig_label, sig_color = "Achat modéré",  "#FFD700"
            elif score == 0:  sig_label, sig_color = "Neutre",         "#888888"
            elif score >= -2: sig_label, sig_color = "Vente modérée", "#FF6B35"
            else:             sig_label, sig_color = "Vente forte",   "#FF4444"

            payload = json.dumps({
                "ticker": ticker, "days": 365, "count": n,
                "data": data,
                "last": {**last, "label": sig_label, "color": sig_color,
                         "score": score, "reasons": reasons},
            })

            async with AsyncSessionLocal() as session:
                existing = await session.get(IntlMarketCache, ticker)
                if existing:
                    existing.fetched_at = datetime.utcnow()
                    existing.data_json  = payload
                else:
                    session.add(IntlMarketCache(
                        ticker=ticker, fetched_at=datetime.utcnow(), data_json=payload,
                    ))
                await session.commit()

            ok += 1
            logger.info("[IntlFetch] ✓ %s (%d pts)", ticker, n)
            await asyncio.sleep(8)   # Twelve Data free tier : 8 calls/min → ≥7.5s entre appels

        except Exception as exc:
            import traceback
            ko += 1
            logger.error(
                "[IntlFetch] ✗ %s — %s: %s\n%s",
                ticker, type(exc).__name__, exc, traceback.format_exc()
            )
            await asyncio.sleep(3)

    logger.info("[IntlFetch] Terminé — %d OK / %d KO", ok, ko)


# ── War Room UEMOA ────────────────────────────────────────────

async def job_warroom() -> None:
    """
    Construit le payload War Room (IMF + World Bank + HDX/ACLED)
    et l'upsert dans intl_market_cache sous la clé 'WARROOM_UEMOA'.
    Planifié : lundi 06h00 UTC + run initial au boot.
    """
    from backend.app.pipeline.warroom_data import build_warroom_payload

    logger.info("[WarRoom] Démarrage mise à jour données réelles")
    try:
        data = await build_warroom_payload()
        payload = json.dumps({
            "updated_at": datetime.utcnow().isoformat(),
            "source":     "IMF+WorldBank+HDX_ACLED",
            "data":       data,
        })

        async with AsyncSessionLocal() as session:
            existing = await session.get(IntlMarketCache, "WARROOM_UEMOA")
            if existing:
                existing.fetched_at = datetime.utcnow()
                existing.data_json  = payload
            else:
                session.add(IntlMarketCache(
                    ticker     = "WARROOM_UEMOA",
                    fetched_at = datetime.utcnow(),
                    data_json  = payload,
                ))
            await session.commit()

        logger.info("[WarRoom] ✓ Données UEMOA mises à jour (%d pays)", len(data))

    except Exception as exc:
        import traceback
        logger.error("[WarRoom] ✗ %s: %s\n%s", type(exc).__name__, exc, traceback.format_exc())
