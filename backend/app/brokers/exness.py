"""
backend/app/brokers/exness.py — Connecteur Exness via MetaTrader 5 SDK

Contraintes architecturales :
  1. MetaTrader5 est SYNCHRONE ET BLOQUANT — chaque appel SDK doit passer
     par asyncio.to_thread() pour ne pas geler la boucle FastAPI.
  2. MetaTrader5 est WINDOWS UNIQUEMENT — le package ne s'installe pas sous
     Linux (environnement Railway/Docker). Import conditionnel obligatoire.

En production, ce connecteur tourne donc sur :
  - Développement local : Windows (brvm_venv)
  - Production Railway  : non disponible — prévoir une passerelle Windows
    dédiée (VPS Windows) qui expose un microservice REST intermédiaire.

Credentials (variables d'environnement) :
  EXNESS_MT5_LOGIN     — numéro de compte MT5 (entier)
  EXNESS_MT5_PASSWORD  — mot de passe de trading
  EXNESS_MT5_SERVER    — nom du serveur Exness (ex: "Exness-MT5Real3")

Ordre limit : seuls les ordres au marché ("market") sont supportés dans
  cette version. Les ordres pendants (limit/stop) nécessitent de connaître
  la direction relative prix/marché pour choisir entre BUY_LIMIT, BUY_STOP,
  SELL_LIMIT, SELL_STOP — à implémenter dans une v2 dédiée.
"""
import asyncio
import logging
import os
import sys

logger = logging.getLogger(__name__)

# ── Import conditionnel (Windows uniquement) ──────────────────
_MT5_AVAILABLE = False
mt5 = None  # type: ignore

if sys.platform == "win32":
    try:
        import MetaTrader5 as mt5  # type: ignore
        _MT5_AVAILABLE = True
    except ImportError:
        logger.warning(
            "[Exness] MetaTrader5 non installé — pip install MetaTrader5 (Windows requis)"
        )
else:
    logger.info(
        "[Exness] MetaTrader5 non disponible sous %s — connecteur désactivé", sys.platform
    )

from backend.app.brokers.base import BaseBrokerConnector


def _require_mt5() -> None:
    """Lève une erreur explicite si MT5 n'est pas disponible sur cet OS."""
    if not _MT5_AVAILABLE or mt5 is None:
        raise RuntimeError(
            "MetaTrader5 SDK indisponible sur cet environnement. "
            "Ce connecteur nécessite Windows + pip install MetaTrader5."
        )


