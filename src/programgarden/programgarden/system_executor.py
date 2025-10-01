"""
컴포지션(각 컴포넌트 주입) + 전체 오케스트레이션
"""

from datetime import datetime
from datetime import time as datetime_time, timedelta
import asyncio
from typing import List, Optional
from zoneinfo import ZoneInfo

from croniter import croniter

from programgarden_core import (
    SystemType, StrategyType, pg_logger,
    OrderTimeType, SymbolInfo
)
from programgarden_core import (
    OrderType,
    OrderStrategyType,
)

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

    async def _execute_trade(
        self,
        system: SystemType,
        symbols_snapshot: list[SymbolInfo],
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
        if any(ot in ["new_buy", "new_sell"] for ot in order_types):
            await self.buy_sell_executor.new_order_execute(
                system=system,
                symbols_from_strategy=symbols_snapshot,
                new_order=trade,
                order_id=order_id,
                order_types=order_types
            )
        elif any(ot in ["modify_buy", "modify_sell"] for ot in order_types):
            await self.buy_sell_executor.modify_order_execute(
                system=system,
                symbols_from_strategy=symbols_snapshot,
                modify_order=trade,
                order_id=order_id,
            )
        elif any(ot in ["cancel_buy", "cancel_sell"] for ot in order_types):
            await self.buy_sell_executor.cancel_order_execute(
                system=system,
                symbols_from_strategy=symbols_snapshot,
                cancel_order=trade,
                order_id=order_id,
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
          "behavior": "defer" | "skip", # optional (default: defer)
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
            pg_logger.error(f"Invalid time format in order_time: start={start_s} end={end_s}")
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
            pg_logger.warning(f"Invalid timezone '{tz_name}' for order; falling back to UTC")
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
        symbols_snapshot: list[SymbolInfo],
        strategy_order_id: str,
        order_types: OrderType,
    ) -> bool:
        """
        Shared helper to handle time-window parsing, immediate execution, skipping, or deferring

        Returns True when the caller should "continue" (i.e. immediate/skip/error paths),
        and False when the deferred path was used (so the caller may proceed to subsequent
        logic after the deferred execution completes).
        """

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
            pg_logger.warning(f"Order '{strategy_order_id}' skipped because outside time window and behavior=skip")
            return False

        # defer: schedule at next window start (subject to max_delay_seconds)
        next_start = self._next_window_start(now, order_range["start"], order_range["days"])
        if not next_start:
            pg_logger.warning(f"Could not compute next window start for order '{strategy_order_id}'")
            return False

        # compute delay and check max_delay_seconds
        delay = (next_start - now).total_seconds()
        if delay > order_range.get("max_delay_seconds", 86400):
            pg_logger.warning(f"Order '{strategy_order_id}' deferred delay {delay}s exceeds max_delay_seconds; skipping")
            return False

        async def _scheduled_exec(delay, symbols_snapshot, trade, order_id, when, tz):
            # wait until scheduled time
            await asyncio.sleep(delay)

            await self._execute_trade(system, symbols_snapshot, trade, order_id, order_types)

        pg_logger.info(f"Deferring and blocking until {order_types} order '{strategy_order_id}' executes at {next_start.isoformat()} ({order_range['tz']})")
        await _scheduled_exec(delay, symbols_snapshot, trade, strategy_order_id, next_start, order_range["tz"])

        # returned after deferred execution; allow caller to continue with subsequent logic
        return True

    async def _run_once_execute(self, system: SystemType, strategy: StrategyType):
        """
        Run a single execution of the strategy within the system.
        """
        print(f"===== Running strategy: {strategy.get('id')} =====")
        response_symbols = await self.condition_executor.execute_condition_list(system=system, strategy=strategy)
        async with self.condition_executor.state_lock:
            success = len(response_symbols) > 0

        if not success:
            return

        # 전략 계산 통과됐으면 매수/매도 진행
        orders = system.get("orders", [])
        strategy_order_id = strategy.get("order_id", None)

        for trade in orders:
            if trade.get("order_id") != strategy_order_id:
                continue

            condition_id = trade.get("condition", {}).get("condition_id", None)
            if not condition_id:
                pg_logger.warning(f"Order '{trade.get('order_id')}' missing condition_id, skipping trade")
                continue

            order_types = await self.plugin_resolver.get_order_types(condition_id)
            if not order_types:
                pg_logger.warning(f"Unknown order_types for condition_id: {condition_id}, skipping trade")
                continue

            symbols_snapshot = list(response_symbols)
            await self._process_trade_time_window(
                system=system,
                trade=trade,
                symbols_snapshot=symbols_snapshot,
                strategy_order_id=strategy_order_id,
                order_types=order_types,
            )

    async def _run_with_strategy(self, strategy_id: str, strategy: StrategyType, system: SystemType):
        """
        Run a single strategy within the system.
        """

        try:
            cron_expr = strategy.get("schedule", None)
            count = strategy.get("count", 9999999)

            if not cron_expr:
                pg_logger.debug(f"Running strategy '{strategy_id}' once (no schedule)")
                await self._run_once_execute(system=system, strategy=strategy)
                return

            tz_name = strategy.get("timezone", "UTC")
            tz = ZoneInfo(tz_name)
        except Exception:
            pg_logger.warning(f"Invalid timezone '{tz_name}', falling back to UTC.")
            tz = ZoneInfo("UTC")

        async def run_cron():
            try:
                valid = croniter.is_valid(cron_expr, second_at_beginning=True)
            except TypeError:
                valid = croniter.is_valid(cron_expr)

            if not valid:
                raise ValueError(f"Invalid cron expression: {cron_expr}")

            cnt = 0
            itr = croniter(cron_expr, datetime.now(tz), second_at_beginning=True)
            while cnt < count and self.running:
                next_dt = itr.get_next(datetime)
                now = datetime.now(tz)
                delay = (next_dt - now).total_seconds()
                if delay < 0:
                    delay = 0

                await asyncio.sleep(delay)
                if not self.running:
                    break

                await self._run_once_execute(system=system, strategy=strategy)

                cnt += 1

        task = asyncio.create_task(run_cron())
        self.tasks.append(task)

    async def execute_system(self, system: SystemType):
        """
        Execute the trading system.
        """

        self.running = True
        try:
            asyncio.create_task(
                self.buy_sell_executor.real_order_executor.real_order_websockets(
                    system=system
                )
            )

            strategies = system.get("strategies", [])

            # 전략 계산
            concurrent_tasks = [self._run_with_strategy(strategy_id=strategy.get("id"), strategy=strategy, system=system) for strategy in strategies]

            if concurrent_tasks:
                await asyncio.gather(*concurrent_tasks, return_exceptions=True)

        except Exception as e:
            pg_logger.error(f"Error executing system: {e}")
            await self.stop()
            raise

    async def stop(self):
        self.running = False
        for task in self.tasks:
            if not task.done():
                task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
