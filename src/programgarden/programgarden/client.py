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
from typing import Callable
from programgarden_core import pg_log, pg_log_disable, system_logger, normalize_system_config
from programgarden_core.bases import SystemType
from programgarden_finance import LS
from programgarden_core import EnforceKoreanAliasMeta
from programgarden_core.exceptions import (
    BasicException,
    LoginException,
    NotExistCompanyException,
    SystemException,
    SystemInitializationException,
    SystemShutdownException,
)
from programgarden import SystemExecutor
from programgarden.pg_listener import (
    StrategyPayload,
    RealOrderPayload,
    ErrorPayload,
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

    def run(
        self,
        system: SystemType
    ):
        """Validate configuration and launch the trading system.

        EN:
            Normalizes the incoming system configuration, checks mandatory
            keys, sets debug logging, and either schedules asynchronous
            execution on an existing event loop or creates a fresh loop via
            `asyncio.run`.

        KR:
            시스템 구성을 정규화하고 필수 키를 검증하며, 디버그 로깅을 설정한 뒤
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
                self._check_debug(system_config)

            exist_system_keys_error(system_config)
        except BasicException as exc:
            pg_listener.emit_exception(exc)
            raise
        except Exception as exc:
            system_logger.exception("System configuration validation failed")
            init_exc = SystemInitializationException(
                message="시스템 설정 검증 중 알 수 없는 오류가 발생했습니다.",
                data={"details": str(exc)},
            )
            pg_listener.emit_exception(init_exc)
            raise init_exc

        try:
            asyncio.get_running_loop()

            if self._task is not None and not self._task.done():
                system_logger.info("A task is already running; returning the existing task.")
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

        system_logger.debug("The program has terminated.")

        shutdown_exc = SystemShutdownException()
        pg_listener.emit_exception(shutdown_exc)
        pg_listener.stop()

    def _check_debug(self, system: SystemType):
        """Apply debug logging preference from the system configuration.

        EN:
            Reads `settings.debug` and adjusts Programgarden logging levels,
            falling back to disabling logs when unspecified.

        KR:
            `settings.debug` 값을 참조하여 Programgarden 로깅 수준을 조정하며,
            지정되지 않은 경우 로깅을 비활성화합니다.

        Args:
            system (SystemType):
                EN: System definition containing the debug setting.
                KR: 디버그 설정을 포함하는 시스템 정의입니다.

        Returns:
            None:
                EN: Adjusts log configuration without a return value.
                KR: 로깅 구성을 조정할 뿐 반환값은 없습니다.
        """

        debug = system.get("settings", {}).get("debug", "").upper()
        if debug == "DEBUG":
            pg_log(logging.DEBUG)
        elif debug == "INFO":
            pg_log(logging.INFO)
        elif debug == "WARNING":
            pg_log(logging.WARNING)
        elif debug == "ERROR":
            pg_log(logging.ERROR)
        elif debug == "CRITICAL":
            pg_log(logging.CRITICAL)
        else:
            pg_log_disable()

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
        try:
            securities = system.get("securities", {})
            product = securities.get("product", None)
            company = securities.get("company", None)
            if company == "ls":
                ls = LS.get_instance()

                paper_trading = bool(securities.get("paper_trading", False))
                if product == "overseas_futures" and paper_trading:
                    system_logger.warning("해외선물 모의투자는 홍콩거래소(HKEX)만 지원됩니다.")

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

        except BasicException as exc:
            pg_listener.emit_exception(exc)
        except Exception as exc:
            system_logger.exception("Unexpected error during system execution")
            system_exc = SystemException(
                message="시스템 실행 중 처리되지 않은 오류가 발생했습니다.",
                code="SYSTEM_EXECUTION_ERROR",
                data={"details": str(exc)},
            )
            pg_listener.emit_exception(system_exc)

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

        await self.executor.stop()
        system_logger.debug("The program has been stopped.")

    def on_strategies_message(self, callback: Callable[[StrategyPayload], None]) -> None:
        """Register a callback for strategy event stream handling.

        EN:
            Subscribes the provided callable to receive strategy payloads as
            they arrive from the listener.

        KR:
            실시간 이벤트 수신 콜백 등록 함수로, 제공된 콜러블을 리스너에서 전달되는 전략 페이로드 수신에 등록합니다.

        Args:
            callback (Callable[[StrategyPayload], None]):
                EN: Function invoked with structured strategy payloads.
                KR: 구조화된 전략 페이로드를 인자로 받는 함수입니다.

        Returns:
            None:
                EN: Registration has no direct return value.
                KR: 등록 과정은 별도의 반환값을 제공하지 않습니다.
        """
        pg_listener.set_strategies_handler(callback)

    def on_real_order_message(self, callback: Callable[[RealOrderPayload], None]) -> None:
        """Register a callback for real order event notifications.

        EN:
            Attaches the handler that will process real order payloads emitted
            by the listener subsystem.

        KR:
            실시간 주문 이벤트 수신 콜백 함수로, 리스너 서브시스템에서 발행하는 실시간 주문 페이로드를 처리할 핸들러를
            등록합니다.

        Args:
            callback (Callable[[RealOrderPayload], None]):
                EN: Consumer receiving real order payload objects.
                KR: 실시간 주문 페이로드 객체를 받는 소비자 함수입니다.

        Returns:
            None:
                EN: Registration completes without returning a value.
                KR: 등록이 완료돼도 반환값은 없습니다.
        """
        pg_listener.set_real_order_handler(callback)

    def on_error_message(self, callback: Callable[[ErrorPayload], None]) -> None:
        """Register a callback for structured error notifications.

        전달되는 페이로드는 ``{"code": str, "message": str, "data": dict}`` 형태이며,
        사용 가능한 에러 코드는 다음과 같다:

        - ``APPKEY_NOT_FOUND``: 인증 키 누락
        - ``CONDITION_EXECUTION_ERROR``: 조건 실행 실패
        - ``INVALID_CRON_EXPRESSION``: 잘못된 스케줄 표현식
        - ``LOGIN_ERROR``: 로그인 실패
        - ``NOT_EXIST_COMPANY``: 지원하지 않는 증권사
        - ``NOT_EXIST_CONDITION``: 등록되지 않은 조건(플러그인)
        - ``NOT_EXIST_KEY``: 필수 키 부재
        - ``NOT_EXIST_SYSTEM``: 정의되지 않은 시스템
        - ``ORDER_ERROR``: 주문 처리 중 오류
        - ``ORDER_EXECUTION_ERROR``: 주문 실행/조회 실패
        - ``STRATEGY_EXECUTION_ERROR``: 전략 실행 실패
        - ``SYSTEM_ERROR``: 일반 시스템 오류
        - ``SYSTEM_EXECUTION_ERROR``: 실행 중 처리되지 않은 예외
        - ``SYSTEM_INITIALIZATION_ERROR``: 시스템 초기 검증 실패
        - ``SYSTEM_SHUTDOWN``: 정상 종료 알림
        - ``TOKEN_ERROR``: 토큰 발급 실패
        - ``TOKEN_NOT_FOUND``: 토큰 부재
        - ``TR_REQUEST_DATA_NOT_FOUND``: TR 요청 데이터 누락
        - ``UNKNOWN_ERROR``: 기타 알 수 없는 오류(기본값)

        외부 개발자는 해당 코드를 기준으로 장애 원인을 분류하고 ``data`` 필드에 포함된
        세부 정보를 활용하면 된다.

        Args:
            callback (Callable[[ErrorPayload], None]):
                EN: Handler invoked for each error payload.
                KR: 각 오류 페이로드에 대해 호출되는 핸들러입니다.

        Returns:
            None:
                EN: Registration finishes without a return value.
                KR: 등록 후 반환값은 없습니다.
        """
        pg_listener.set_error_handler(callback)
