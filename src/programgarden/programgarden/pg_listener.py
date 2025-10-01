from enum import Enum
from dotenv import load_dotenv
import threading
import queue
import concurrent.futures
import inspect
from typing import Any, Dict, Callable, Optional, TypedDict
from programgarden_core import BaseStrategyConditionResponseType, OrderRealResponseType

load_dotenv()


class ListenerCategoryType(Enum):
    STRATEGIES = "strategies"
    REAL_ORDER = "real_order"


class RealOrderPayload(TypedDict):
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
    condition_id: str
    message: Optional[str]
    response: Optional[BaseStrategyConditionResponseType] = None,


class RealTimeListener:
    """
    Threaded event queue + ThreadPoolExecutor dispatch.
    daemon runs in background; the worker is started on first emit or when handlers are set.
    Now supports four handlers: strategies, buy, sell, error.
    """

    def __init__(self, max_workers: int = 4) -> None:
        self._handlers: Dict[ListenerCategoryType, Optional[Callable[[Dict[str, Any]], Any]]] = {
            ListenerCategoryType.STRATEGIES: None,
            ListenerCategoryType.REAL_ORDER: None,
        }
        self._q: "queue.Queue[Optional[Dict[str, Any]]]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def set_handler(self, category_type: ListenerCategoryType, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """Set the handler for a specific category type."""
        self._handlers[category_type] = handler

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self, wait: bool = True) -> None:
        self._running = False
        self._q.put(None)
        if self._thread is not None and wait:
            self._thread.join(timeout=2)
        try:
            self._executor.shutdown(wait=wait)
        except Exception:
            pass

    def emit(self, category_type: ListenerCategoryType, data: Dict[str, Any]) -> None:
        self._q.put({"type": category_type, "data": data})
        if not self._running:
            self.start()

    def _worker(self) -> None:
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
    def __init__(self, emitter: Optional[Callable[[ListenerCategoryType, Dict[str, Any]], None]] = None) -> None:
        self._lock = threading.Lock()
        self._last_payload: Dict[str, Any] = {}
        self._emitter = emitter

    def emit(self, payload: StrategyPayload) -> None:
        with self._lock:
            self._last_payload = dict(payload)
            payload_local: StrategyPayload = dict(self._last_payload)  # type: ignore[arg-type]
        if self._emitter:
            try:
                self._emitter(ListenerCategoryType.STRATEGIES, payload_local)
            except Exception:
                pass


class RealOrderListener:
    def __init__(self, emitter: Optional[Callable[[ListenerCategoryType, Dict[str, Any]], None]] = None) -> None:
        self._lock = threading.Lock()
        self._last_payload: Dict[str, Any] = {}
        self._emitter = emitter

    def emit(self, payload: RealOrderPayload) -> None:
        with self._lock:
            self._last_payload = dict(payload)
            payload_local: RealOrderPayload = dict(self._last_payload)  # type: ignore[arg-type]
        if self._emitter:
            try:
                self._emitter(ListenerCategoryType.REAL_ORDER, payload_local)
            except Exception:
                pass


class PGListener:
    """Module-level singleton wrapper for all four category listeners."""

    def __init__(self, max_workers: int = 4) -> None:
        self.realtime = RealTimeListener(max_workers=max_workers)
        self.strategies = StrategiesListener(emitter=self.realtime.emit)
        self.real_order = RealOrderListener(emitter=self.realtime.emit)

    def set_strategies_handler(self, handler: Callable[[StrategyPayload], Any]) -> None:
        self.realtime.set_handler(ListenerCategoryType.STRATEGIES, handler)
        self.realtime.start()

    def set_real_order_handler(self, handler: Callable[[RealOrderPayload], Any]) -> None:
        self.realtime.set_handler(ListenerCategoryType.REAL_ORDER, handler)
        self.realtime.start()

    def emit_strategies(self, payload: StrategyPayload) -> None:
        self.strategies.emit(payload)

    def emit_real_order(self, payload: RealOrderPayload) -> None:
        self.real_order.emit(payload)

    def stop(self) -> None:
        self.realtime.stop()


# module-level singleton
pg_listener = PGListener()


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

#     # emit_error with ErrorPayload
#     set_error_handler(lambda payload: print(f"Error: {payload}"))
#     pg_listener.emit_error({"error_code": 123, "message": "additional info", "data": {}})
#     import time
#     # 이벤트가 워커에서 처리될 시간을 약간 줌
#     time.sleep(0.1)
#     # 워커와 executor를 정리(옵션)
#     pg_listener.stop()
