"""
Scheduler APScheduler — scraping BRVM automatique.
Toutes les 15 minutes pendant les heures de marché (09h–17h WAT = UTC+0).
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler() -> None:
    from backend.app.pipeline.jobs import job_scrape_market

    # Toutes les 15 min, lundi–vendredi, entre 09h00 et 17h00 UTC
    # (BRVM ouvre à 09h WAT ≈ UTC+0 en heure hivernale)
    scheduler.add_job(
        job_scrape_market,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour="9-17",
            minute="0,15,30,45",
            timezone="UTC",
        ),
        id="scrape_brvm_market",
        name="BRVM Market Scraper (15 min)",
        replace_existing=True,
        misfire_grace_time=300,
    )

    scheduler.start()
    logger.info("[Scheduler] Démarré — scraping BRVM toutes les 15 min (lun-ven 09h-17h UTC)")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Arrêté")
