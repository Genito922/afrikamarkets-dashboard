"""
Afrika Markets — BrokerExecutionFactory
Route les ordres vers Binance / Exness / Deriv via une interface unique.
"""
import os
from backend.app.brokers.base    import BaseBrokerConnector
from backend.app.brokers.binance import BinanceConnector
from backend.app.brokers.exness  import ExnessConnector
from backend.app.brokers.deriv   import DerivBrokerConnector

# Mapping symbole → broker par défaut
SYMBOL_ROUTING = {
    # Crypto → Binance Futures
    "BTCUSDT":  "binance",
    "ETHUSDT":  "binance",
    "SOLUSDT":  "binance",
    "XRPUSDT":  "binance",
    # Forex + Or → Exness MT5
    "XAUUSD":   "exness",
    "EURUSD":   "exness",
    "USDJPY":   "exness",
    "GBPUSD":   "exness",
    # Indices synthétiques → Deriv (24/7)
    "R_75":     "deriv",   # Volatility 75 Index
    "R_100":    "deriv",   # Volatility 100 Index
    "BOOM1000": "deriv",   # Boom 1000 Index
    "CRASH1000":"deriv",   # Crash 1000 Index
    "R_50":     "deriv",   # Volatility 50 Index
}

class BrokerExecutionFactory:
    """
    Retourne le bon connecteur selon le symbole ou le broker explicite.
    Usage :
        async with BrokerExecutionFactory.get("BTCUSDT") as broker:
            await broker.execute_order(...)
    """
    @staticmethod
    def get(symbol_or_broker: str) -> BaseBrokerConnector:
        broker_name = SYMBOL_ROUTING.get(
            symbol_or_broker.upper(),
            symbol_or_broker.lower()
        )
        if broker_name == "binance":
            return BinanceConnector(
                api_key    = os.environ.get("BINANCE_API_KEY",""),
                api_secret = os.environ.get("BINANCE_SECRET_KEY",""),
                testnet    = os.environ.get("ENVIRONMENT","production") != "production",
            )
        elif broker_name == "exness":
            return ExnessConnector(
                account = os.environ.get("EXNESS_ACCOUNT",""),
                password= os.environ.get("EXNESS_PASSWORD",""),
                server  = os.environ.get("EXNESS_SERVER","Exness-MT5Real"),
            )
        elif broker_name == "deriv":
            return DerivBrokerConnector(
                app_id = os.environ.get("DERIV_APP_ID","1011"),
                token  = os.environ.get("DERIV_API_TOKEN",""),
            )
        else:
            raise ValueError(f"Broker non supporté : {broker_name}")

    @staticmethod
    def detect_broker(symbol: str) -> str:
        return SYMBOL_ROUTING.get(symbol.upper(), "inconnu")

    @staticmethod
    def list_symbols() -> dict:
        return SYMBOL_ROUTING
