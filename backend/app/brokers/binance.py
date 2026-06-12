"""
backend/app/brokers/binance.py — Connecteur Binance Futures (CCXT async)

Utilise ccxt.async_support (inclus dans le package ccxt standard, gratuit).
ccxt.pro n'est PAS requis pour l'exécution d'ordres — il est réservé au
streaming d'orderbook professionnel, non nécessaire ici.

Credentials : charger depuis variables d'environnement, jamais en dur.
  BINANCE_API_KEY   — clé API Binance (permissions : Futures trading)
  BINANCE_SECRET    — secret API Binance

Mode sandbox : pointe sur Binance Testnet Futures (paper trading).
Mode live    : pointe sur api.binance.com — ordres réels.
"""
import logging
import os
from typing import Any

import ccxt.async_support as ccxt

from backend.app.brokers.base import BaseBrokerConnector

logger = logging.getLogger(__name__)

# Format symbole attendu par CCXT pour Binance Futures : "BTC/USDT:USDT"
# (différent du format Binance natif "BTCUSDT")


class BinanceConnector(BaseBrokerConnector):
    """
    Connecteur Binance Futures asynchrone via CCXT.

    Usage :
      connector = BinanceConnector(sandbox=True)   # lit les clés depuis l'env
      await connector.connect()
      balance = await connector.get_balance()
      ticket  = await connector.execute_order("BTC/USDT:USDT", "buy", 0.001)
      await connector.disconnect()

    Context manager :
      async with BinanceConnector() as c:
          await c.execute_order(...)
    """

    def __init__(
        self,
        api_key: str | None = None,
        secret: str | None = None,
        sandbox: bool = True,
    ) -> None:
        # Priorité : paramètres explicites, puis variables d'environnement
        self._api_key  = api_key  or os.environ.get("BINANCE_API_KEY",  "")
        self._secret   = secret   or os.environ.get("BINANCE_SECRET",   "")
        self._sandbox  = sandbox
        self._exchange: ccxt.binance | None = None

    # ── Context manager ───────────────────────────────────────

    async def __aenter__(self) -> "BinanceConnector":
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.disconnect()

    # ── Cycle de vie ──────────────────────────────────────────

    async def connect(self) -> bool:
        """Initialise l'instance CCXT et valide les credentials via load_markets."""
        if not self._api_key or not self._secret:
            logger.error("[Binance] Credentials manquants — BINANCE_API_KEY / BINANCE_SECRET non définis")
            return False

        logger.info("[Binance] Connexion Futures (%s)…", "testnet" if self._sandbox else "live")
        try:
            self._exchange = ccxt.binance({
                "apiKey":          self._api_key,
                "secret":          self._secret,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "future",
                },
            })
            if self._sandbox:
                self._exchange.set_sandbox_mode(True)

            await self._exchange.load_markets()
            logger.info("[Binance] Connecté — %d marchés chargés", len(self._exchange.markets))
            return True

        except ccxt.AuthenticationError as exc:
            logger.error("[Binance] Authentification refusée : %s", exc)
            await self._safe_close()
            return False
        except Exception as exc:
            logger.error("[Binance] Erreur de connexion : %s", exc)
            await self._safe_close()
            return False

    async def disconnect(self) -> None:
        """Ferme proprement la session HTTP et les éventuels WebSockets."""
        await self._safe_close()
        logger.info("[Binance] Déconnecté")

    async def _safe_close(self) -> None:
        if self._exchange is not None:
            try:
                await self._exchange.close()
            except Exception:
                pass
            self._exchange = None

    def _require_connected(self) -> ccxt.binance:
        """Retourne l'instance exchange ou lève RuntimeError si non connecté."""
        if self._exchange is None:
            raise RuntimeError(
                "BinanceConnector non connecté — appelez await connector.connect() d'abord"
            )
        return self._exchange

    # ── Capital ───────────────────────────────────────────────

    async def get_balance(self) -> dict:
        """
        Retourne l'état du compte Futures USDT-M.
        Clés : total_usd, available_usd, margin_used_usd, unrealized_pnl_usd.
        """
        exchange = self._require_connected()
        try:
            raw = await exchange.fetch_balance(params={"type": "future"})

            total_usd     = float(raw.get("total", {}).get("USDT", 0.0))
            available_usd = float(raw.get("free",  {}).get("USDT", 0.0))
            margin_used   = float(raw.get("used",  {}).get("USDT", 0.0))

            # PnL non réalisé agrégé sur toutes les positions ouvertes
            positions = raw.get("info", {}).get("positions", [])
            unrealized_pnl = sum(
                float(p.get("unrealizedProfit", 0.0))
                for p in positions
                if float(p.get("unrealizedProfit", 0.0)) != 0.0
            )

            return {
                "total_usd":          total_usd,
                "available_usd":      available_usd,
                "margin_used_usd":    margin_used,
                "unrealized_pnl_usd": unrealized_pnl,
            }

        except Exception as exc:
            logger.error("[Binance] get_balance échoué : %s", exc)
            raise

    # ── Exécution ─────────────────────────────────────────────

    async def execute_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str = "market",
        price: float | None = None,
        stop_loss: float | None = None,
        **kwargs: Any,
    ) -> dict:
        """
        Place un ordre Futures et optionnellement un STOP_MARKET de protection.

        Paramètres :
          symbol     — format CCXT : "BTC/USDT:USDT" (pas "BTCUSDT")
          side       — "buy" | "sell"
          amount     — quantité en unité de base (ex: 0.001 BTC)
          order_type — "market" | "limit"
          price      — requis si order_type="limit"
          stop_loss  — niveau de déclenchement du stop de protection (optionnel)

        Retourne le ticket : {order_id, status, filled, avg_price, stop_loss_order_id?}
        Lève une exception en cas d'échec (jamais de retour silencieux).
        """
        # ── Validations ──────────────────────────────────────
        side = side.lower()
        if side not in ("buy", "sell"):
            raise ValueError(f"side invalide '{side}' — attendu 'buy' ou 'sell'")
        if amount <= 0:
            raise ValueError(f"amount invalide ({amount}) — doit être > 0")
        if order_type == "limit" and price is None:
            raise ValueError("price est requis pour un ordre limit")

        exchange = self._require_connected()

        logger.info(
            "[Binance] execute_order %s %s %.6f %s%s",
            order_type.upper(), side.upper(), amount, symbol,
            f" @ {price}" if price else "",
        )

        # ── Ordre principal ───────────────────────────────────
        main = await exchange.create_order(
            symbol=symbol,
            type=order_type,
            side=side,
            amount=amount,
            price=price,
            params=kwargs,
        )

        ticket: dict = {
            "order_id":   main.get("id"),
            "status":     main.get("status"),
            "filled":     float(main.get("filled")     or 0.0),
            "remaining":  float(main.get("remaining")  or 0.0),
            "avg_price":  float(main.get("average")    or 0.0),
            "fee":        main.get("fee"),
            "sl_order_id": None,
        }

        # ── Stop Loss de protection ───────────────────────────
        if stop_loss is not None:
            inverse_side = "sell" if side == "buy" else "buy"
            logger.info("[Binance] Pose du stop loss %.4f sur %s", stop_loss, symbol)

            sl = await exchange.create_order(
                symbol=symbol,
                type="STOP_MARKET",
                side=inverse_side,
                amount=amount,
                params={
                    "stopPrice":  stop_loss,
                    "reduceOnly": True,
                },
            )
            ticket["sl_order_id"] = sl.get("id")

        logger.info("[Binance] Ordre exécuté : %s", ticket)
        return ticket
