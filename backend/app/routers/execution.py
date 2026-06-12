"""
Afrika Markets — Execution Router
POST /execution/order  → route vers le bon broker
GET  /execution/status → état des 3 brokers
GET  /execution/symbols → mapping symboles
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from backend.app.brokers.factory import BrokerExecutionFactory

router  = APIRouter(prefix="/execution", tags=["execution"])
logger  = logging.getLogger("execution")

class OrderRequest(BaseModel):
    symbol:     str              # Ex: BTCUSDT, XAUUSD, R_75
    side:       str              # BUY | SELL
    amount:     float            # Montant en USD ou unités
    order_type: str = "market"
    stop_loss:  Optional[float] = None
    broker:     Optional[str]   = None  # Forcer un broker spécifique

class OrderResponse(BaseModel):
    order_id:   str
    status:     str
    broker:     str
    symbol:     str
    side:       str
    price:      float
    volume:     float

@router.post("/order", response_model=OrderResponse)
async def place_order(req: OrderRequest):
    """Place un ordre sur le bon broker selon le symbole."""
    target = req.broker or req.symbol

    try:
        broker_name = BrokerExecutionFactory.detect_broker(req.symbol)
        logger.info(f"[ORDER] {req.symbol} {req.side} {req.amount} → {broker_name}")

        async with BrokerExecutionFactory.get(target) as broker:
            result = await broker.execute_order(
                symbol     = req.symbol,
                side       = req.side,
                amount     = req.amount,
                order_type = req.order_type,
                stop_loss  = req.stop_loss,
            )
        return OrderResponse(
            order_id = str(result["order_id"]),
            status   = result["status"],
            broker   = broker_name,
            symbol   = req.symbol,
            side     = req.side.upper(),
            price    = float(result.get("price", 0)),
            volume   = float(result.get("volume", req.amount)),
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except ConnectionError as e:
        raise HTTPException(503, f"Broker indisponible : {e}")
    except RuntimeError as e:
        raise HTTPException(502, f"Erreur broker : {e}")
    except Exception as e:
        logger.error(f"[ORDER] Erreur inattendue : {e}")
        raise HTTPException(500, str(e))

@router.get("/symbols")
async def list_symbols():
    """Mapping symboles → brokers."""
    return {
        "routing": BrokerExecutionFactory.list_symbols(),
        "brokers": {
            "binance": "Crypto Futures — BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT",
            "exness":  "Forex + Or — XAUUSD, EURUSD, GBPUSD, USDJPY",
            "deriv":   "Synthétiques 24/7 — R_75, R_100, BOOM1000, CRASH1000",
        }
    }

@router.get("/balance/{broker}")
async def get_balance(broker: str):
    """Solde d'un broker."""
    try:
        async with BrokerExecutionFactory.get(broker) as b:
            return {"broker": broker, "balance": await b.get_balance()}
    except Exception as e:
        raise HTTPException(503, str(e))
