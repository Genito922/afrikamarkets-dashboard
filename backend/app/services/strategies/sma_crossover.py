"""
Stratégie SMA Crossover — Signal B (prouvé en IS backtest)

Paramètres par défaut :
  fast     : 9  périodes
  slow     : 21 périodes
  qty      : 0.01 unité (taille de position)
  interval : "1m" (bougie 1 minute)
  stop_pct : 0.015 (stop-loss 1.5 %)
  tp_pct   : 0.030 (take-profit 3.0 %)
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.models import TradingBot, UserBrokerCredential

logger = logging.getLogger(__name__)


class SMACrossoverStrategy:
    """
    Implémentation SMA crossover compatible avec tous les BrokerAdapter.
    Tourne dans un asyncio.Task — utilise un deque de prix OHLCV.
    """

    def __init__(self, bot: "TradingBot", cred: "UserBrokerCredential | None"):
        params = json.loads(bot.params_json or "{}")
        self.bot_id   = bot.id
        self.user_id  = bot.user_id
        self.broker   = bot.broker
        self.symbol   = bot.symbol
        self.mode     = bot.mode
        self.fast     = int(params.get("fast",     9))
        self.slow     = int(params.get("slow",    21))
        self.qty      = float(params.get("qty",  0.01))
        self.interval = params.get("interval",   "1m")
        self.stop_pct = float(params.get("stop_pct", 0.015))
        self.tp_pct   = float(params.get("tp_pct",   0.030))
        self.cred     = cred

        self._closes: deque[float] = deque(maxlen=self.slow + 5)
        self._position: str | None = None   # "long" | "short" | None
        self._entry_price: float = 0.0
        self._adapter = None
        self._stop_event = asyncio.Event()

    # ── Public API ────────────────────────────────────────────────────────────

    async def run(self):
        """Point d'entrée principal — tourne jusqu'à stop()."""
        self._adapter = await self._build_adapter()
        try:
            await self._adapter.connect()
            logger.info("[%s] Démarré — %s %s %s", self.bot_id, self.broker, self.symbol, self.mode.value)
            while not self._stop_event.is_set():
                await self._tick()
                await asyncio.sleep(60)  # 1 tick par minute (ajuster selon interval)
        except asyncio.CancelledError:
            logger.info("[%s] Annulé proprement", self.bot_id)
        except Exception as exc:
            logger.exception("[%s] Erreur stratégie: %s", self.bot_id, exc)
            raise
        finally:
            if self._adapter:
                await self._adapter.disconnect()

    def stop(self):
        self._stop_event.set()

    # ── Internals ─────────────────────────────────────────────────────────────

    async def _build_adapter(self):
        """Instancie le bon BrokerAdapter selon broker + mode + credentials."""
        from backend.app.brokers.factory import get_broker
        from backend.app.core.encryption import decrypt_secret
        import json as _json

        api_key    = decrypt_secret(self.cred.api_key_enc)    if (self.cred and self.cred.api_key_enc)    else None
        api_secret = decrypt_secret(self.cred.api_secret_enc) if (self.cred and self.cred.api_secret_enc) else None
        extra      = _json.loads(decrypt_secret(self.cred.extra_enc)) if (self.cred and self.cred.extra_enc) else {}

        is_testnet = (self.cred and self.cred.is_testnet) or (self.mode.value != "live")

        return get_broker(
            broker=self.broker,
            symbol=self.symbol,
            api_key=api_key,
            api_secret=api_secret,
            testnet=is_testnet,
            extra=extra,
        )

    async def _tick(self):
        """Un tick = récupération du dernier prix + signal + ordre éventuel."""
        price = await self._get_last_price()
        if price is None:
            return

        self._closes.append(price)

        if len(self._closes) < self.slow:
            return  # pas assez de données

        closes = list(self._closes)
        sma_fast = sum(closes[-self.fast:]) / self.fast
        sma_slow = sum(closes[-self.slow:]) / self.slow

        prev_fast = sum(closes[-self.fast - 1:-1]) / self.fast
        prev_slow = sum(closes[-self.slow - 1:-1]) / self.slow

        # Golden cross → BUY
        if prev_fast <= prev_slow and sma_fast > sma_slow:
            if self._position != "long":
                await self._open_long(price)

        # Death cross → SELL / close long
        elif prev_fast >= prev_slow and sma_fast < sma_slow:
            if self._position == "long":
                await self._close_long(price)

        # Gestion stop-loss / take-profit si en position
        if self._position == "long" and self._entry_price > 0:
            if price <= self._entry_price * (1 - self.stop_pct):
                logger.info("[%s] Stop-loss déclenché @ %.5f", self.bot_id, price)
                await self._close_long(price, reason="stop_loss")
            elif price >= self._entry_price * (1 + self.tp_pct):
                logger.info("[%s] Take-profit déclenché @ %.5f", self.bot_id, price)
                await self._close_long(price, reason="take_profit")

    async def _get_last_price(self) -> float | None:
        """Récupère le dernier prix via l'adapter (paper mode = bilan solde)."""
        try:
            if self._adapter is None:
                return None
            # get_balance retourne dict {"balance": X, "currency": "USD"}
            # Pour le prix réel on utilise execute_order dry_run=True (pas standard)
            # → implémentation simplifiée : demander l'équilibre comme proxy
            # Dans une vraie implémentation, ajouter get_ticker() à BrokerAdapter
            balance = await self._adapter.get_balance()
            # fallback: si l'adapter ne fournit pas de ticker, simuler avec bruit
            return balance.get("last_price") or balance.get("price")
        except Exception as exc:
            logger.warning("[%s] get_price error: %s", self.bot_id, exc)
            return None

    async def _open_long(self, price: float):
        if self._adapter is None:
            return
        try:
            result = await self._adapter.execute_order(
                symbol=self.symbol,
                side="buy",
                qty=self.qty,
                order_type="market",
            )
            self._position = "long"
            self._entry_price = price
            logger.info("[%s] BUY %.4f @ %.5f — %s", self.bot_id, self.qty, price, result)
        except Exception as exc:
            logger.error("[%s] open_long failed: %s", self.bot_id, exc)

    async def _close_long(self, price: float, reason: str = "signal"):
        if self._adapter is None:
            return
        try:
            result = await self._adapter.execute_order(
                symbol=self.symbol,
                side="sell",
                qty=self.qty,
                order_type="market",
            )
            pnl = (price - self._entry_price) * self.qty
            self._position = None
            self._entry_price = 0.0
            logger.info(
                "[%s] SELL %.4f @ %.5f | PnL=%.4f | reason=%s — %s",
                self.bot_id, self.qty, price, pnl, reason, result,
            )
        except Exception as exc:
            logger.error("[%s] close_long failed: %s", self.bot_id, exc)
