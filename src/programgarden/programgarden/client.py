"""Programgarden client wrapper for orchestrating trading systems.

EN:
    This module exposes the `Programgarden` client which coordinates system
    configuration validation, authentication, execution, and lifecycle
    callbacks for strategy developers integrating with LS Securities APIs.

KR:
    이 모듈은 LS 증권 API와 연동하는 전략 개발자를 위해 시스템 설정 검증,
    인증, 실행, 라이프사이클 콜백을 조율하는 `Programgarden` 클라이언트를
    제공합니다.
"""

import asyncio
import logging
import threading
from typing import Callable, Dict, Any
from programgarden_core import normalize_system_config

logger = logging.getLogger("programgarden.client")
from programgarden_core.bases import SystemType
from programgarden_finance import LS
from programgarden_core import EnforceKoreanAliasMeta
from programgarden_core.exceptions import (
    BasicException,
    LoginException,
    NotExistCompanyException,
    PerformanceExceededException,
    SystemException,
    SystemInitializationException,
    SystemShutdownException,
)
from programgarden import SystemExecutor
from programgarden.pg_listener import (
    StrategyPayload,
    OrderPayload,
    RealOrderPayload,
    ErrorPayload,
    PerformancePayload,
    pg_listener
)
from .system_keys import exist_system_keys_error


