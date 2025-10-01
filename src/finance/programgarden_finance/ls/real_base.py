from abc import ABC
import asyncio
import json
from typing import Callable, Dict, List, Optional, Any, TypeVar
import importlib
import random

from websockets import ClientConnection, connect
import inspect
from websockets.exceptions import WebSocketException
from programgarden_finance.ls.config import URLS
from programgarden_finance.ls.token_manager import TokenManager

T = TypeVar("T")

# cache for dynamic response class lookups: tr_cd -> (response_model, header_model, body_model) or None
_RESPONSE_CLASS_CACHE: Dict[str, Optional[tuple]] = {}

# candidate module roots where tr_cd modules may live; keep order from most likely to least
_RESPONSE_MODULE_BASES = [
    "programgarden_finance.ls.overseas_stock.real",
    "programgarden_finance.ls.overseas_futureoption.real",
]


class RealRequestAbstract(ABC):
    """
    실시간 요청 추상 클래스
    """

    def __init__(
        self,
        reconnect=True,
        recv_timeout=5.0,
        ping_interval=30.0,
        ping_timeout=5.0,
        max_backoff=60.0,
        token_manager: Optional[TokenManager] = None,
    ):
        super().__init__()

        self._reconnect = reconnect
        self._recv_timeout = recv_timeout
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._max_backoff = max_backoff
        self._token_manager = token_manager

        # Event that is set when a websocket connection is successfully opened
        self._connected_event = asyncio.Event()

        self._ws: Optional[ClientConnection] = None
        self._listen_task = None
        self._as01234_connect = False
        self._on_message_listeners: Dict[str, Callable[[Any], Any]] = {}

    async def is_connected(self) -> bool:
        return self._connected_event.is_set()

    async def connect(
        self,
        wait: bool = True,
        timeout: float = 5.0,
    ):

        self._stop = False

        async def _connection_loop():
            """Runs the connection lifecycle: connect, receive messages, handle errors and reconnect.

            - Outer loop: manages connection attempts and reconnection/backoff.
            - Inner loop: runs while a single websocket connection is open and receives messages.
            """
            backoff = 1.0
            # Outer loop: connection attempt / reconnect
            while not self._stop:
                try:
                    # set ping/pong to keep connection alive
                    async with connect(
                        uri=URLS.WSS_URL,
                        ping_interval=self._ping_interval,
                        ping_timeout=self._ping_timeout,
                    ) as ws:
                        self._ws = ws
                        # signal that a connection is available
                        try:
                            self._connected_event.set()
                        except Exception:
                            pass
                        backoff = 1.0  # reset backoff after successful connect

                        # Inner loop: active connection receive loop
                        while not self._stop:
                            try:
                                # use explicit recv with timeout so stalled connections are detected
                                raw = await asyncio.wait_for(ws.recv(), timeout=self._recv_timeout)
                            except asyncio.TimeoutError:
                                # no message received within recv_timeout; send a ping and continue
                                try:
                                    await ws.ping()
                                except Exception:
                                    # ping failed; break to reconnect
                                    break
                                continue
                            except asyncio.CancelledError:
                                # propagate cancellation so outer task can stop cleanly
                                raise
                            except (WebSocketException, ConnectionError):
                                # connection-level errors -> break to reconnect
                                break
                            except Exception:
                                # unexpected error on recv; try to continue listening
                                continue

                            # parse message quickly and hand off
                            try:
                                resp_json = json.loads(raw)

                            except Exception:
                                # ignore malformed payloads
                                continue

                            tr_cd = resp_json.get('header', {}).get('tr_cd', None)

                            # dynamically import the module for this tr_cd and cache the classes
                            if not tr_cd:
                                continue

                            cached = _RESPONSE_CLASS_CACHE.get(tr_cd)
                            if cached is None:
                                mod = None
                                response_model = response_header_model = response_body_model = None
                                # try each candidate base until one imports successfully
                                for base in _RESPONSE_MODULE_BASES:
                                    module_name = f"{base}.{tr_cd}.blocks"
                                    try:
                                        m = importlib.import_module(module_name)
                                    except Exception:
                                        continue
                                    # prefer the first base that contains the expected attributes
                                    try:
                                        response_model = getattr(m, f"{tr_cd}RealResponse")
                                        response_header_model = getattr(m, f"{tr_cd}RealResponseHeader")
                                        response_body_model = getattr(m, f"{tr_cd}RealResponseBody")
                                        mod = m
                                        break
                                    except Exception:
                                        # module existed but didn't expose the expected classes; try next base
                                        continue

                                if mod is None:
                                    # remember failures so we don't repeatedly try to import missing modules
                                    _RESPONSE_CLASS_CACHE[tr_cd] = None
                                    continue

                                _RESPONSE_CLASS_CACHE[tr_cd] = (response_model, response_header_model, response_body_model)
                            else:
                                if cached is None:
                                    continue
                                response_model, response_header_model, response_body_model = cached

                            try:

                                on_message = self._on_message_listeners.get(tr_cd, None)

                                resp_header = resp_json.get('header', {})

                                resp_body = resp_json.get('body', {})
                                resp = response_model(
                                    header=response_header_model.model_validate(resp_header),
                                    body=response_body_model.model_validate(resp_body) if resp_body else None,
                                    rsp_cd=resp_header.get("rsp_cd", ""),
                                    rsp_msg=resp_header.get("rsp_msg", ""),
                                )
                                resp.raw_data = resp_json
                            except Exception as e:
                                resp = response_model(
                                    header=None,
                                    body=None,
                                    rsp_cd="",
                                    rsp_msg="",
                                    error_msg=str(e),
                                )

                            if on_message is None:
                                continue

                            loop = asyncio.get_running_loop()

                            # async handler: schedule a task
                            if inspect.iscoroutinefunction(on_message):
                                try:
                                    task = asyncio.create_task(on_message(resp))
                                except Exception:
                                    # if scheduling fails, skip
                                    continue

                                # attach simple exception logging to avoid silent failures
                                def _on_done(t: asyncio.Task):
                                    try:
                                        exc = t.exception()
                                        if exc is not None:
                                            pass
                                            # print(f"handler task error: {exc}")
                                    except asyncio.CancelledError:
                                        pass

                                task.add_done_callback(_on_done)
                            else:
                                # sync handler: offload to default threadpool so recv loop isn't blocked
                                try:
                                    loop.run_in_executor(None, on_message, resp)
                                except Exception:
                                    continue

                except asyncio.CancelledError:
                    # allow cancellation to bubble up for clean shutdown
                    break
                except Exception:
                    # general connection failure
                    if not self._reconnect:
                        break

                # reconnect/backoff logic
                if not self._reconnect or self._stop:
                    break

                # exponential backoff with small jitter
                jitter = random.uniform(0, backoff * 0.1)
                await asyncio.sleep(backoff + jitter)
                backoff = min(self._max_backoff, backoff * 2)
                # clear connected event when leaving the connect attempt
                try:
                    self._connected_event.clear()
                except Exception:
                    pass
        # create the listener task
        self._listen_task = asyncio.create_task(_connection_loop())
        # optionally wait until a connection is established
        if wait:
            try:
                await asyncio.wait_for(self._connected_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                raise RuntimeError("Timeout waiting for websocket connection")
        else:
            await asyncio.sleep(0)

    async def close(self):
        self._stop = True
        # cancel listener task if running
        if self._listen_task is not None:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass

    def _on_message(self, message_key: str,  listener: Callable[[Any], None]):
        if not self._connected_event.is_set():
            raise RuntimeError("WebSocket is not connected")
        self._on_message_listeners[message_key] = listener

    def _on_remove_message(self, message_key: str):
        if not self._connected_event.is_set():
            raise RuntimeError("WebSocket is not connected")
        if message_key in self._on_message_listeners:
            del self._on_message_listeners[message_key]

        if len(self._on_message_listeners) == 0:
            self._as01234_connect = False
            self._remove_real_order()

    def _add_message_symbols(self, symbols: List[str], tr_cd: str):
        if not self._connected_event.is_set():
            raise RuntimeError("WebSocket is not connected")

        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        for symbol in symbols:

            if tr_cd == "GSC":
                from programgarden_finance.ls.overseas_stock.real.GSC.blocks import GSCRealRequest, GSCRealRequestBody
                req = GSCRealRequest(
                    body=GSCRealRequestBody(
                        tr_key=symbol
                    )
                )
                req.header.tr_type = "3"
            elif tr_cd == "GSH":
                from programgarden_finance.ls.overseas_stock.real.GSH.blocks import GSHRealRequest, GSHRealRequestBody
                req = GSHRealRequest(
                    body=GSHRealRequestBody(
                        tr_key=symbol
                    )
                )
                req.header.tr_type = "3"
            elif tr_cd == "OVC":
                from programgarden_finance.ls.overseas_futureoption.real.OVC.blocks import OVCRealRequest, OVCRealRequestBody
                req = OVCRealRequest(
                    body=OVCRealRequestBody(
                        tr_key=symbol
                    )
                )
                req.header.tr_type = "3"
            elif tr_cd == "OVH":
                from programgarden_finance.ls.overseas_futureoption.real.OVH.blocks import OVHRealRequest, OVHRealRequestBody
                req = OVHRealRequest(
                    body=OVHRealRequestBody(
                        tr_key=symbol
                    )
                )
                req.header.tr_type = "3"
            elif tr_cd == "WOC":
                from programgarden_finance.ls.overseas_futureoption.real.WOC.blocks import WOCRealRequest, WOCRealRequestBody
                req = WOCRealRequest(
                    body=WOCRealRequestBody(
                        tr_key=symbol
                    )
                )
                req.header.tr_type = "3"
            elif tr_cd == "WOH":
                from programgarden_finance.ls.overseas_futureoption.real.WOH.blocks import WOHRealRequest, WOHRealRequestBody
                req = WOHRealRequest(
                    body=WOHRealRequestBody(
                        tr_key=symbol
                    )
                )
                req.header.tr_type = "3"
            else:
                continue

            if req is None:
                break

            req.header.token = self._token_manager.access_token

            req = {"header": req.header.model_dump(), "body": req.body.model_dump()}

            # print(f"Sending real request: {req}, {self._ws}")
            asyncio.create_task(self._ws.send(json.dumps(req)))

    def _remove_message_symbols(self, symbols: List[str], tr_cd: str):
        if not self._connected_event.is_set():
            raise RuntimeError("WebSocket is not connected")

        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        for symbol in symbols:

            if tr_cd == "GSC":
                from programgarden_finance.ls.overseas_stock.real.GSC.blocks import GSCRealRequest, GSCRealRequestBody
                req = GSCRealRequest(
                    body=GSCRealRequestBody(
                        tr_key=symbol
                    )
                )
                req.header.tr_type = "4"
            elif tr_cd == "GSH":
                from programgarden_finance.ls.overseas_stock.real.GSH.blocks import GSHRealRequest, GSHRealRequestBody
                req = GSHRealRequest(
                    body=GSHRealRequestBody(
                        tr_key=symbol
                    )
                )
                req.header.tr_type = "4"
            elif tr_cd == "OVC":
                from programgarden_finance.ls.overseas_futureoption.real.OVC.blocks import OVCRealRequest, OVCRealRequestBody
                req = OVCRealRequest(
                    body=OVCRealRequestBody(
                        tr_key=symbol
                    )
                )
                req.header.tr_type = "4"
            elif tr_cd == "OVH":
                from programgarden_finance.ls.overseas_futureoption.real.OVH.blocks import OVHRealRequest, OVHRealRequestBody
                req = OVHRealRequest(
                    body=OVHRealRequestBody(
                        tr_key=symbol
                    )
                )
                req.header.tr_type = "4"
            elif tr_cd == "WOC":
                from programgarden_finance.ls.overseas_futureoption.real.WOC.blocks import WOCRealRequest, WOCRealRequestBody
                req = WOCRealRequest(
                    body=WOCRealRequestBody(
                        tr_key=symbol
                    )
                )
                req.header.tr_type = "4"
            elif tr_cd == "WOH":
                from programgarden_finance.ls.overseas_futureoption.real.WOH.blocks import WOHRealRequest, WOHRealRequestBody
                req = WOHRealRequest(
                    body=WOHRealRequestBody(
                        tr_key=symbol
                    )
                )
                req.header.tr_type = "4"

            if req is None:
                break

            req.header.token = self._token_manager.access_token

            req = {"header": req.header.model_dump(), "body": req.body.model_dump()}

            asyncio.create_task(self._ws.send(json.dumps(req)))

    def _add_real_order(self):
        """
        해외주식 주문 체결, 정정, 취소, 거부 실시간 요청을 전부 자동 등록합니다.
        (증권사에서 AS0, AS2, AS3, AS4 어떤걸로 요청해도 전부 다 자동 등록되기 때문에 구분지어서 요청할 필요가 없습니다.)
        """
        if not self._connected_event.is_set():
            raise RuntimeError("WebSocket is not connected")

        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        # AS0, AS2, AS3, AS4 어떤걸로 요청해도 증권사에서는 전부 다
        # 자동 등록되기 때문에 구분지어서 요청할 필요가 없다.
        if self._as01234_connect is False:
            from programgarden_finance.ls.overseas_stock.real.AS1.blocks import AS1RealRequest, AS1RealRequestBody, AS1RealRequestHeader
            req = AS1RealRequest(
                header=AS1RealRequestHeader(
                    token=self._token_manager.access_token,
                    tr_type="1"
                ),
                body=AS1RealRequestBody(
                    tr_cd="",
                    tr_key="",
                )
            )
            req = {"header": req.header.model_dump(), "body": req.body.model_dump()}
            asyncio.create_task(self._ws.send(json.dumps(req)))

    def _remove_real_order(self):
        """
        해외주식 주문 접수, 체결, 정정, 취소, 거부 실시간 요청을 해제합니다.
        """
        if not self._connected_event.is_set():
            raise RuntimeError("WebSocket is not connected")

        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        if self._as01234_connect is True:
            # 실시간은 주문 상태는 전체를 끊는데 json을 만들어야해서 AS1을 가지고 한거다. AS0, AS2, AS3, AS4 아무거나 해도 상관없다.
            from programgarden_finance.ls.overseas_stock.real.AS1.blocks import AS1RealRequest, AS1RealRequestBody, AS1RealRequestHeader
            req = AS1RealRequest(
                header=AS1RealRequestHeader(
                    token=self._token_manager.access_token,
                    tr_type="2"
                ),
                body=AS1RealRequestBody(
                    tr_cd="",
                    tr_key="",
                )
            )
            req = {"header": req.header.model_dump(), "body": req.body.model_dump()}
            asyncio.create_task(self._ws.send(json.dumps(req)))
