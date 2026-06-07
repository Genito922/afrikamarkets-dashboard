"""
Scheduler APScheduler
  • BRVM scraper    : toutes les 15 min (lun-ven 09h-17h UTC)
  • Intl pre-fetch  : toutes les 6h + run immédiat 60s après démarrage
"""
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler() -> None:
    from backend.app.pipeline.jobs import job_scrape_market, job_prefetch_international, job_warroom

    # ── BRVM : toutes les 15 min (lun-ven 09h-17h UTC) ───────
    scheduler.add_job(
        job_scrape_market,
        trigger=CronTrigger(
            day_of_week="mon-fri", hour="9-17", minute="0,15,30,45", timezone="UTC",
        ),
        id="scrape_brvm_market",
        name="BRVM Market Scraper (15 min)",
        replace_existing=True,
        misfire_grace_time=300,
    )

    # ── Marchés internationaux : toutes les 6h ────────────────
    scheduler.add_job(
        job_prefetch_international,
        trigger=CronTrigger(hour="0,6,12,18", minute="5", timezone="UTC"),
        id="prefetch_intl_6h",
        name="Intl Markets Pre-fetch (6h)",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # ── Run initial 60s après démarrage (cache vide au premier boot) ──
    scheduler.add_job(
        job_prefetch_international,
        trigger=DateTrigger(run_date=datetime.utcnow() + timedelta(seconds=60)),
        id="prefetch_intl_boot",
        name="Intl Markets Pre-fetch (boot)",
        replace_existing=True,
    )

    # ── War Room UEMOA : chaque lundi 06h05 UTC ───────────────
    scheduler.add_job(
        job_warroom,
        trigger=CronTrigger(day_of_week="mon", hour="6", minute="5", timezone="UTC"),
        id="warroom_weekly",
        name="War Room UEMOA (IMF + WorldBank + HDX/ACLED)",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # ── War Room initial 90s après démarrage ──────────────────
    scheduler.add_job(
        job_warroom,
        trigger=DateTrigger(run_date=datetime.utcnow() + timedelta(seconds=90)),
        id="warroom_boot",
        name="War Room UEMOA (boot)",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "[Scheduler] Démarré — BRVM 15 min (lun-ven) · Intl 6h · WarRoom lundi (boot+90s)"
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Arrêté")
