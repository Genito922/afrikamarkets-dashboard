"""
Pipeline Jobs — scrape BRVM + persist PostgreSQL/SQLite
"""
import logging
from datetime import date

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.market_models import BrvmAction, BrvmIndex, BrvmMarketSummary
from backend.app.pipeline.scraper import fetch_actions, fetch_indices, fetch_marche

logger = logging.getLogger(__name__)


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

async def _upsert_action(session: AsyncSession, row, today: date) -> None:
    res = await session.execute(
        select(BrvmAction).where(
            and_(BrvmAction.symbole == row["symbole"], BrvmAction.date == today)
        )
    )
    record = res.scalar_one_or_none()
    if record:
        record.cours        = row["cours"]
        record.cours_veille = row["cours_veille"]
        record.cours_ouv    = row["cours_ouv"]
        record.variation    = row["variation"]
        record.volume       = int(row["volume"])
        record.secteur      = row.get("secteur")
    else:
        session.add(BrvmAction(
            symbole      = row["symbole"],
            nom          = row["nom"],
            secteur      = row.get("secteur"),
            cours_ouv    = row["cours_ouv"],
            cours        = row["cours"],
            cours_veille = row["cours_veille"],
            variation    = row["variation"],
            volume       = int(row["volume"]),
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