class Programgarden(metaclass=EnforceKoreanAliasMeta):
    """High-level client facade for executing Programgarden trading systems.

    EN:
        The `Programgarden` client encapsulates lifecycle management for a
        trading strategy: it validates configuration, handles asynchronous
        execution, coordinates login with LS Securities, and publishes runtime
        events through the listener subsystem.

    KR:
        `Programgarden` 클라이언트는 거래 전략의 라이프사이클을 캡슐화하여
        구성 검증, 비동기 실행, LS 증권 로그인, 리스너 서브시스템을 통한
        런타임 이벤트 발행을 책임집니다.

    Attributes:
        _lock (threading.RLock):
            EN: Reentrant lock protecting shared client state.
            KR: 클라이언트의 공유 상태를 보호하는 재진입 가능 잠금입니다.
        _executor (SystemExecutor | None):
            EN: Lazily instantiated executor coordinating system tasks.
            KR: 시스템 태스크를 조율하는 지연 생성 실행기입니다.
        _executor_lock (threading.RLock):
            EN: Double-checked locking guard for executor creation.
            KR: 실행기 생성 시 사용하는 중복 확인 잠금입니다.
        _task (asyncio.Task | None):
            EN: Handle to the currently running asynchronous execution
            task, preventing duplicate runs in a live event loop.
            KR: 현재 실행 중인 비동기 실행 태스크를 가리키는 핸들로,
            실시간 이벤트 루프에서 중복 실행을 방지합니다.
        _shutdown_notified (bool):
            EN: Flag indicating whether shutdown notifications have been
            emitted to listeners.
            KR: 종료 알림이 리스너에 전파되었는지 나타내는 플래그입니다.
    """

    def __init__(self):

        # EN: Synchronization guard ensuring thread-safe access to state.
        # KR: 상태에 대한 스레드 안전 접근을 보장하는 동기화 잠금입니다.
        self._lock = threading.RLock()

        # EN: Lazily instantiated executor pointer; initialized on demand.
        # KR: 필요 시 생성되는 지연 초기화 실행기 포인터입니다.
        self._executor = None
        self._executor_lock = threading.RLock()

        # EN: Async task handle preventing duplicate execution within an
        #          active event loop.
        # KR: 활성 이벤트 루프에서 중복 실행을 방지하는 비동기 태스크 핸들입니다.
        self._task = None
        self._shutdown_notified = False
        self._loop = None

    @property
    def executor(self):
        """Return the lazily constructed `SystemExecutor` instance.

        EN:
            Ensures a single `SystemExecutor` is created using
            double-checked locking so concurrent threads share the same
            executor reference.

        KR:
            이 프로퍼티는 이중 확인 잠금 패턴을 사용하여 하나의
            `SystemExecutor`만 생성하고, 동시 스레드가 동일한 실행기를 사용하도록
            보장합니다.

        Returns:
            SystemExecutor: EN: Shared executor instance for the current
                client.
                KR: 현재 클라이언트와 공유되는 실행기 인스턴스입니다.
        """
        if getattr(self, "_executor", None) is None:
            with self._executor_lock:
                if getattr(self, "_executor", None) is None:
                    self._executor = SystemExecutor()
        return self._executor

    def get_performance_status(self, sample_interval: float = 0.05) -> Dict[str, Any]:
        """Get current system performance metrics.

        EN:
            Returns a snapshot of the current process's CPU and memory usage.
            Requires the system to be initialized (executor created).

        KR:
            현재 프로세스의 CPU 및 메모리 사용량 스냅샷을 반환합니다.
            시스템이 초기화되어 있어야 합니다(실행기 생성).

        Args:
            sample_interval (float):
                EN: Optional blocking duration for CPU sampling. Concurrency
                is also blocked during this period.
                KR: CPU 샘플링을 위한 선택적 블로킹 시간입니다. 동시성 처리도 블록킹 됩니다.

        Returns:
            Dict[str, Any]: Performance metrics snapshot.
        """
        executor = self.executor
        executor.perf_monitor.refresh_cpu_baseline()
        return executor.perf_monitor.get_current_status(sample_interval=sample_interval)

    def run(
        self,
        system: SystemType
    ):
        """Validate configuration and launch the trading system.

        EN:
            Normalizes the incoming system configuration, checks mandatory
            keys, configures display settings, and either schedules asynchronous
            execution on an existing event loop or creates a fresh loop via
            `asyncio.run`.

        KR:
            시스템 구성을 정규화하고 필수 키를 검증하며, 표시 설정을 적용한 뒤
            실행 중인 이벤트 루프에서는 비동기 태스크로, 그렇지 않을 경우
            `asyncio.run`으로 시스템을 실행합니다.

        Args:
            system (SystemType):
                EN: Declarative system definition including settings,
                securities, and strategy configuration.
                KR: 설정, 증권, 전략 구성을 포함한 선언형 시스템 정의입니다.

        Returns:
            asyncio.Task | None:
                EN: A running task when executed inside an existing loop;
                otherwise `None` because the method blocks until completion.
                KR: 기존 루프에서 실행 시 반환되는 실행 중인 태스크;
                그렇지 않으면 실행이 완료될 때까지 블록되므로 `None`을 반환합니다.

        Raises:
            SystemInitializationException:
                EN: Raised when configuration validation fails for
                unexpected reasons.
                KR: 예상치 못한 이유로 구성 검증에 실패하면 발생합니다.
            BasicException:
                EN: Propagated domain-specific validation failures.
                KR: 도메인 특화 검증 실패가 전파됩니다.
        """

        self._shutdown_notified = False

        try:
            system_config = system
            if system_config:
                system_config = normalize_system_config(system_config)

                # 시작 로그 출력
                settings = system_config.get("settings", {}) or {}
                strategies = system_config.get("strategies", []) or []
                dry_run_mode = settings.get("dry_run_mode", "live")
                system_id = settings.get("system_id", "")
                logger.info(
                    f"ProgramGarden 시작: system_id={system_id}, "
                    f"strategies={len(strategies)}, mode={dry_run_mode}"
                )
            exist_system_keys_error(system_config)
        except BasicException as exc:
            pg_listener.emit_exception(exc, domain="performance")
            raise
        except Exception as exc:
            logger.exception("System configuration validation failed")
            init_exc = SystemInitializationException(
                message="시스템 설정 검증 중 알 수 없는 오류가 발생했습니다.",
                data={"details": str(exc)},
            )
            pg_listener.emit_exception(init_exc, domain="performance")
            raise init_exc

        try:
            asyncio.get_running_loop()

            if self._task is not None and not self._task.done():
                logger.info("A task is already running; returning the existing task.")
                return self._task

            task = asyncio.create_task(self._execute(system_config))
            self._task = task

            return task

        except RuntimeError:
            return asyncio.run(self._execute(system_config))

    def _handle_shutdown(self):
        """Notify listeners about shutdown and stop event streaming.

        EN:
            Emits a single `SystemShutdownException` through the listener and
            stops the listener, ensuring downstream consumers can cleanup.

        KR:
            리스너를 중지하고 `SystemShutdownException`을 한 번만 발행하여
            다운스트림 소비자가 정리 작업을 수행할 수 있도록 합니다.

        Returns:
            None:
                EN: The helper performs side effects without returning a
                value.
                KR: 부수 효과만 수행하고 값을 반환하지 않습니다.
        """
        if self._shutdown_notified:
            return
        self._shutdown_notified = True

        logger.debug("The program has terminated.")

        shutdown_exc = SystemShutdownException()
        pg_listener.emit_exception(shutdown_exc, domain="performance")
        pg_listener.stop()

    async def _execute(self, system: SystemType):
        """Drive the asynchronous execution lifecycle for the system.

        EN:
            Ensures LS login, configures trading mode, runs the executor, and
            keeps the event loop alive while the system remains active.

        KR:
            LS 로그인을 보장하고, 거래 모드를 설정하며, 실행기를 실행한 뒤
            시스템이 활성 상태인 동안 이벤트 루프를 유지합니다.

        Args:
            system (SystemType):
                EN: Normalized system configuration dictionary.
                KR: 정규화된 시스템 구성 딕셔너리입니다.

        Raises:
            LoginException:
                EN: Raised when LS authentication fails in required
                scenarios.
                KR: 필수 시나리오에서 LS 인증이 실패하면 발생합니다.
            NotExistCompanyException:
                EN: Raised when the requested securities company is not
                supported.
                KR: 지원되지 않는 증권사를 요청하면 발생합니다.

        Returns:
            None:
                EN: This coroutine completes without a value once cleanup
                finishes.
                KR: 정리 작업이 끝나면 값을 반환하지 않고 종료합니다.
        """
        self._loop = asyncio.get_running_loop()
        try:
            securities = system.get("securities", {})
            product = securities.get("product", None)
            company = securities.get("company", None)
            if company == "ls":
                ls = LS.get_instance()

                paper_trading = bool(securities.get("paper_trading", False))
                if product == "overseas_futures" and paper_trading:
                    logger.warning("해외선물 모의투자는 홍콩거래소(HKEX)만 지원됩니다.")

                if getattr(ls, "token_manager", None) is not None:
                    ls.token_manager.configure_trading_mode(paper_trading)

                if not ls.is_logged_in():
                    login_result = await ls.async_login(
                        appkey=securities.get("appkey"),
                        appsecretkey=securities.get("appsecretkey"),
                        paper_trading=paper_trading,
                    )
                    if not login_result:
                        raise LoginException()
            else:
                raise NotExistCompanyException(
                    message=f"LS증권 이외의 증권사는 아직 지원하지 않습니다: {company}"
                )

            await self.executor.execute_system(system)

            while self.executor.running:
                await asyncio.sleep(1)

        except PerformanceExceededException as exc:
            # PerformanceExceededException은 항상 fatal
            if not getattr(exc, "_pg_error_emitted", False):
                pg_listener.emit_exception(exc, domain="performance")
            raise
        except BasicException as exc:
            if not getattr(exc, "_pg_error_emitted", False):
                pg_listener.emit_exception(exc, domain="performance")
            # severity가 fatal인 경우 즉시 종료
            severity = getattr(exc, "severity", "strategy")
            if severity == "fatal":
                logger.error(f"치명적 에러 발생으로 시스템을 종료합니다: {exc.code} - {exc.message}")
                raise
        except Exception as exc:
            logger.exception("Unexpected error during system execution")
            system_exc = SystemException(
                message="시스템 실행 중 처리되지 않은 오류가 발생했습니다.",
                code="SYSTEM_EXECUTION_ERROR",
                data={"details": str(exc)},
            )
            pg_listener.emit_exception(system_exc, domain="performance")
            # 처리되지 않은 예외는 fatal로 취급
            raise system_exc from exc

        finally:
            await self.stop()
            self._task = None
            self._handle_shutdown()

    async def stop(self):
        """Stop the running system executor and release resources.

        EN:
            Awaits graceful shutdown of the executor and logs the lifecycle
            transition for observability.

        KR:
            실행기를 정상 종료하도록 대기하고, 라이프사이클 전환을 로깅합니다.

        Returns:
            None:
                EN: The coroutine resolves after the executor stops.
                KR: 실행기가 중지된 뒤 값을 반환하지 않고 종료합니다.
        """

        if getattr(self, "_loop", None) and self._loop.is_running():
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                current_loop = None

            if current_loop != self._loop:
                future = asyncio.run_coroutine_threadsafe(self.executor.stop(), self._loop)
                await asyncio.wrap_future(future)
                logger.debug("The program has been stopped (thread-safe).")
                return

        await self.executor.stop()
        logger.debug("The program has been stopped.")

    def on_strategy(self, callback: Callable[[StrategyPayload], None]) -> None:
        """Register a callback for strategy event stream handling.

        EN:
            Subscribes the provided callable to receive strategy payloads as
            they arrive from the listener. Events include condition evaluations,
            successes, failures, and errors.

        KR:
            전략 이벤트 스트림 처리를 위한 콜백을 등록합니다. 조건 평가,
            성공, 실패, 오류 등의 이벤트를 수신합니다.

        페이로드 구조:
            - event_type: 이벤트 유형 (condition_evaluated, condition_passed, condition_failed, condition_error, strategy_completed)
            - condition_id: 조건 식별자
            - message: 메시지
            - response: 조건 응답 객체
            - error_code: 에러 코드 (에러 발생 시)
            - error_data: 에러 상세 데이터 (에러 발생 시)

        Args:
            callback (Callable[[StrategyPayload], None]):
                EN: Function invoked with structured strategy payloads.
                KR: 구조화된 전략 페이로드를 인자로 받는 함수입니다.

        Returns:
            None:
                EN: Registration has no direct return value.
                KR: 등록 과정은 별도의 반환값을 제공하지 않습니다.
        """
        pg_listener.set_strategy_handler(callback)

    def on_strategies_message(self, callback: Callable[[StrategyPayload], None]) -> None:
        """Deprecated: Use on_strategy instead.
        
        Register a callback for strategy event stream handling.
        """
        self.on_strategy(callback)

    def on_order(self, callback: Callable[[OrderPayload], None]) -> None:
        """Register a callback for order event notifications.

        EN:
            Attaches the handler that will process order payloads emitted
            by the listener subsystem. Events include submissions, fills,
            modifications, cancellations, and errors.

        KR:
            주문 이벤트 알림을 위한 콜백을 등록합니다. 제출, 체결, 정정,
            취소, 오류 등의 이벤트를 수신합니다.

        페이로드 구조:
            - event_type: 이벤트 유형 (order_submitted, order_filled, order_modified, order_cancelled, order_rejected, order_error)
            - order_type: 주문 유형 (매수/매도 구분)
            - message: 작업 내용
            - response: 실시간 데이터
            - error_code: 에러 코드 (에러 발생 시)
            - error_data: 에러 상세 데이터 (에러 발생 시)

        Args:
            callback (Callable[[OrderPayload], None]):
                EN: Consumer receiving order payload objects.
                KR: 주문 페이로드 객체를 받는 소비자 함수입니다.

        Returns:
            None:
                EN: Registration completes without returning a value.
                KR: 등록이 완료돼도 반환값은 없습니다.
        """
        pg_listener.set_order_handler(callback)

    def on_real_order_message(self, callback: Callable[[RealOrderPayload], None]) -> None:
        """Deprecated: Use on_order instead.
        
        Register a callback for real order event notifications.
        """
        self.on_order(callback)

    def on_performance_message(self, callback: Callable[[PerformancePayload], None]) -> None:
        """Register a callback for performance metric and system lifecycle notifications.

        EN:
            Attaches the handler that will process performance payloads emitted
            by the listener subsystem. Also receives system errors and shutdown events.

        KR:
            퍼포먼스 지표 및 시스템 라이프사이클 알림 수신 콜백 함수로, 리스너 서브시스템에서 
            발행하는 퍼포먼스 페이로드를 처리할 핸들러를 등록합니다.
            시스템 오류 및 종료 이벤트도 이 콜백으로 전달됩니다.

        페이로드 구조:
            - event_type: 이벤트 유형 (perf_snapshot, perf_exceeded, system_shutdown, system_error)
            - context: 컨텍스트 (예: "strategy:my_strategy_id", "system")
            - stats: 성능 통계
            - status: 상태 (선택)
            - details: 상세 정보 (선택, 에러 시 error_code, error_message 포함)

        Args:
            callback (Callable[[PerformancePayload], None]):
                EN: Consumer receiving performance payload objects.
                KR: 퍼포먼스 페이로드 객체를 받는 소비자 함수입니다.

        Returns:
            None:
                EN: Registration completes without returning a value.
                KR: 등록이 완료돼도 반환값은 없습니다.
        """
        pg_listener.set_performance_handler(callback)

    def on_error_message(self, callback: Callable[[ErrorPayload], None]) -> None:
        """Deprecated: 오류는 이제 도메인별 콜백(on_strategy, on_order, on_performance_message)으로 전달됩니다.
        
        이 메서드는 하위 호환성을 위해 유지되지만 아무 동작도 하지 않습니다.
        대신 on_strategy, on_order, on_performance_message 콜백에서 event_type 필드를 확인하여
        오류를 처리하세요:
        
        - 전략 오류: event_type이 'condition_error' 또는 'strategy_error'인 경우
        - 주문 오류: event_type이 'order_error' 또는 'order_rejected'인 경우  
        - 시스템 오류: event_type이 'system_error'인 경우

        기존 에러 코드들은 각 페이로드의 error_code 필드로 전달됩니다:
        - ``APPKEY_NOT_FOUND``: 인증 키 누락
        - ``CONDITION_EXECUTION_ERROR``: 조건 실행 실패
        - ``INVALID_CRON_EXPRESSION``: 잘못된 스케줄 표현식
        - ``LOGIN_ERROR``: 로그인 실패
        - ``ORDER_ERROR``: 주문 처리 중 오류
        - ``STRATEGY_EXECUTION_ERROR``: 전략 실행 실패
        - ``SYSTEM_ERROR``: 일반 시스템 오류
        - 등등...

        Args:
            callback (Callable[[ErrorPayload], None]):
                EN: Handler (ignored - this method does nothing).
                KR: 핸들러 (무시됨 - 이 메서드는 아무 동작도 하지 않습니다).

        Returns:
            None
        """
        # Deprecated: errors are now domain-specific
        pg_listener.set_error_handler(callback)
