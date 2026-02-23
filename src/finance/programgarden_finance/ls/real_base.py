"""Base utilities for LS Securities real-time websocket handling.

EN:
    Provides reconnection-aware websocket scaffolding, dynamic TR response
    resolution, and convenience hooks for subscribing to live market/order
    feeds.

KO:
    재연결을 고려한 웹소켓 기반 구조와 실시간 TR 응답 동적 로딩, 시세/주문
    구독을 위한 헬퍼를 제공합니다.
"""

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

# cache for dynamic response class lookups (EN/KR)
# EN: tr_cd -> (response_model, header_model, body_model) or None
# KO: tr_cd에 대응하는 응답/헤더/바디 모델 캐시입니다 (없으면 None)
_RESPONSE_CLASS_CACHE: Dict[str, Optional[tuple]] = {}

# candidate module roots where tr_cd modules may live; keep order from most likely to least
# EN: search bases for dynamic imports; KO: 동적 import 시도 순서를 정의합니다.
_RESPONSE_MODULE_BASES = [
    "programgarden_finance.ls.overseas_stock.real",
    "programgarden_finance.ls.overseas_futureoption.real",
]


class RealRequestAbstract(ABC):
    """Reconnect-capable abstract base for LS real-time requests.

    EN:
        Manages websocket lifecycle, dynamic TR model loading, and listener
        dispatching so concrete real-time clients can focus on business logic.

    KO:
        실시간 요청에 필요한 추상클래스이며, 웹소켓 연결 수명주기, TR 모델 동적 로딩, 수신 리스너 디스패치를 관리하여
        하위 클래스가 비즈니스 로직에 집중할 수 있게 합니다.
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
        self._ref_count = 0
        self._ref_lock = asyncio.Lock()  # ref_count 보호용 Lock
        # 구독 심볼 추적 (재연결 시 자동 재구독용)
        self._subscribed_symbols: Dict[str, List[str]] = {}  # tr_cd -> [symbols]
        self._stop = False

    async def is_connected(self) -> bool:
        """Check whether the websocket handshake completed.

        EN:
            Returns ``True`` once the connection event is set after a successful
            websocket handshake.

        KO:
            웹소켓 핸드셰이크가 완료되어 연결 이벤트가 설정되었을 때 ``True`` 를
            반환합니다.
        """
        return self._connected_event.is_set()

    def get_subscribed_symbols(self) -> Dict[str, List[str]]:
        """현재 구독 중인 심볼 목록 (tr_cd -> symbols)."""
        return dict(self._subscribed_symbols)

    async def connect(
        self,
        wait: bool = True,
        timeout: float = 5.0,
    ):
        """Open the websocket and launch the listener loop.

        EN:
            Optionally waits until the first successful connection. Handles
            reconnection with exponential backoff when ``reconnect`` is enabled.
            When a connection is already active, increments the reference count
            and returns immediately (singleton-safe).

        KO:
            최초 연결이 성사될 때까지 대기할 수 있으며 ``reconnect`` 설정 시
            지수 백오프 기반으로 재연결을 처리합니다. 이미 연결이 활성화된 경우
            참조 카운트만 증가시키고 즉시 반환합니다 (싱글톤 안전).

        Parameters:
            wait (bool): EN: Wait for connection event. KO: 연결 완료까지 대기 여부.
            timeout (float): EN: Max seconds to wait when ``wait`` is True. KO:
                ``wait`` 가 True일 때 대기 시간.
        """

        need_connect = False
        async with self._ref_lock:
            self._ref_count += 1

            # 이미 연결됨 → 즉시 반환
            if self._connected_event.is_set():
                return

            # 연결 시도 중 → wait만 수행
            if self._listen_task is not None and not self._listen_task.done():
                need_connect = False
            else:
                self._stop = False
                need_connect = True

        # Lock 밖에서 wait (Lock 중 대기 시 deadlock 방지)
        if not need_connect:
            if wait:
                try:
                    await asyncio.wait_for(self._connected_event.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    raise RuntimeError("Timeout waiting for websocket connection")
            return

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
                    target_uri = None
                    if self._token_manager is not None:
                        target_uri = getattr(self._token_manager, "wss_url", None)
                    # NOTE: ping_interval=None disables automatic pings from websockets library
                    # to avoid interference with message reception. Manual pings are sent 
                    # via recv_timeout to detect stalled connections.
                    async with connect(
                        uri=target_uri or URLS.WSS_URL,
                        ping_interval=None,
                        ping_timeout=None,
                    ) as ws:
                        self._ws = ws
                        # signal that a connection is available
                        try:
                            self._connected_event.set()
                        except Exception:
                            pass

                        # 재연결 시 이전 구독 자동 복원
                        if backoff > 1.0 and self._subscribed_symbols:
                            import logging
                            _logger = logging.getLogger("programgarden_finance.real")
                            for _tr_cd, _syms in self._subscribed_symbols.items():
                                if _syms:
                                    try:
                                        self._add_message_symbols(list(_syms), _tr_cd)
                                        _logger.info(
                                            f"WebSocket 재연결 후 자동 재구독: "
                                            f"{_tr_cd} {len(_syms)}개 심볼"
                                        )
                                    except Exception as _e:
                                        _logger.error(
                                            f"WebSocket 재구독 실패 ({_tr_cd}): {_e}"
                                        )

                        backoff = 1.0  # reset backoff after successful connect

                        # Inner loop: active connection receive loop
                        while not self._stop:
                            try:
                                # blocking recv - no timeout for real-time streaming
                                raw = await ws.recv()
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

                # H-15: 재연결 중 메시지 누락 경고
                import logging
                _logger = logging.getLogger("programgarden_finance.real")
                _logger.warning(
                    f"WebSocket 연결 끊김 - 재연결 시도 중 "
                    f"(backoff={backoff:.1f}s). 이 기간 동안 시세/체결 데이터가 누락될 수 있습니다."
                )

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

    async def close(self, force: bool = False):
        """Stop listening and close the websocket connection.

        EN:
            Decrements the reference count and only performs the actual
            shutdown when the count reaches zero.  Use ``force=True`` to
            bypass reference counting and close immediately (also removes
            the instance from the singleton cache).

        KO:
            참조 카운트를 감소시키고 0이 되었을 때만 실제 종료를 수행합니다.
            ``force=True`` 를 사용하면 참조 카운트를 무시하고 즉시 종료하며,
            싱글톤 캐시에서 인스턴스를 제거합니다.

        Parameters:
            force (bool): EN: Close immediately regardless of ref count.
                KO: 참조 카운트를 무시하고 즉시 종료.
        """
        async with self._ref_lock:
            if not force:
                self._ref_count = max(0, self._ref_count - 1)
                if self._ref_count > 0:
                    return
            elif self._ref_count > 1:
                import logging
                _logger = logging.getLogger("programgarden_finance.real")
                _logger.warning(
                    f"WebSocket force close while ref_count={self._ref_count}. "
                    f"다른 {self._ref_count - 1}개 노드의 실시간 연결이 끊어집니다."
                )

            self._ref_count = 0
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

        self._connected_event.clear()
        self._cleanup_singleton_cache()

    def _cleanup_singleton_cache(self):
        """Remove this instance from the singleton caches.

        EN:
            Cleans up references in OverseasStock and OverseasFutureoption
            class-level caches so the next ``real()`` call creates a fresh
            instance.

        KO:
            OverseasStock 및 OverseasFutureoption 클래스 레벨 캐시에서
            자기 자신을 제거하여 다음 ``real()`` 호출 시 새 인스턴스가
            생성되도록 합니다.
        """
        tm_id = id(self._token_manager)
        try:
            from programgarden_finance.ls.overseas_stock import OverseasStock
            if OverseasStock._real_instances.get(tm_id) is self:
                del OverseasStock._real_instances[tm_id]
        except ImportError:
            pass
        try:
            from programgarden_finance.ls.overseas_futureoption import OverseasFutureoption
            if OverseasFutureoption._real_instances.get(tm_id) is self:
                del OverseasFutureoption._real_instances[tm_id]
        except ImportError:
            pass

    def _on_message(self, message_key: str,  listener: Callable[[Any], None]):
        """Register a callback to handle messages for a specific TR code.

        EN:
            Raises if the websocket is not yet connected.

        KO:
            웹소켓이 연결되지 않은 경우 예외를 발생시키며, 특정 TR 코드에 대한
            콜백을 등록합니다.
        """
        if not self._connected_event.is_set():
            raise RuntimeError("WebSocket is not connected")
        self._on_message_listeners[message_key] = listener

    def _on_remove_message(self, message_key: str):
        """Detach a registered listener and clean up order subscriptions.

        EN:
            Removes the listener and, when no listeners remain, clears
            auto-registered order streams.

        KO:
            등록된 리스너를 제거하며 더 이상 리스너가 없을 경우 자동 주문 구독을
            해제합니다.
        """
        if not self._connected_event.is_set():
            raise RuntimeError("WebSocket is not connected")
        if message_key in self._on_message_listeners:
            del self._on_message_listeners[message_key]

        if len(self._on_message_listeners) == 0:
            self._as01234_connect = False
            self._remove_real_order()

    def _add_message_symbols(self, symbols: List[str], tr_cd: str):
        """Subscribe to real-time feeds for given symbols and TR code.

        EN:
            Builds the correct request model per TR code and sends a subscribe
            message with transaction type ``3``. Also tracks subscribed symbols
            for automatic resubscription after reconnection.

        KO:
            TR 코드별로 올바른 요청 모델을 생성하고 트랜잭션 타입 ``3`` 으로 구독
            메시지를 전송합니다. 재연결 시 자동 재구독을 위해 구독 심볼을 추적합니다.

        Parameters:
            symbols (List[str]): EN: Symbols to subscribe. KO: 구독할 종목 코드들.
            tr_cd (str): EN: TR identifier to route request. KO: 요청 라우팅용 TR 코드.
        """
        if not self._connected_event.is_set():
            raise RuntimeError("WebSocket is not connected")

        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        # 구독 심볼 추적 (재연결 시 자동 재구독용)
        if tr_cd not in self._subscribed_symbols:
            self._subscribed_symbols[tr_cd] = []
        for sym in symbols:
            if sym not in self._subscribed_symbols[tr_cd]:
                self._subscribed_symbols[tr_cd].append(sym)

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
        """Unsubscribe from real-time feeds for given symbols.

        EN:
            Reuses the same TR-specific models with transaction type ``4`` to
            cancel registrations. Also removes symbols from the tracked list.

        KO:
            동일한 TR 모델을 사용하되 트랜잭션 타입 ``4`` 로 전송하여 실시간 등록을
            해제합니다. 구독 추적 목록에서도 제거합니다.
        """
        if not self._connected_event.is_set():
            raise RuntimeError("WebSocket is not connected")

        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        # 구독 추적에서 제거
        if tr_cd in self._subscribed_symbols:
            for sym in symbols:
                try:
                    self._subscribed_symbols[tr_cd].remove(sym)
                except ValueError:
                    pass
            if not self._subscribed_symbols[tr_cd]:
                del self._subscribed_symbols[tr_cd]

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
        """Auto-subscribe to all overseas stock order lifecycle feeds.

        EN:
            Registers AS0/AS2/AS3/AS4 streams in one shot since the broker
            auto-enables every order channel.

        KO:
            증권사가 AS0/AS2/AS3/AS4 주문 채널을 자동 활성화하므로 한 번의 호출로
            해외주식 주문 전체 상태를 등록합니다.
        """
        if not self._connected_event.is_set():
            raise RuntimeError("WebSocket is not connected")

        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")

        # AS0, AS2, AS3, AS4 어떤걸로 요청해도 증권사에서는 전부 다
        # 자동 등록되기 때문에 구분지어서 요청할 필요가 없다.
        if self._as01234_connect is False:
            self._as01234_connect = True  # 중복 등록 방지
            from programgarden_finance.ls.overseas_stock.real.AS1.blocks import AS1RealRequest, AS1RealRequestBody, AS1RealRequestHeader
            req = AS1RealRequest(
                header=AS1RealRequestHeader(
                    token=self._token_manager.access_token,
                    tr_type="1"
                ),
                body=AS1RealRequestBody(
                    tr_cd="AS1",
                    tr_key="",
                )
            )
            req = {"header": req.header.model_dump(), "body": req.body.model_dump()}
            asyncio.create_task(self._ws.send(json.dumps(req)))

    def _remove_real_order(self):
        """Unsubscribe from overseas stock order lifecycle feeds.

        EN:
            Sends the deregistration request (transaction type ``2``) using the
            AS1 schema.

        KO:
            AS1 스키마를 이용해 트랜잭션 타입 ``2`` 로 실시간 주문 구독을 해제합니다. 한번의 해제로 주문 접수, 체결, 정정, 취소, 거부 실시간 요청을 해제합니다.
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