class ExnessConnector(BaseBrokerConnector):
    """
    Connecteur Exness (Forex, Métaux, Indices) via MetaTrader 5 SDK.

    Usage :
      connector = ExnessConnector()          # lit les credentials depuis l'env
      await connector.connect()              # retourne False si MT5 indisponible
      bal = await connector.get_balance()
      ticket = await connector.execute_order("XAUUSD", "buy", 0.01)
      await connector.disconnect()

    Context manager :
      async with ExnessConnector() as c:
          await c.execute_order(...)
    """

    # Identifiant magique : permet d'isoler les ordres Sentinel des trades manuels
    MAGIC_NUMBER: int = 202606

    def __init__(
        self,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
        deviation: int = 10,
    ) -> None:
        """
        deviation : slippage maximal toléré en points (défaut 10 — adapté Forex/Métaux)
        """
        self._login    = login    or int(os.environ.get("EXNESS_MT5_LOGIN",    0))
        self._password = password or os.environ.get("EXNESS_MT5_PASSWORD", "")
        self._server   = server   or os.environ.get("EXNESS_MT5_SERVER",   "")
        self._deviation = deviation
        self._connected = False

    # ── Context manager ───────────────────────────────────────

    async def __aenter__(self) -> "ExnessConnector":
        await self.connect()
        return self

    async def __aexit__(self, *_) -> None:
        await self.disconnect()

    # ── Cycle de vie ──────────────────────────────────────────

    async def connect(self) -> bool:
        """
        Initialise le terminal MT5 et authentifie le compte Exness.
        Retourne False (sans lever) si MT5 est indisponible ou si les
        credentials sont manquants — cohérent avec le contrat BaseBrokerConnector.
        """
        if not _MT5_AVAILABLE:
            logger.error("[Exness] connect() impossible — MT5 non disponible sur cet OS")
            return False

        if not self._login or not self._password or not self._server:
            logger.error("[Exness] Credentials manquants — EXNESS_MT5_LOGIN / PASSWORD / SERVER")
            return False

        logger.info("[Exness] Initialisation MT5 (serveur: %s)…", self._server)
        try:
            initialized = await asyncio.to_thread(mt5.initialize)
            if not initialized:
                logger.error("[Exness] mt5.initialize() échoué : %s", mt5.last_error())
                return False

            authorized = await asyncio.to_thread(
                mt5.login, self._login,
                password=self._password,
                server=self._server,
            )
            if not authorized:
                logger.error("[Exness] Authentification refusée : %s", mt5.last_error())
                await asyncio.to_thread(mt5.shutdown)
                return False

            self._connected = True
            acc = await asyncio.to_thread(mt5.account_info)
            logger.info(
                "[Exness] Connecté — compte %d, balance %.2f %s",
                self._login,
                acc.balance if acc else 0,
                acc.currency if acc else "?",
            )
            return True

        except Exception as exc:
            logger.error("[Exness] Erreur de connexion inattendue : %s", exc)
            return False

    async def disconnect(self) -> None:
        """Arrête proprement le terminal MT5."""
        if self._connected and _MT5_AVAILABLE and mt5 is not None:
            await asyncio.to_thread(mt5.shutdown)
            self._connected = False
            logger.info("[Exness] Déconnecté")

    def _require_connected(self) -> None:
        """Lève RuntimeError si le connecteur n'est pas actif."""
        _require_mt5()
        if not self._connected:
            raise RuntimeError(
                "ExnessConnector non connecté — appelez await connector.connect() d'abord"
            )

    # ── Capital ───────────────────────────────────────────────

    async def get_balance(self) -> dict:
        """
        Retourne l'état du compte via mt5.account_info().
        Clés : total_usd, available_usd, margin_used_usd, unrealized_pnl_usd.
        """
        self._require_connected()

        acc = await asyncio.to_thread(mt5.account_info)
        if acc is None:
            raise RuntimeError(f"mt5.account_info() a échoué : {mt5.last_error()}")

        return {
            "total_usd":          float(acc.balance),
            "available_usd":      float(acc.margin_free),
            "margin_used_usd":    float(acc.margin),
            "unrealized_pnl_usd": float(acc.profit),
        }

    # ── Exécution ─────────────────────────────────────────────

    async def execute_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str = "market",
        price: float | None = None,
        stop_loss: float | None = None,
        **kwargs,
    ) -> dict:
        """
        Place un ordre MT5 sur Exness.

        Paramètres :
          symbol     — symbole MT5 : "XAUUSD", "EURUSD", "BTCUSD"…
          side       — "buy" | "sell"
          amount     — volume en lots (0.01 = 1 micro-lot)
          order_type — "market" uniquement dans cette version
          price      — ignoré en mode market (prix récupéré depuis le dernier tick)
          stop_loss  — niveau SL (prix absolu, pas en pips)

        Lève une exception en cas d'échec — jamais de retour silencieux.
        """
        # ── Validations ──────────────────────────────────────
        side = side.lower()
        if side not in ("buy", "sell"):
            raise ValueError(f"side invalide '{side}' — attendu 'buy' ou 'sell'")
        if amount <= 0:
            raise ValueError(f"amount invalide ({amount}) — doit être > 0")
        if order_type != "market":
            raise NotImplementedError(
                "Seuls les ordres 'market' sont supportés dans cette version. "
                "Les ordres pendants (limit/stop) nécessitent de résoudre "
                "BUY_LIMIT vs BUY_STOP selon la position du prix courant."
            )

        self._require_connected()

        # ── Préparation du symbole ────────────────────────────
        symbol_info = await asyncio.to_thread(mt5.symbol_info, symbol)
        if symbol_info is None:
            raise ValueError(f"Symbole '{symbol}' introuvable sur ce compte Exness")

        # Active le symbole dans le MarketWatch si nécessaire
        if not symbol_info.visible:
            await asyncio.to_thread(mt5.symbol_select, symbol, True)
            symbol_info = await asyncio.to_thread(mt5.symbol_info, symbol)

        # ── Prix d'exécution ──────────────────────────────────
        tick = await asyncio.to_thread(mt5.symbol_info_tick, symbol)
        if tick is None:
            raise RuntimeError(f"Impossible d'obtenir le tick de prix pour '{symbol}'")

        exec_price = tick.ask if side == "buy" else tick.bid

        # ── Filling mode dynamique ────────────────────────────
        # Le filling mode dépend du symbole et du serveur broker.
        # Lire symbol_info.filling_mode (bitmask) évite les rejets serveur.
        #   Bit 0 (1) = ORDER_FILLING_FOK
        #   Bit 1 (2) = ORDER_FILLING_IOC
        #   Bit 2 (4) = ORDER_FILLING_RETURN (exécution partielle)
        fm = symbol_info.filling_mode
        if fm & 1:
            filling = mt5.ORDER_FILLING_FOK
        elif fm & 2:
            filling = mt5.ORDER_FILLING_IOC
        else:
            filling = mt5.ORDER_FILLING_RETURN

        # ── Construction de la requête MT5 ────────────────────
        mt5_side = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL

        request: dict = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       symbol,
            "volume":       float(amount),
            "type":         mt5_side,
            "price":        float(exec_price),
            "deviation":    self._deviation,
            "magic":        self.MAGIC_NUMBER,
            "comment":      "Sentinel algo",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": filling,
        }

        if stop_loss is not None:
            if stop_loss <= 0:
                raise ValueError(f"stop_loss invalide ({stop_loss}) — doit être > 0")
            request["sl"] = float(stop_loss)

        logger.info(
            "[Exness] execute_order %s %s %.4f lots @ %.5f (SL: %s)",
            side.upper(), symbol, amount, exec_price,
            f"{stop_loss:.5f}" if stop_loss else "aucun",
        )

        # ── Envoi de l'ordre (non-bloquant) ──────────────────
        result = await asyncio.to_thread(mt5.order_send, request)

        if result is None:
            raise RuntimeError(
                f"mt5.order_send() sans réponse pour {symbol} — {mt5.last_error()}"
            )

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(
                f"Ordre rejeté par Exness (retcode={result.retcode}) : {result.comment}"
            )

        logger.info(
            "[Exness] Ordre exécuté — ticket=%d price=%.5f volume=%.4f",
            result.order, result.price, result.volume,
        )

        return {
            "order_id":          result.order,
            "status":            "FILLED",
            "avg_price":         float(result.price),
            "filled":            float(result.volume),
            "sl_order_id":       None,   # SL intégré à l'ordre MT5, pas d'ID séparé
            "stop_loss_attached": stop_loss is not None,
        }
