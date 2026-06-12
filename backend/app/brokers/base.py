"""
backend/app/brokers/base.py — Interface abstraite pour les connecteurs broker

Contrat immuable : tout connecteur (Binance, Exness, Deriv) doit implémenter
ces 4 méthodes. L'exécution d'ordres réels sur les marchés financiers ne peut
se faire que via une sous-classe concrète de BaseBrokerConnector.

Hiérarchie prévue :
  BaseBrokerConnector
    ├── BinanceConnector   (CCXT Pro — Futures, REST + WebSocket)
    ├── ExnessConnector    (MetaTrader5 SDK — Forex/Métaux, via asyncio.to_thread)
    └── DerivConnector     (WebSocket persistant — Indices synthétiques)

Sécurité : aucun connecteur concret ne doit stocker les clés API en clair.
           Charger exclusivement depuis les variables d'environnement.
"""
from abc import ABC, abstractmethod


class BaseBrokerConnector(ABC):
    """
    Interface commune pour tous les connecteurs de courtage.

    Méthodes obligatoires :
      connect()        — initialise la session et valide les credentials
      disconnect()     — ferme proprement la session / WebSocket
      execute_order()  — place un ordre de façon atomique
      get_balance()    — retourne marges et capital disponible
    """

    # ── Cycle de vie ──────────────────────────────────────────

    @abstractmethod
    async def connect(self) -> bool:
        """
        Initialise la connexion au broker (REST auth, WebSocket handshake…).
        Retourne True si la session est établie, False sinon.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Ferme proprement la session et libère les ressources réseau."""

    # ── Exécution ─────────────────────────────────────────────

    @abstractmethod
    async def execute_order(
        self,
        symbol: str,
        side: str,       # "buy" | "sell"
        amount: float,   # en unité de base (BTC, lots, contrats…)
        order_type: str = "market",  # "market" | "limit"
        price: float | None = None,  # requis si order_type="limit"
        stop_loss: float | None = None,
        **kwargs,
    ) -> dict:
        """
        Place un ordre en production.
        Retourne le ticket broker : {order_id, status, filled, avg_price, fee, …}

        Toute implémentation doit :
          - Vérifier que amount > 0 avant envoi
          - Logger l'ordre et la réponse broker
          - Lever une exception explicite en cas d'échec (pas silencieux)
        """

    # ── Capital ───────────────────────────────────────────────

    @abstractmethod
    async def get_balance(self) -> dict:
        """
        Retourne l'état du compte :
          {total_usd, available_usd, margin_used_usd, unrealized_pnl_usd}
        """

    # ── Représentation ────────────────────────────────────────

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
