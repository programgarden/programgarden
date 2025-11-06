"""Event listener bridge between Programgarden core and host applications.

EN:
        Provides thread-safe listener utilities that forward condition results,
        real-order updates, and error payloads to user-defined callbacks. The
        module exposes a singleton ``pg_listener`` with helper methods to emit
        structured payloads and register handlers. All emissions run on a
        background worker backed by :class:`concurrent.futures.ThreadPoolExecutor`.

KR:
        조건 결과, 실시간 주문 업데이트, 오류 정보를 사용자 콜백에 전달하는 스레드 안전
        리스너 유틸리티를 제공합니다. 백그라운드 워커와
        :class:`concurrent.futures.ThreadPoolExecutor` 기반으로 동작하는 싱글턴
        ``pg_listener``를 통해 핸들러 등록과 페이로드 발행을 간편하게 수행할 수 있습니다.
"""

from enum import Enum
from dotenv import load_dotenv
import threading
import queue
import concurrent.futures
import inspect
from typing import Any, Dict, Callable, Optional, TypedDict, Union
from typing_extensions import NotRequired
from programgarden_core import (
    OrderRealResponseType,
    BaseStrategyConditionResponseOverseasStockType,
    BaseStrategyConditionResponseOverseasFuturesType
)
from programgarden_core.exceptions import BasicException

load_dotenv()


class ListenerCategoryType(Enum):
    """Enumerate supported listener queues (EN/KR described).

    EN:
        Distinguishes strategy events, real-order updates, and error notifications
        so handlers can subscribe selectively.

    KR:
        전략 이벤트, 실시간 주문 업데이트, 오류 알림을 구분하여 핸들러가 원하는
        카테고리만 구독할 수 있도록 합니다.
    """

    STRATEGIES = "strategies"
    REAL_ORDER = "real_order"
    ERROR = "error"


class RealOrderPayload(TypedDict):
    """Structured payload emitted for real-order updates.

    EN:
        Bundles the unified order type, human-readable message, and raw response
        from LS real-time APIs.

    KR:
        LS 실시간 API의 응답을 기반으로 통합 주문 유형, 메시지, 원본 응답을 묶은
        자료구조입니다.
    """

    order_type: OrderRealResponseType
    """
    실시간 상태
    """
    message: str
    """
    작업 내용
    """
    response: Dict[str, Any]
    """
    실시간 데이터
    """


class StrategyPayload(TypedDict):
    """Payload emitted when a strategy condition produces a response.

    EN:
        Contains the originating condition identifier, optional message, and the
        structured condition response object.

    KR:
        발생한 조건 식별자, 선택적 메시지, 구조화된 조건 응답 객체를 포함합니다.
    """

    condition_id: str
    message: NotRequired[str]
    response: NotRequired[Union[BaseStrategyConditionResponseOverseasStockType, BaseStrategyConditionResponseOverseasFuturesType]]


class ErrorPayload(TypedDict):
    """Normalized error payload shared with host applications.

    EN:
        Mirrors :class:`programgarden_core.exceptions.BasicException` payloads and
        includes arbitrary ``data`` for context.

    KR:
        :class:`programgarden_core.exceptions.BasicException` 페이로드와 동일한 구조를
        따르며 추가 컨텍스트 데이터를 포함합니다.
    """

    code: str
    message: str
    data: NotRequired[Dict[str, Any]]


