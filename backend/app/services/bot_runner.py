"""
BotRunner — gestionnaire asyncio de tâches de trading multi-tenant.

Un asyncio.Task par bot actif.
Restart automatique en cas de crash (max 3 fois par session).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.models import TradingBot, UserBrokerCredential

logger = logging.getLogger(__name__)

# Registre global : bot_id → _BotEntry
_registry: dict[str, "_BotEntry"] = {}


@dataclass
class _BotEntry:
    bot_id: str
    task: asyncio.Task
    strategy: object        # SMACrossoverStrategy instance
    restart_count: int = 0
    max_restarts: int = 3
    bot_snapshot: "TradingBot" = None
    cred_snapshot: "UserBrokerCredential | None" = None


# ── Public API ────────────────────────────────────────────────────────────────

async def start_bot(bot: "TradingBot", cred: "UserBrokerCredential | None") -> None:
    """Lance un bot dans un asyncio.Task. Idempotent si déjà en cours."""
    if bot.id in _registry:
        logger.warning("[runner] Bot %s déjà dans le registre — skip", bot.id)
        return

    strategy = _build_strategy(bot, cred)
    task = asyncio.create_task(
        _run_with_restart(bot.id, strategy, bot, cred),
        name=f"bot-{bot.id[:8]}",
    )
    _registry[bot.id] = _BotEntry(
        bot_id=bot.id,
        task=task,
        strategy=strategy,
        bot_snapshot=bot,
        cred_snapshot=cred,
    )
    logger.info("[runner] Bot %s démarré (task=%s)", bot.id, task.get_name())


async def stop_bot(bot_id: str) -> None:
    """Arrête proprement le bot et le retire du registre."""
    entry = _registry.pop(bot_id, None)
    if not entry:
        return
    entry.strategy.stop()
    entry.task.cancel()
    try:
        await asyncio.wait_for(asyncio.shield(entry.task), timeout=5.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass
    logger.info("[runner] Bot %s arrêté", bot_id)


def is_running(bot_id: str) -> bool:
    return bot_id in _registry and not _registry[bot_id].task.done()


def list_running() -> list[str]:
    return [bid for bid, e in _registry.items() if not e.task.done()]


# ── Internal ──────────────────────────────────────────────────────────────────

def _build_strategy(bot: "TradingBot", cred):
    from backend.app.services.strategies.sma_crossover import SMACrossoverStrategy
    STRATEGY_MAP = {
        "sma_crossover": SMACrossoverStrategy,
    }
    cls = STRATEGY_MAP.get(bot.strategy, SMACrossoverStrategy)
    return cls(bot, cred)


async def _run_with_restart(
    bot_id: str,
    strategy,
    bot: "TradingBot",
    cred,
) -> None:
    """Wrapper qui redémarre la stratégie jusqu'à max_restarts."""
    entry = _registry.get(bot_id)

    while True:
        try:
            await strategy.run()
            # Sortie propre (stop() appelé) → ne pas redémarrer
            break
        except asyncio.CancelledError:
            break
        except Exception as exc:
            if not entry:
                break
            entry.restart_count += 1
            logger.error(
                "[runner] Bot %s crash #%d/%d: %s",
                bot_id, entry.restart_count, entry.max_restarts, exc,
            )
            if entry.restart_count >= entry.max_restarts:
                logger.error("[runner] Bot %s max restarts atteint — abandon", bot_id)
                await _mark_bot_error(bot_id, str(exc))
                _registry.pop(bot_id, None)
                break

            # Back-off exponentiel : 5s, 10s, 20s
            backoff = 5 * (2 ** (entry.restart_count - 1))
            logger.info("[runner] Bot %s redémarrage dans %ds...", bot_id, backoff)
            await asyncio.sleep(backoff)

            # Recréer la stratégie
            strategy = _build_strategy(entry.bot_snapshot, entry.cred_snapshot)
            entry.strategy = strategy


async def _mark_bot_error(bot_id: str, error_msg: str) -> None:
    """Met à jour le statut en DB après dépassement max_restarts."""
    try:
        from backend.app.core.database import AsyncSessionLocal
        from sqlalchemy import select
        from backend.app.models.models import TradingBot, BotStatusEnum

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(TradingBot).where(TradingBot.id == bot_id))
            bot = result.scalar_one_or_none()
            if bot:
                bot.status = BotStatusEnum.ERROR
                bot.last_error = error_msg[:500]
                bot.stopped_at = datetime.now(timezone.utc)
                await db.commit()
    except Exception as e:
        logger.error("[runner] Impossible de marquer bot %s en erreur: %s", bot_id, e)
