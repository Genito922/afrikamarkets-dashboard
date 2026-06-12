import os, json, logging, asyncio, uuid
from typing import Optional, Dict
import aiohttp
from backend.app.brokers.base import BaseBrokerConnector

logger = logging.getLogger("brokers.deriv")

class DerivBrokerConnector(BaseBrokerConnector):
    def __init__(self, app_id=None, token=None):
        self.app_id = app_id or os.environ.get("DERIV_APP_ID","1011")
        self.token  = token  or os.environ.get("DERIV_API_TOKEN","")
        self.ws_url = f"wss://ws.derivws.com/websockets/v3?app_id={self.app_id}"
        self.session = None
        self.ws      = None
        self._is_connected       = False
        self._listen_task        = None
        self._pending_responses: Dict[str, asyncio.Future] = {}

    async def __aenter__(self):
        await self.connect(); return self

    async def __aexit__(self, *_):
        await self.disconnect()

    async def connect(self) -> bool:
        if not self.token:
            raise ValueError("DERIV_API_TOKEN manquant")
        self.session = aiohttp.ClientSession()
        try:
            self.ws = await self.session.ws_connect(self.ws_url)
            self._is_connected = True
            self._listen_task  = asyncio.create_task(self._background_listener())
            auth = await self._send_and_wait({"authorize": self.token})
            if "error" in auth:
                raise ConnectionError(auth["error"]["message"])
            logger.info(f"Deriv connecté — {auth['authorize']['email']}")
            return True
        except Exception as e:
            logger.error(f"Deriv connexion échouée : {e}")
            await self.disconnect()
            return False

    async def disconnect(self):
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try: await self._listen_task
            except asyncio.CancelledError: pass
        if self.ws  and not self.ws.closed:   await self.ws.close()
        if self.session and not self.session.closed: await self.session.close()
        self._is_connected = False
        self._pending_responses.clear()

    async def get_balance(self) -> dict:
        r = await self._send_and_wait({"balance": 1})
        if "error" in r: raise RuntimeError(r["error"]["message"])
        bal = float(r["balance"]["balance"])
        return {"total_usd": bal, "available_usd": bal, "margin_used_usd": 0.0}

    async def execute_order(self, symbol, side, amount, order_type="market",
                            price=None, stop_loss=None) -> dict:
        if side.upper() not in ("BUY","SELL"):
            raise ValueError(f"Side invalide : {side}")
        if order_type.lower() != "market":
            raise NotImplementedError("Deriv : market orders uniquement")
        if not self._is_connected:
            raise ConnectionError("Deriv WebSocket inactif")

        contract_type = "CALL" if side.upper() == "BUY" else "PUT"
        payload = {
            "buy": "1",
            "price": float(amount),
            "parameters": {
                "amount": float(amount), "basis": "stake",
                "contract_type": contract_type, "currency": "USD",
                "duration": 1, "duration_unit": "m", "symbol": symbol,
            }
        }
        if stop_loss:
            payload["parameters"]["barrier"] = str(stop_loss)

        r = await self._send_and_wait(payload)
        if "error" in r: raise RuntimeError(r["error"]["message"])
        info = r["buy"]
        return {
            "order_id": info["contract_id"], "status": "FILLED",
            "price": float(info.get("price", 0)), "volume": amount,
        }

    async def _send_and_wait(self, payload: dict) -> dict:
        req_id = str(uuid.uuid4())[:8]
        payload["req_id"] = req_id
        future = asyncio.get_running_loop().create_future()
        self._pending_responses[req_id] = future
        try:
            await self.ws.send_str(json.dumps(payload))
            return await asyncio.wait_for(future, timeout=15.0)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Deriv timeout req_id={req_id}")
        finally:
            self._pending_responses.pop(req_id, None)

    async def _background_listener(self):
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    req_id = data.get("req_id")
                    if req_id and req_id in self._pending_responses:
                        f = self._pending_responses[req_id]
                        if not f.done(): f.set_result(data)
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
        except asyncio.CancelledError: pass
        except Exception as e: logger.error(f"Deriv listener erreur : {e}")