class RealTimeListener:
    """Thread-safe dispatcher for Programgarden listener categories.

    EN:
        Maintains a queue that is drained by a background daemon thread. Payloads
        are delivered to registered handlers using a thread pool, and coroutine
        handlers are executed safely via ``asyncio.run``.

    KR:
        백그라운드 데몬 스레드가 큐를 소모하면서 등록된 핸들러로 페이로드를 전달합니다.
        코루틴 핸들러는 ``asyncio.run``을 통해 안전하게 실행되며, 스레드 풀을 활용해
        동시성을 확보합니다.
    """

    def __init__(self, max_workers: int = 4) -> None:
        """Initialize handler registry, worker queue, and thread pool.

        EN:
            Prepares handler slots per category, allocates the queue consumed by
            the worker, and creates a :class:`ThreadPoolExecutor` with the desired
            concurrency.

        KR:
            카테고리별 핸들러 슬롯을 준비하고 워커가 사용할 큐를 할당하며 원하는 동시성
            수준의 :class:`ThreadPoolExecutor`를 생성합니다.
        """
        self._handlers: Dict[ListenerCategoryType, Optional[Callable[[Dict[str, Any]], Any]]] = {
            ListenerCategoryType.STRATEGIES: None,
            ListenerCategoryType.REAL_ORDER: None,
            ListenerCategoryType.ERROR: None,
        }
        self._q: "queue.Queue[Optional[Dict[str, Any]]]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def set_handler(self, category_type: ListenerCategoryType, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """Register a handler for the given listener category.

        EN:
            Assigns (or replaces) the callable invoked when events of the specified
            type are emitted. Accepts synchronous or asynchronous functions.

        KR:
            지정된 유형의 이벤트가 발생할 때 호출할 동기/비동기 핸들러를 등록하거나
            교체합니다.
        """
        self._handlers[category_type] = handler

    def start(self) -> None:
        """Launch the background worker thread if not running.

        EN:
            Ensures the queue-draining daemon is active so newly emitted events are
            dispatched immediately.

        KR:
            새로 발행된 이벤트를 즉시 전달할 수 있도록 큐를 소비하는 데몬 스레드를
            기동합니다.
        """
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self, wait: bool = True) -> None:
        """Gracefully shut down worker thread and executor.

        EN:
            Signals the worker loop to exit, optionally waits for thread/join, and
            shuts down the executor to release resources.

        KR:
            워커 루프에 종료 신호를 보내고 필요 시 스레드를 기다린 뒤, 실행기를 종료하여
            자원을 해제합니다.
        """
        self._running = False
        self._q.put(None)
        if self._thread is not None and wait:
            self._thread.join(timeout=2)
        try:
            self._executor.shutdown(wait=wait)
        except Exception:
            pass

    def emit(self, category_type: ListenerCategoryType, data: Dict[str, Any]) -> None:
        """Enqueue a payload for later dispatch and auto-start the worker.

        EN:
            Places the payload on the queue and starts the worker if it has not
            been initialized yet.

        KR:
            페이로드를 큐에 적재하고 워커가 실행 중이 아니면 즉시 시작합니다.
        """
        self._q.put({"type": category_type, "data": data})
        if not self._running:
            self.start()

    def _worker(self) -> None:
        """Continuously drain the queue and forward events to handlers.

        EN:
            Implements a blocking loop with timeout so the worker can terminate
            when ``_running`` flips to ``False``. Remaining items are drained before
            exit to avoid message loss.

        KR:
            ``_running`` 플래그가 ``False``가 되면 종료될 수 있도록 타임아웃이 있는
            루프를 사용하며, 종료 전에 남은 항목을 비워 메시지 손실을 방지합니다.
        """
        while True:
            try:
                item = self._q.get(timeout=1)
            except Exception:
                if not self._running and self._q.empty():
                    break
                continue
            if item is None:
                break
            event_type = item.get("type")
            data = item.get("data")
            self._dispatch(event_type, data)
        # drain remaining
        while not self._q.empty():
            item = self._q.get_nowait()
            if item is None:
                break
            self._dispatch(item.get("type"), item.get("data"))

    def _dispatch(self, event_type: Any, data: Dict[str, Any]) -> None:
        handler = self._handlers.get(event_type)
        if handler is None:
            return
        # support sync or async handlers
        if inspect.iscoroutinefunction(handler):
            def _run_coro():
                import asyncio
                asyncio.run(handler(data))
            self._executor.submit(_run_coro)
            return
        try:
            result = handler(data)
            if inspect.iscoroutine(result):
                def _run_result_coro():
                    import asyncio
                    asyncio.run(result)
                self._executor.submit(_run_result_coro)
        except Exception:
            pass


class StrategiesListener:
    """Store and emit the latest strategy payload via the realtime emitter.

    EN:
        Maintains the last payload for synchronous inspection and emits copies via
        the optional ``emitter`` callback to avoid mutation.

    KR:
        최근 페이로드를 보관하면서 선택적으로 제공된 ``emitter`` 콜백을 사용해 복사본을
        발행합니다. 원본 변형을 방지하기 위해 복사본을 전달합니다.
    """

    def __init__(self, emitter: Optional[Callable[[ListenerCategoryType, Dict[str, Any]], None]] = None) -> None:
        self._lock = threading.Lock()
        self._last_payload: Dict[str, Any] = {}
        self._emitter = emitter

    def emit(self, payload: StrategyPayload) -> None:
        """Persist the latest payload and forward it to the emitter.

        EN:
            Copies the incoming payload while holding a lock to keep state
            consistent for concurrent readers, then emits it if an emitter is
            configured.

        KR:
            락을 잡아 동시 접근 시 상태를 일관되게 유지하고, 복사본을 생성한 뒤
            emitter가 설정되어 있으면 발행합니다.
        """
        with self._lock:
            self._last_payload = dict(payload)
            payload_local: StrategyPayload = dict(self._last_payload)  # type: ignore[arg-type]
        if self._emitter:
            try:
                self._emitter(ListenerCategoryType.STRATEGIES, payload_local)
            except Exception:
                pass


class RealOrderListener:
    """Persist and emit the latest real-order payload.

    EN:
        Keeps a thread-safe copy of the newest payload and forwards a duplicate to
        the realtime emitter when present.

    KR:
        최신 페이로드를 스레드 안전하게 보관하고, 실시간 emitter가 구성된 경우 복사본을
        전달합니다.
    """

    def __init__(self, emitter: Optional[Callable[[ListenerCategoryType, Dict[str, Any]], None]] = None) -> None:
        self._lock = threading.Lock()
        self._last_payload: Dict[str, Any] = {}
        self._emitter = emitter

    def emit(self, payload: RealOrderPayload) -> None:
        """Update last known payload and emit it to listeners.

        EN:
            Uses a lock to avoid race conditions while copying the payload, then
            emits it if the emitter callback is defined.

        KR:
            페이로드를 복사하는 동안 레이스 컨디션을 방지하기 위해 락을 사용하고,
            emitter가 설정되어 있으면 전달합니다.
        """
        with self._lock:
            self._last_payload = dict(payload)
            payload_local: RealOrderPayload = dict(self._last_payload)  # type: ignore[arg-type]
        if self._emitter:
            try:
                self._emitter(ListenerCategoryType.REAL_ORDER, payload_local)
            except Exception:
                pass


class ErrorListener:
    """Persist and emit normalized error payloads.

    EN:
        Ensures a ``data`` dict is always present and forwards copies to the
        configured emitter.

    KR:
        ``data`` 딕셔너리가 항상 존재하도록 보장하고, 설정된 emitter로 복사본을 전달합니다.
    """

    def __init__(self, emitter: Optional[Callable[[ListenerCategoryType, Dict[str, Any]], None]] = None) -> None:
        self._lock = threading.Lock()
        self._last_payload: Dict[str, Any] = {}
        self._emitter = emitter

    def emit(self, payload: ErrorPayload) -> None:
        """Normalize error payload and forward it to the emitter.

        EN:
            Copies the payload, ensures ``data`` exists to simplify downstream
            consumers, then emits the sanitized version.

        KR:
            페이로드를 복사하여 ``data`` 키가 항상 존재하도록 한 뒤 정리된 버전을
            emitter에 전달합니다.
        """
        with self._lock:
            self._last_payload = dict(payload)
            payload_local: ErrorPayload = dict(self._last_payload)  # type: ignore[arg-type]
            payload_local.setdefault("data", {})
        if self._emitter:
            try:
                self._emitter(ListenerCategoryType.ERROR, payload_local)
            except Exception:
                pass


class PGListener:
    """Facade that binds specialized listeners to the realtime dispatcher.

    EN:
        Instantiates category-specific listener helpers and wires them to a shared
        :class:`RealTimeListener` emitter.

    KR:
        카테고리별 리스너 헬퍼를 생성하고 공통 :class:`RealTimeListener` emitter에 연결하는
        파사드입니다.
    """

    def __init__(self, max_workers: int = 4) -> None:
        self.realtime = RealTimeListener(max_workers=max_workers)
        self.strategies = StrategiesListener(emitter=self.realtime.emit)
        self.real_order = RealOrderListener(emitter=self.realtime.emit)
        self.error = ErrorListener(emitter=self.realtime.emit)

    def set_strategies_handler(self, handler: Callable[[StrategyPayload], Any]) -> None:
        """Register a strategy handler and ensure the realtime worker is running."""
        self.realtime.set_handler(ListenerCategoryType.STRATEGIES, handler)
        self.realtime.start()

    def set_real_order_handler(self, handler: Callable[[RealOrderPayload], Any]) -> None:
        """Register a real-order handler and ensure the realtime worker is running."""
        self.realtime.set_handler(ListenerCategoryType.REAL_ORDER, handler)
        self.realtime.start()

    def set_error_handler(self, handler: Callable[[ErrorPayload], Any]) -> None:
        """Register an error handler and ensure the realtime worker is running."""
        self.realtime.set_handler(ListenerCategoryType.ERROR, handler)
        self.realtime.start()

    def emit_strategies(self, payload: StrategyPayload) -> None:
        """Emit a strategy payload through the strategies listener."""
        self.strategies.emit(payload)

    def emit_real_order(self, payload: RealOrderPayload) -> None:
        """Emit a real-order payload through the real-order listener."""
        self.real_order.emit(payload)

    def emit_exception(self, exc: Exception, *, data: Optional[Dict[str, Any]] = None) -> None:
        """Normalize and emit exceptions unless already reported."""
        if getattr(exc, "_pg_error_emitted", False):
            return
        payload = build_error_payload(exc, data=data)
        self.error.emit(payload)
        try:
            setattr(exc, "_pg_error_emitted", True)
        except Exception:
            pass

    def stop(self) -> None:
        """Stop the realtime dispatcher and worker threads."""
        self.realtime.stop()


# module-level singleton
pg_listener = PGListener()


def build_error_payload(exc: Exception, data: Optional[Dict[str, Any]] = None) -> ErrorPayload:
    """Translate Python exceptions into the standardized error payload shape.

    EN:
        Delegates to :class:`BasicException.to_payload` when available and ensures
        ``data`` is always a dict.

    KR:
        :class:`BasicException.to_payload`을 사용할 수 있으면 위임하고, ``data``가 항상
        딕셔너리 형태를 갖도록 보장합니다.
    """
    extra_data: Dict[str, Any] = dict(data or {})
    if isinstance(exc, BasicException):
        payload = exc.to_payload(extra=extra_data)
        payload.setdefault("data", {})
        return payload

    message = str(exc) or exc.__class__.__name__
    code_value = getattr(exc, "code", "UNEXPECTED_ERROR")
    payload = {
        "code": str(code_value),
        "message": message,
        "data": extra_data,
    }
    return payload


# def set_strategies_handler(handler: Callable[[EventPayload], Any]) -> None:
#     pg_listener.set_strategies_handler(handler)


# def set_error_handler(handler: Callable[[ErrorPayload], Any]) -> None:
#     pg_listener.set_error_handler(handler)


# if __name__ == "__main__":
#     # example handlers expect the full payload dicts
#     set_strategies_handler(lambda payload: print(f"Event: {payload}"))
#     pg_listener.emit_strategies(
#         EventPayload(
#             code="tr",
#             message="Transaction event",
#             data={"key": "value"}
#         )
#     )

#     set_error_handler(lambda payload: print(f"Error: {payload}"))
#     import time
#     # 이벤트가 워커에서 처리될 시간을 약간 줌
#     time.sleep(0.1)
#     # 워커와 executor를 정리(옵션)
#     pg_listener.stop()
