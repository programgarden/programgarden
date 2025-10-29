"""
컴포지션(각 컴포넌트 주입) + 전체 오케스트레이션
"""

from datetime import datetime
from datetime import time as datetime_time, timedelta
import asyncio
from typing import List, Optional, Union
from zoneinfo import ZoneInfo

from croniter import croniter

from programgarden_core import (
    SystemType,
    StrategyType,
    OrderTimeType,
    SymbolInfoOverseasStock,
    SymbolInfoOverseasFutures,
    BaseOrderOverseasStock,
    BaseOrderOverseasFutures,
    strategy_logger,
    trade_logger,
    system_logger,
    condition_logger,
)
from programgarden_core import (
    OrderType,
    OrderStrategyType,
)
from programgarden_core.exceptions import (
    BasicException,
    InvalidCronExpressionException,
    StrategyExecutionException,
    SystemException,
)
from programgarden.pg_listener import pg_listener

from .plugin_resolver import PluginResolver
from .symbols_provider import SymbolProvider
from .condition_executor import ConditionExecutor
from .buysell_executor import BuySellExecutor


class SystemExecutor:
    def __init__(self):
        self.running = False
        self.tasks: list[asyncio.Task] = []

        # 컴포넌트 주입
        self.plugin_resolver = PluginResolver()
        self.symbol_provider = SymbolProvider()
        self.condition_executor = ConditionExecutor(self.plugin_resolver, self.symbol_provider)
        self.buy_sell_executor = BuySellExecutor(self.plugin_resolver)

    def _format_order_types(self, order_types: Union[List[OrderType], OrderType]) -> str:
        if isinstance(order_types, (list, tuple, set)):
            return ", ".join(str(ot) for ot in order_types)
        return str(order_types)

    async def _execute_trade(
        self,
        system: SystemType,
        symbols_snapshot: list[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]],
        trade: OrderStrategyType,
        order_id: str,
        order_types: List[OrderType],
    ):
        """
        Helper to execute a trade based on its kind.

        Args:
            system (SystemType): The trading system configuration.
            symbols_snapshot (list[SymbolInfo]): The list of symbols to trade.
            trade (OrderStrategyType): The trade order configuration.
            order_id (str): The unique identifier for the order.
            order_types (List[OrderType]): The types of orders to execute.
        """
        order_type_label = self._format_order_types(order_types)
        symbol_count = len(symbols_snapshot)

        if any(ot in ["new_buy", "new_sell"] for ot in order_types):
            trade_logger.info(
                f"🟢 {order_id}: {symbol_count}개 종목에 신규 주문({order_type_label}) 전송"
            )
            await self.buy_sell_executor.new_order_execute(
                system=system,
                symbols_from_strategy=symbols_snapshot,
                new_order=trade,
                order_id=order_id,
                order_types=order_types
            )
        elif any(ot in ["modify_buy", "modify_sell"] for ot in order_types):
            trade_logger.info(
                f"🟡 {order_id}: {symbol_count}개 종목에 정정 주문({order_type_label}) 전송"
            )
            await self.buy_sell_executor.modify_order_execute(
                system=system,
                symbols_from_strategy=symbols_snapshot,
                modify_order=trade,
                order_id=order_id,
            )
        elif any(ot in ["cancel_buy", "cancel_sell"] for ot in order_types):
            trade_logger.info(
                f"🔴 {order_id}: {symbol_count}개 종목에 취소 주문({order_type_label}) 전송"
            )
            await self.buy_sell_executor.cancel_order_execute(
                system=system,
                symbols_from_strategy=symbols_snapshot,
                cancel_order=trade,
                order_id=order_id,
            )
        else:
            trade_logger.warning(
                f"⚠️ {order_id}: 지원되지 않는 주문 유형({order_type_label})이라 실행을 건너뜁니다"
            )

    # Helper: parse order_time range object
    def _parse_order_time_range(self, order: Optional[OrderTimeType], fallback_tz: str):
        """
        Parse an order's `order_time` range config.

        Expected shape:
        {
          "start": "09:30:00",
          "end": "16:00:00",
          "days": ["mon","tue",...],  # optional, defaults to weekdays
          "timezone": "America/New_York", # optional
          "behavior": Union["defer", "skip"], # optional (default: defer)
          "max_delay_seconds": 86400  # optional
        }
        """
        ot = order or {}
        start_s: Optional[str] = ot.get("start")
        end_s: Optional[str] = ot.get("end")
        if not start_s or not end_s:
            return None

        try:
            start_parts = [int(x) for x in start_s.split(":")]
            end_parts = [int(x) for x in end_s.split(":")]
            start_tm = datetime_time(*start_parts)
            end_tm = datetime_time(*end_parts)
        except Exception:
            system_logger.error(f"order_time 시간 형식이 잘못되었습니다: start={start_s} end={end_s}")
            return None

        days_list = ot.get("days", ["mon", "tue", "wed", "thu", "fri"]) or ["mon", "tue", "wed", "thu", "fri"]
        days_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
        days_set = set()
        for d in days_list:
            v = days_map.get(d.lower())
            if v is not None:
                days_set.add(v)

        tz_name = ot.get("timezone", fallback_tz)
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            system_logger.warning(f"주문에 지정된 시간대 '{tz_name}'가 유효하지 않아 UTC로 대체합니다")
            tz = ZoneInfo("UTC")

        behavior = ot.get("behavior", "defer")
        max_delay = int(ot.get("max_delay_seconds", 86400))

        return {
            "start": start_tm,
            "end": end_tm,
            "days": days_set,
            "tz": tz,
            "behavior": behavior,
            "max_delay_seconds": max_delay,
        }

    def _is_dt_in_window(self, dt: datetime, start: datetime_time, end: datetime_time, days: set):
        """Return True if dt (timezone-aware) falls within the time window."""
        # Work with seconds-since-midnight to avoid tz-aware vs naive time comparisons
        weekday = dt.weekday()

        t_seconds = dt.hour * 3600 + dt.minute * 60 + dt.second
        start_seconds = start.hour * 3600 + start.minute * 60 + getattr(start, "second", 0)
        end_seconds = end.hour * 3600 + end.minute * 60 + getattr(end, "second", 0)

        # Non-empty days set restricts allowed weekdays
        if end_seconds > start_seconds:
            # Normal same-day window
            if days and weekday not in days:
                return False
            return start_seconds <= t_seconds < end_seconds

        # Overnight window (end <= start): e.g., start=22:30, end=02:00
        # Times on or after `start` belong to the same weekday as `dt`.
        if t_seconds >= start_seconds:
            if days and weekday not in days:
                return False
            return True

        # Times before `end` (early morning) belong to the previous day's window.
        prev_weekday = (weekday - 1) % 7
        if days and prev_weekday not in days:
            return False
        return t_seconds < end_seconds

    def _next_window_start(self, now: datetime, start: datetime_time, days: set):
        """Compute next datetime (timezone-aware) for the window start (can be today)."""
        for add_days in range(0, 8):
            candidate = now + timedelta(days=add_days)
            if days and candidate.weekday() not in days:
                continue
            # construct candidate datetime with start time
            start_dt = datetime(
                year=candidate.year,
                month=candidate.month,
                day=candidate.day,
                hour=start.hour,
                minute=start.minute,
                second=getattr(start, "second", 0),
                tzinfo=now.tzinfo,
            )
            if start_dt > now:
                return start_dt
        return None

    async def _process_trade_time_window(
        self,
        system: SystemType,
        trade: OrderStrategyType,
        symbols_snapshot: list[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]],
        strategy_order_id: str,
        order_types: OrderType,
    ) -> bool:
        """
        Shared helper to handle time-window parsing, immediate execution, skipping, or deferring

        Returns True when the caller should "continue" (i.e. immediate/skip/error paths),
        and False when the deferred path was used (so the caller may proceed to subsequent
        logic after the deferred execution completes).
        """

        order_type_label = self._format_order_types(order_types)
        order_time = trade.get("order_time", None)

        order_range: Optional[dict] = None
        if order_time:
            fallback_tz = order_time.get("timezone", "UTC")
            order_range = self._parse_order_time_range(order_time, fallback_tz)

        # no scheduling configured -> execute immediately
        if not order_range:
            await self._execute_trade(system, symbols_snapshot, trade, strategy_order_id, order_types)
            return True

        # inside window -> immediate
        now = datetime.now(order_range["tz"]) if order_range["tz"] else datetime.now()
        if self._is_dt_in_window(now, order_range["start"], order_range["end"], order_range["days"]):

            # inside window -> immediate
            await self._execute_trade(system, symbols_snapshot, trade, strategy_order_id, order_types)
            return True

        # outside window -> behavior
        behavior = order_range.get("behavior", "defer")
        if behavior == "skip":
            trade_logger.warning(
                f"주문 '{strategy_order_id}'이 시간 조건을 벗어나 동작=skip 설정에 따라 건너뜁니다 ({order_type_label})"
            )
            return False

        # defer: schedule at next window start (subject to max_delay_seconds)
        next_start = self._next_window_start(now, order_range["start"], order_range["days"])
        if not next_start:
            trade_logger.warning(
                f"주문 '{strategy_order_id}'에 대해 다음 실행 시간 창을 계산할 수 없어 건너뜁니다 ({order_type_label})"
            )
            return False

        # compute delay and check max_delay_seconds
        delay = (next_start - now).total_seconds()
        if delay > order_range.get("max_delay_seconds", 86400):
            trade_logger.warning(
                f"주문 '{strategy_order_id}'의 지연 시간 {delay}s가 허용치(max_delay_seconds)를 초과하여 건너뜁니다 ({order_type_label})"
            )
            return False

        async def _scheduled_exec(delay, symbols_snapshot, trade, order_id, when, tz):
            # wait until scheduled time
            await asyncio.sleep(delay)

            await self._execute_trade(system, symbols_snapshot, trade, order_id, order_types)

        trade_logger.info(
            f"⏳ {strategy_order_id}: {order_type_label} 주문을 {next_start.isoformat()} ({order_range['tz']}) 실행으로 예약했습니다"
        )
        await _scheduled_exec(delay, symbols_snapshot, trade, strategy_order_id, next_start, order_range["tz"])

        # returned after deferred execution; allow caller to continue with subsequent logic
        return True

    async def _run_once_execute(self, system: SystemType, strategy: StrategyType):
        """
        Run a single execution of the strategy within the system.
        """
        strategy_id = strategy.get("id", "<unknown>")
        strategy_logger.info(f"🚀 {strategy_id}: 전략 실행을 시작합니다")

        conditions = strategy.get("conditions", [])
        if not conditions:
            strategy_logger.warning(f"⚪️ {strategy_id}: 조건이 없어 주문을 건너뜁니다")
            return

        response_symbols = await self.condition_executor.execute_condition_list(system=system, strategy=strategy)
        async with self.condition_executor.state_lock:
            success = len(response_symbols) > 0

        if not success:
            strategy_logger.info(f"⚪️ {strategy_id}: 조건을 통과한 종목이 없어 주문을 건너뜁니다")
            return

        symbol_count = len(response_symbols)

        # 전략 계산 통과됐으면 매수/매도 진행
        orders = system.get("orders", [])
        strategy_order_id = strategy.get("order_id", None)

        matched_trade = False
        triggered_trades: list[str] = []
        for trade in orders:
            if trade.get("order_id") != strategy_order_id:
                continue

            matched_trade = True

            condition = trade.get("condition", None)
            if condition is None:
                continue

            if isinstance(condition, (BaseOrderOverseasStock, BaseOrderOverseasFutures)):
                condition_id = condition.id
                order_types = condition.order_types
            else:
                condition_id = condition.get("condition_id")
                order_types = await self.plugin_resolver.get_order_types(condition_id)

            if not condition_id:
                condition_logger.warning(f"주문 '{trade.get('order_id')}'에 condition_id가 없습니다.")
                continue

            if not order_types:
                condition_logger.warning(f"condition_id '{condition_id}'에 대한 주문 유형을 알 수 없어 건너뜁니다")
                continue

            symbols_snapshot = list(response_symbols)

            await self._process_trade_time_window(
                system=system,
                trade=trade,
                symbols_snapshot=symbols_snapshot,
                strategy_order_id=strategy_order_id,
                order_types=order_types,
            )
            triggered_trades.append(
                f"{trade.get('order_id')} ({self._format_order_types(order_types)})"
            )

        if matched_trade:
            trade_summary = ", ".join(triggered_trades) if triggered_trades else "없음"
            strategy_logger.info(
                f"✅ {strategy_id}: {symbol_count}개 종목 통과, 실행된 주문 -> {trade_summary}"
            )

    async def _run_with_strategy(self, strategy_id: str, strategy: StrategyType, system: SystemType):
        """
        Run a single strategy within the system.
        """

        run_once_on_start = bool(strategy.get("run_once_on_start", False))

        try:
            cron_expr = strategy.get("schedule", None)
            count = strategy.get("count", 9999999)
            tz_name = strategy.get("timezone", "UTC")

            if not cron_expr:
                strategy_logger.info(f"🕐 {strategy_id}: 스케줄이 없어 한 번만 실행합니다")
                try:
                    await self._run_once_execute(system=system, strategy=strategy)
                except BasicException as exc:
                    pg_listener.emit_exception(exc)
                    raise
                except Exception as exc:
                    strategy_logger.exception(
                        f"{strategy_id}: 단일 실행 중 예외 발생"
                    )
                    strategy_exc = StrategyExecutionException(
                        message=f"전략 '{strategy_id}' 실행 중 오류가 발생했습니다.",
                        data={"strategy_id": strategy_id, "details": str(exc)},
                    )
                    pg_listener.emit_exception(strategy_exc)
                    raise strategy_exc

                return

            tz = ZoneInfo(tz_name)
            tz_label = getattr(tz, "key", str(tz))
        except Exception:
            strategy_logger.warning(f"{strategy_id}: 시간대 '{tz_name}'가 유효하지 않아 UTC로 대체합니다")
            tz = ZoneInfo("UTC")
            tz_label = getattr(tz, "key", str(tz))

        if run_once_on_start:
            try:
                await self._run_once_execute(system=system, strategy=strategy)
            except BasicException as exc:
                pg_listener.emit_exception(exc)
                raise
            except Exception as exc:
                strategy_logger.exception(
                    f"{strategy_id}: 시작 즉시 실행 중 예외 발생"
                )
                strategy_exc = StrategyExecutionException(
                    message=f"전략 '{strategy_id}' 실행 중 오류가 발생했습니다.",
                    data={"strategy_id": strategy_id, "details": str(exc)},
                )
                pg_listener.emit_exception(strategy_exc)
                raise strategy_exc

        async def run_cron():
            try:
                valid = croniter.is_valid(cron_expr, second_at_beginning=True)
            except TypeError:
                valid = croniter.is_valid(cron_expr)

            try:
                if not valid:
                    strategy_logger.error(f"{strategy_id}: cron 표현식 '{cron_expr}'이 잘못되었습니다")
                    raise InvalidCronExpressionException(
                        message=f"Invalid cron expression: {cron_expr}",
                        data={"strategy_id": strategy_id},
                    )
            except InvalidCronExpressionException as exc:
                strategy_logger.error(f"{strategy_id}: cron 예외 발생 - {exc}")
                pg_listener.emit_exception(exc)
                raise

            cnt = 0
            itr = croniter(cron_expr, datetime.now(tz), second_at_beginning=True)
            while cnt < count and self.running:
                next_dt = itr.get_next(datetime)
                now = datetime.now(tz)
                delay = (next_dt - now).total_seconds()
                if delay < 0:
                    delay = 0

                strategy_logger.debug(
                    f"{strategy_id}: 다음 실행 #{cnt + 1}은 {next_dt.isoformat()} ({tz_label})"
                )
                await asyncio.sleep(delay)
                if not self.running:
                    break

                try:
                    await self._run_once_execute(system=system, strategy=strategy)
                except BasicException as exc:
                    pg_listener.emit_exception(exc)
                    raise
                except Exception as exc:
                    strategy_logger.exception(
                        f"{strategy_id}: 실행 중 예외 발생"
                    )
                    strategy_exc = StrategyExecutionException(
                        message=f"전략 '{strategy_id}' 실행 중 오류가 발생했습니다.",
                        data={"strategy_id": strategy_id, "details": str(exc)},
                    )
                    pg_listener.emit_exception(strategy_exc)
                    raise strategy_exc

                cnt += 1

            strategy_logger.info(f"⏹️ {strategy_id}: cron 실행이 종료되었습니다 (총 {cnt}회)")

        task = asyncio.create_task(run_cron())
        self.tasks.append(task)

        try:
            await task
        except asyncio.CancelledError:
            strategy_logger.debug(f"{strategy_id}: cron 태스크가 취소되었습니다")
            raise

    async def execute_system(self, system: SystemType):
        """
        Execute the trading system.
        """

        system_settings = system.get("settings", {}) or {}
        system_id = system_settings.get("system_id", system.get("id", "<unknown>"))
        strategies = system.get("strategies", [])
        self.running = True
        self.plugin_resolver.reset_error_tracking()

        system_logger.info(
            f"👋 {system_id}: {len(strategies)}개 전략 실행을 시작합니다"
        )

        try:
            real_order_task = asyncio.create_task(
                self.buy_sell_executor.real_order_executor.real_order_websockets(
                    system=system
                )
            )
            self.tasks.append(real_order_task)

            # 전략 계산
            concurrent_tasks = [self._run_with_strategy(strategy_id=strategy.get("id"), strategy=strategy, system=system) for strategy in strategies]

            if concurrent_tasks:
                results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
                for idx, result in enumerate(results):
                    if isinstance(result, asyncio.CancelledError):
                        system_logger.warning(
                            f"{system_id}: 전략 태스크 {idx + 1}이(가) 취소되었습니다"
                        )
                        continue
                    if isinstance(result, Exception):
                        strategy_meta = strategies[idx] if idx < len(strategies) else {}
                        strategy_key = strategy_meta.get("id", f"strategy_{idx + 1}")
                        system_logger.error(
                            f"{system_id}: 전략 '{strategy_key}' 태스크에서 예외 발생 -> {result}"
                        )
                        if getattr(result, "_pg_error_emitted", False):
                            continue
                        if isinstance(result, BasicException):
                            pg_listener.emit_exception(result)
                        else:
                            wrapped_exc = StrategyExecutionException(
                                message=f"전략 '{strategy_key}' 실행 중 오류가 발생했습니다.",
                                data={
                                    "strategy_id": strategy_key,
                                    "details": str(result),
                                },
                            )
                            pg_listener.emit_exception(wrapped_exc)
                system_logger.info(f"✅ {system_id}: 모든 전략 태스크가 완료되었습니다")
            else:
                system_logger.info(f"ℹ️ {system_id}: 실행할 전략이 구성되어 있지 않습니다")

        except BasicException as exc:
            system_logger.error(f"{system_id}: 실행 중 오류 발생 -> {exc}")
            pg_listener.emit_exception(exc)
            await self.stop()
            raise
        except Exception as exc:
            system_logger.exception(f"{system_id}: 실행 중 처리되지 않은 오류 발생")
            system_exc = SystemException(
                message=f"시스템 '{system_id}' 실행 중 처리되지 않은 오류가 발생했습니다.",
                code="SYSTEM_EXECUTION_ERROR",
                data={"system_id": system_id, "details": str(exc)},
            )
            pg_listener.emit_exception(system_exc)
            await self.stop()
            raise system_exc from exc
        finally:
            system_logger.info(f"🏁 {system_id}: 시스템 실행이 종료되었습니다")

    async def stop(self):
        self.running = False
        pending = sum(1 for task in self.tasks if not task.done())
        system_logger.info(f"🛑 중지 요청 수신, 진행 중인 태스크 {pending}개를 취소합니다")
        for task in self.tasks:
            if not task.done():
                task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
            system_logger.info("🧹 남은 태스크 취소를 완료했습니다")
        self.tasks.clear()
