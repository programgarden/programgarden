
import asyncio
import logging
import threading
from typing import Callable
from programgarden_core import pg_log, pg_log_disable, pg_logger
from programgarden_core.bases import SystemType
from programgarden_finance import LS
from programgarden_core import EnforceKoreanAliasMeta
from programgarden_core.exceptions import LoginException
from programgarden import SystemExecutor
from programgarden.pg_listener import StrategyPayload, RealOrderPayload, pg_listener
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

        tprint("""
Program Garden
    x
LS Securities
""", font="tarty1")

        if system:
            self._check_debug(system)

        try:
            exist_system_keys_error(system)
            asyncio.get_running_loop()

            if self._task is not None and not self._task.done():
                pg_logger.info("A task is already running; returning the existing task.")
                return self._task

            task = asyncio.create_task(self._execute(system))
            self._task = task

            return task

        except RuntimeError:
            return asyncio.run(self._execute(system))

        finally:
            pg_logger.error("The program has terminated.")
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
        """
        Execute the trading strategy.
        """
        try:
            securities = system.get("securities", {})
            company = securities.get("company", None)
            if company == "ls":
                ls = LS.get_instance()

                if not ls.is_logged_in():
                    login_result = await ls.async_login(
                        appkey=securities.get("appkey"),
                        appsecretkey=securities.get("appsecretkey")
                    )
                    if not login_result:
                        raise LoginException(
                            message="LS 증권 로그인에 실패했습니다. 로그인 정보를 확인하세요."
                        )

            await self.executor.execute_system(system)

            while self.executor.running:
                await asyncio.sleep(1)

        finally:
            self.on_strategies_message(
                {
                    "event": "system_stopped",
                    "message": "시스템이 종료되었습니다."
                }
            )
            await self.stop()
            # 실행 종료 후 태스크 핸들 초기화
            self._task = None

    async def stop(self):
        await self.executor.stop()
        pg_logger.debug("The program has been stopped.")

    def on_strategies_message(self, callback: Callable[[StrategyPayload], None]) -> None:
        """실시간 이벤트 수신 콜백 등록"""
        pg_listener.set_strategies_handler(callback)

    def on_real_order_message(self, callback: Callable[[RealOrderPayload], None]) -> None:
        """실시간 주문 이벤트 수신 콜백 등록"""
        pg_listener.set_real_order_handler(callback)
