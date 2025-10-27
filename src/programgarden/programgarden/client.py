
import asyncio
import logging
import threading
from typing import Callable
from programgarden_core import pg_log, pg_log_disable, pg_logger, normalize_system_config
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
from art import tprint


class Programgarden(metaclass=EnforceKoreanAliasMeta):
    """
    Programgarden DSL Client for running trading systems.
    """

    def __init__(self):

        # 내부 상태
        self._lock = threading.RLock()

        # lazy init: SystemExecutor는 실제로 필요할 때 생성한다.
        self._executor = None
        self._executor_lock = threading.RLock()

        # 비동기 실행 태스크 핸들 (이벤트 루프 내에서 중복 실행 방지용)
        self._task = None
        self._shutdown_notified = False

    @property
    def executor(self):
        """
        Lazily create and return the `SystemExecutor` instance.

        The executor is created on first access. Double-checked locking is
        used to avoid creating multiple executors in concurrent access
        scenarios.

        Returns:
            SystemExecutor: the executor instance used to run strategies.
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
        """
        Run the system - continuous execution
        This method starts the system and, if an event loop is already running,
        runs it as a background task. If no event loop is running, it uses
        asyncio.run() to execute the system.

        Args:
            system (SystemType): The system data object to run.
        """

        self._shutdown_notified = False
        self._print_banner()

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
            pg_logger.exception("System configuration validation failed")
            init_exc = SystemInitializationException(
                message="시스템 설정 검증 중 알 수 없는 오류가 발생했습니다.",
                data={"details": str(exc)},
            )
            pg_listener.emit_exception(init_exc)
            raise init_exc

        try:
            asyncio.get_running_loop()

            if self._task is not None and not self._task.done():
                pg_logger.info("A task is already running; returning the existing task.")
                return self._task

            task = asyncio.create_task(self._execute(system_config))
            self._task = task

            return task

        except RuntimeError:
            return asyncio.run(self._execute(system_config))

    def _handle_shutdown(self):
        if self._shutdown_notified:
            return
        self._shutdown_notified = True
        pg_logger.info("The program has terminated.")
        shutdown_exc = SystemShutdownException()
        pg_listener.emit_exception(shutdown_exc)
        pg_listener.stop()

    def _check_debug(self, system: SystemType):
        """Check debug mode setting and set the logging level"""

        debug = system.get("settings", {}).get("debug", None)
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
        try:
            securities = system.get("securities", {})
            company = securities.get("company", None)
            if company == "ls":
                ls = LS.get_instance()

                paper_trading = bool(securities.get("paper_trading", False))
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
            pg_logger.exception("Unexpected error during system execution")
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
        await self.executor.stop()
        pg_logger.debug("The program has been stopped.")

    def on_strategies_message(self, callback: Callable[[StrategyPayload], None]) -> None:
        """실시간 이벤트 수신 콜백 등록"""
        pg_listener.set_strategies_handler(callback)

    def on_real_order_message(self, callback: Callable[[RealOrderPayload], None]) -> None:
        """실시간 주문 이벤트 수신 콜백 등록"""
        pg_listener.set_real_order_handler(callback)

    def on_error_message(self, callback: Callable[[ErrorPayload], None]) -> None:
        """실시간 에러 이벤트 수신 콜백 등록.

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
        """
        pg_listener.set_error_handler(callback)

    def _print_banner(self):
        try:
            tprint("""
Program Garden
    x
LS Securities
    """, font="tarty1")
        except Exception as e:
            pg_logger.warning(f"Banner print failed: {e}")
