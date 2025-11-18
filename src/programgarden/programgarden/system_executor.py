"""Programgarden system orchestration layer.

EN:
    Centralizes dependency composition and time-aware execution for trading
    systems. The module coordinates condition evaluation, order routing,
    and websocket listeners while enforcing scheduling constraints per
    strategy. It also ensures that cron-based strategies, immediate
    executions, and deferred windows run under unified error reporting via
    :mod:`programgarden.pg_listener`.

KR:
    트레이딩 시스템의 컴포넌트 주입과 시간 기반 실행을 총괄합니다. 전략별
    스케줄 제약을 준수하면서 조건 평가, 주문 라우팅, 웹소켓 리스너를
    조율하고 :mod:`programgarden.pg_listener`를 통해 오류를 통합 보고합니다.
    크론 기반 전략, 즉시 실행, 지연 실행을 일관된 파이프라인에서 처리합니다.
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
    """Coordinate strategy scheduling, condition resolution, and order flows.

    EN:
        Provides the high-level engine that wires together condition evaluation,
        symbol lookups, and order execution. The executor tracks running tasks,
        handles cron scheduling, evaluates order-time windows, and streams
        exceptions to :mod:`programgarden.pg_listener` so host applications can
        react gracefully.

    KR:
        조건 평가, 종목 조회, 주문 실행을 하나로 묶는 상위 엔진입니다. 실행 중인
        태스크를 추적하고, 크론 스케줄을 관리하며, 주문 시간대를 검증하여
        :mod:`programgarden.pg_listener`로 예외를 전달하므로 호스트 애플리케이션이
        안정적으로 대응할 수 있습니다.

    Attributes:
        running (bool):
            EN: Indicates whether the executor loop is active.
            KR: 실행 루프가 활성 상태인지 나타냅니다.
        tasks (list[asyncio.Task]):
            EN: Collection of background tasks (cron loops, websockets, etc.).
            KR: 크론 루프, 웹소켓 등 백그라운드 태스크를 모은 리스트입니다.
        plugin_resolver (PluginResolver):
            EN: Resolves condition or order plugin identifiers to implementations.
            KR: 조건/주문 플러그인 식별자를 실제 구현으로 해석합니다.
        symbol_provider (SymbolProvider):
            EN: Supplies strategy-specific symbol universes.
            KR: 전략별 종목 집합을 제공합니다.
        condition_executor (ConditionExecutor):
            EN: Executes condition trees and returns filtered symbols.
            KR: 조건 트리를 실행해 필터링된 종목을 반환합니다.
        buy_sell_executor (BuySellExecutor):
            EN: Handles buy/sell order submissions, modifications, and cancellations.
            KR: 신규/정정/취소 주문을 처리합니다.
    """

    def __init__(self):
        self.running = False
        self.tasks: list[asyncio.Task] = []

        # EN: Instantiate core collaborators in deterministic order.
        # KR: 핵심 협력 객체를 결정된 순서로 초기화합니다.
        self.plugin_resolver = PluginResolver()
        self.symbol_provider = SymbolProvider()
        self.condition_executor = ConditionExecutor(self.plugin_resolver, self.symbol_provider)
        self.buy_sell_executor = BuySellExecutor(self.plugin_resolver)

    def _format_order_types(self, order_types: Union[List[OrderType], OrderType]) -> str:
        """Return a comma-separated label for heterogeneous order type inputs.

        EN:
            Accepts a single order type or an iterable collection and normalizes
            the representation for logging or telemetry. Non-iterable inputs are
            coerced to ``str`` directly.

        KR:
            단일 주문 유형이나 이터러블 컬렉션을 받아 로깅 및 텔레메트리에 사용할
            문자열로 통일합니다. 이터러블이 아닌 입력은 ``str``로 즉시 변환합니다.

        Args:
            order_types (Union[List[OrderType], OrderType]):
                EN: Raw order type value(s) from configuration or plugins.
                KR: 설정 또는 플러그인에서 온 원시 주문 유형 값입니다.

        Returns:
            str: EN: Comma-joined text for multi-value inputs; KR: 여러 값을 쉼표로
            이어붙인 문자열을 반환합니다.
        """
        if isinstance(order_types, (list, tuple, set)):
            return ", ".join(str(ot) for ot in order_types)
        return str(order_types)

    async def _execute_trade(
        self,
        system: SystemType,
        res_symbols_from_conditions: list[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]],
        trade: OrderStrategyType,
        order_id: str,
        order_types: List[OrderType],
    ):
        """Dispatch order execution based on requested order types.

        EN:
            Selects the appropriate execution branch (new, modify, cancel) for the
            supplied ``order_types`` and hands the symbol snapshot to
            :class:`BuySellExecutor`. Unsupported types are logged and skipped.

        KR:
            전달된 ``order_types``에 따라 신규/정정/취소 실행 경로를 선택하고 종목
            스냅샷을 :class:`BuySellExecutor`에 위임합니다. 지원되지 않는 유형은
            경고 로그 후 건너뜁니다.

        Args:
            system (SystemType):
                EN: Full system configuration containing accounts and orders.
                KR: 계좌와 주문이 포함된 전체 시스템 구성입니다.
            res_symbols_from_conditions (list[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]):
                EN: Symbols that passed condition evaluation.
                KR: 조건 평가를 통과한 종목 목록입니다.
            trade (OrderStrategyType):
                EN: Order strategy metadata dict.
                KR: 주문 전략 메타데이터 딕셔너리입니다.
            order_id (str):
                EN: Identifier shared with strategy definition.
                KR: 전략 정의와 연동되는 식별자입니다.
            order_types (List[OrderType]):
                EN: Declarative order type(s) resolved from configuration.
                KR: 설정으로부터 해석된 선언적 주문 유형입니다.
        """
        order_type_label = self._format_order_types(order_types)
        symbol_count = len(res_symbols_from_conditions)

        if any(ot in ["new_buy", "new_sell"] for ot in order_types):
            trade_logger.info(
                f"주문 전략 {order_id}의 {symbol_count}개 종목 신규 주문을 위한 분석에 들어갑니다."
            )
            await self.buy_sell_executor.new_order_execute(
                system=system,
                res_symbols_from_conditions=res_symbols_from_conditions,
                new_order=trade,
                order_id=order_id,
                order_types=order_types
            )
        elif any(ot in ["modify_buy", "modify_sell"] for ot in order_types):
            await self.buy_sell_executor.modify_order_execute(
                system=system,
                symbols_from_strategy=res_symbols_from_conditions,
                modify_order=trade,
                order_id=order_id,
            )
        elif any(ot in ["cancel_buy", "cancel_sell"] for ot in order_types):
            trade_logger.info(
                f"주문 전략 {order_id}의 {symbol_count}개 종목에 취소 주문 요청합니다."
            )
            await self.buy_sell_executor.cancel_order_execute(
                system=system,
                symbols_from_strategy=res_symbols_from_conditions,
                cancel_order=trade,
                order_id=order_id,
            )
        else:
            trade_logger.warning(
                f"주문 전략 {order_id}에서 지원되지 않는 주문 유형({order_type_label})이라 실행을 건너뜁니다"
            )

    def _parse_order_time_range(self, order: Optional[OrderTimeType], fallback_tz: str):
        """Normalize the ``order_time`` configuration into a runtime schedule.

        EN:
            Validates the provided time strings, resolves the timezone, and builds
            a dictionary containing parsed ``datetime.time`` objects, allowed
            weekdays, and defer/skip behaviors. Invalid inputs fall back to safe
            defaults (UTC timezone, weekday set).

        KR:
            지정된 시간 문자열을 검증하고 시간대를 해석한 뒤, ``datetime.time`` 객체,
            허용 요일, 지연/건너뛰기 행동을 담은 사전을 생성합니다. 잘못된 입력은
            안전한 기본값(UTC 시간대, 주중 요일)으로 대체됩니다.

        Args:
            order (Optional[OrderTimeType]):
                EN: Optional scheduling dictionary from order configuration.
                KR: 주문 설정에 포함된 선택적 스케줄링 딕셔너리입니다.
            fallback_tz (str):
                EN: Timezone used when the order payload omits ``timezone``.
                KR: ``timezone``이 비어 있을 때 사용할 기본 시간대입니다.

        Returns:
            Optional[dict]:
                EN: Parsed schedule metadata or ``None`` when configuration is invalid.
                KR: 해석된 스케줄 메타데이터 또는 설정이 유효하지 않을 경우 ``None``을
                반환합니다.

        Example:
            EN: ``{"start": "09:30:00", "end": "16:00:00", "days": ["mon"], ...}``
            KR: ``{"start": "09:30:00", "end": "16:00:00", "days": ["mon"], ...}``
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
        """Determine whether a timestamp lands inside the configured window.

        EN:
            Compares a timezone-aware ``datetime`` against start/end boundaries,
            handling both same-day and overnight windows. Weekday restrictions are
            enforced when provided.

        KR:
            시간대 정보가 포함된 ``datetime``이 시작/종료 경계를 충족하는지 평가하며,
            같은 날과 밤 사이 창 모두를 처리합니다. 요일 제한이 지정되면 이를
            적용합니다.

        Args:
            dt (datetime):
                EN: Current timestamp in the target timezone.
                KR: 대상 시간대의 현재 시각입니다.
            start (datetime_time):
                EN: Window start time-of-day.
                KR: 창의 시작 시각입니다.
            end (datetime_time):
                EN: Window end time-of-day.
                KR: 창의 종료 시각입니다.
            days (set):
                EN: Optional set of allowed weekdays represented as integers.
                KR: 허용 요일을 정수로 표현한 선택적 집합입니다.

        Returns:
            bool: EN: ``True`` when ``dt`` lies within the window; KR: ``dt``가 창에
            포함되면 ``True``를 반환합니다.
        """
        # EN: Work with seconds-since-midnight to avoid naive vs aware comparisons.
        # KR: tz 정보 차이로 인한 비교 문제를 피하기 위해 초 단위로 환산합니다.
        weekday = dt.weekday()

        t_seconds = dt.hour * 3600 + dt.minute * 60 + dt.second
        start_seconds = start.hour * 3600 + start.minute * 60 + getattr(start, "second", 0)
        end_seconds = end.hour * 3600 + end.minute * 60 + getattr(end, "second", 0)

        # EN: When days are specified, reject timestamps outside the allowed weekdays.
        # KR: 요일이 지정된 경우 허용되지 않은 요일의 시간은 배제합니다.
        if end_seconds > start_seconds:
            # Normal same-day window
            if days and weekday not in days:
                return False
            return start_seconds <= t_seconds < end_seconds

        # EN: Overnight windows treat post-start times as same-day occurrences.
        # KR: 야간 창에서는 시작 이후 시각을 같은 날짜로 간주합니다.
        if t_seconds >= start_seconds:
            if days and weekday not in days:
                return False
            return True

        # EN: Early-morning timestamps belong to the previous day's window.
        # KR: 새벽 시간은 전날 창에 속합니다.
        prev_weekday = (weekday - 1) % 7
        if days and prev_weekday not in days:
            return False
        return t_seconds < end_seconds

    def _next_window_start(self, now: datetime, start: datetime_time, days: set):
        """Compute the next valid start datetime for a window (including today).

        EN:
            Iterates up to one week ahead to find the next date that satisfies the
            weekday constraint, then merges the ``start`` time-of-day.

        KR:
            최대 1주일 범위에서 요일 조건을 충족하는 다음 날짜를 찾고 ``start`` 시각을
            결합합니다.

        Args:
            now (datetime):
                EN: Current timestamp with timezone info.
                KR: 시간대 정보가 포함된 현재 시각입니다.
            start (datetime_time):
                EN: Desired time-of-day for the window to open.
                KR: 창이 열릴 목표 시각입니다.
            days (set):
                EN: Optional allowed weekdays as integers.
                KR: 허용 요일을 정수로 표현한 선택적 집합입니다.

        Returns:
            Optional[datetime]:
                EN: Next start timestamp or ``None`` when none is found within the
                search horizon.
                KR: 탐색 범위에서 찾지 못하면 ``None``을 반환합니다.
        """
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
        res_symbols_from_conditions: list[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]],
        strategy_order_id: str,
        order_types: OrderType,
    ) -> bool:
        """Evaluate order-time constraints before executing an order strategy.

        EN:
            Parses the ``order_time`` specification, executes immediately when the
            window is open, skips when behavior is ``skip``, or defers execution to
            the next eligible window while respecting ``max_delay_seconds``.

        KR:
            ``order_time`` 설정을 해석해 창이 열려 있으면 즉시 실행하고, 행동이
            ``skip``이면 건너뛰며, ``max_delay_seconds`` 제한 범위에서 다음 창으로
            실행을 지연시킵니다.

        Args:
            system (SystemType):
                EN: System configuration for downstream order execution.
                KR: 이후 주문 실행에 필요한 시스템 구성입니다.
            trade (OrderStrategyType):
                EN: Strategy order payload containing ``order_time`` metadata.
                KR: ``order_time`` 메타데이터가 들어 있는 전략 주문 페이로드입니다.
            res_symbols_from_conditions (list[Union[SymbolInfoOverseasStock, SymbolInfoOverseasFutures]]):
                EN: Symbols eligible for trading based on condition results.
                KR: 조건 결과로 거래 대상이 된 종목 목록입니다.
            strategy_order_id (str):
                EN: Identifier tying the strategy to a specific order block.
                KR: 전략과 특정 주문 블록을 연결하는 식별자입니다.
            order_types (OrderType):
                EN: Order type or tuple derived from plugin/runtime resolution.
                KR: 플러그인/런타임 해석으로 얻은 주문 유형입니다.

        Returns:
            bool:
                EN: ``True`` when execution occurred immediately or after a defer;
                ``False`` if scheduling prevented the order (skip/invalid window).
                KR: 즉시 또는 지연 실행이 완료되면 ``True``를, 스케줄 조건으로 인해
                실행이 이루어지지 않은 경우 ``False``를 반환합니다.
        """

        order_type_label = self._format_order_types(order_types)
        order_time = trade.get("order_time", None)

        order_range: Optional[dict] = None
        if order_time:
            fallback_tz = order_time.get("timezone", "UTC")
            order_range = self._parse_order_time_range(order_time, fallback_tz)

        # no scheduling configured -> execute immediately
        if not order_range:
            await self._execute_trade(system, res_symbols_from_conditions, trade, strategy_order_id, order_types)
            return True

        # inside window -> immediate
        now = datetime.now(order_range["tz"]) if order_range["tz"] else datetime.now()
        if self._is_dt_in_window(now, order_range["start"], order_range["end"], order_range["days"]):

            # inside window -> immediate
            await self._execute_trade(system, res_symbols_from_conditions, trade, strategy_order_id, order_types)
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

        async def _scheduled_exec(delay, res_symbols_from_conditions, trade, order_id, when, tz):
            # wait until scheduled time
            await asyncio.sleep(delay)

            await self._execute_trade(system, res_symbols_from_conditions, trade, order_id, order_types)

        trade_logger.info(
            f"⏳ {strategy_order_id}: {order_type_label} 주문을 {next_start.isoformat()} ({order_range['tz']}) 실행으로 예약했습니다"
        )
        await _scheduled_exec(delay, res_symbols_from_conditions, trade, strategy_order_id, next_start, order_range["tz"])

        # returned after deferred execution; allow caller to continue with subsequent logic
        return True

    async def _run_once_execute(
            self,
            system: SystemType,
            strategy: StrategyType,
            cnt: int = 0
    ):
        """Run the strategy once, applying condition filters and order flows.

        EN:
            Evaluates all conditions for the provided strategy, gathers eligible
            symbols, and matches them against configured orders whose ``order_id``
            aligns with the strategy. Each qualifying order then passes through the
            time-window gatekeeper before execution.

        KR:
            주어진 전략의 모든 조건을 평가해 거래 가능한 종목을 수집한 뒤, 전략과
            ``order_id``가 일치하는 주문을 찾아 시간 창 검증을 거쳐 실행합니다.

        Args:
            system (SystemType):
                EN: System definition containing strategies and order blocks.
                KR: 전략과 주문 블록을 포함한 시스템 정의입니다.
            strategy (StrategyType):
                EN: Strategy metadata currently under execution.
                KR: 실행 중인 전략 메타데이터입니다.
            cnt (int):
                EN: Execution index for logging (0 for ad-hoc runs).
                KR: 로깅용 실행 인덱스(임의 실행 시 0).
        """
        strategy_id = strategy.get("id", "<unknown>")
        strategy_logger.info(f"\n\n\n🚀🚀🚀 전략 {strategy_id}의 {cnt}번째 실행을 시작합니다 🚀🚀🚀\n\n")

        # conditions = strategy.get("conditions", [])
        # if not conditions:
        #     strategy_logger.warning(f"⚪️ {strategy_id}: 조건이 없어 주문을 건너뜁니다")
        #     return

        # 조건 계산 결과값 종목들 반환
        # 해외선물은 결과에 position_side가 포함되어 있는데, 이는 duplication 중복 주문 방지에 사용된다.
        res_symbols_from_conditions = await self.condition_executor.execute_condition_list(system=system, strategy=strategy)
        async with self.condition_executor.state_lock:
            success = len(res_symbols_from_conditions) > 0

        if not success:
            strategy_logger.info(f"전략 {strategy_id}을 통과한 종목이 없어 주문을 건너뜁니다")
            return

        # 전략 계산 통과됐으면 매수/매도 진행
        orders = system.get("orders", [])
        strategy_order_id = strategy.get("order_id", None)

        for trade in orders:
            if trade.get("order_id") != strategy_order_id:
                continue

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

            m_res_symbols_from_conditions = list(res_symbols_from_conditions)

            await self._process_trade_time_window(
                system=system,
                trade=trade,
                res_symbols_from_conditions=m_res_symbols_from_conditions,
                strategy_order_id=strategy_order_id,
                order_types=order_types,
            )

    async def _run_with_strategy(self, strategy_id: str, strategy: StrategyType, system: SystemType):
        """Launch cron-driven execution for a single strategy.

        EN:
            Resolves the strategy's cron expression, timezone, and iteration count.
            Supports optional immediate execution (`run_once_on_start`) and routes
            runtime errors through :mod:`programgarden.pg_listener` with contextual
            payloads.

        KR:
            전략의 크론 표현식, 시간대, 반복 횟수를 해석하고 `run_once_on_start`
            옵션이 설정되면 즉시 한 번 실행합니다. 실행 중 발생하는 오류는 컨텍스트와
            함께 :mod:`programgarden.pg_listener`로 전달됩니다.

        Args:
            strategy_id (str):
                EN: Identifier from the strategy payload.
                KR: 전략 페이로드의 식별자입니다.
            strategy (StrategyType):
                EN: Complete strategy configuration.
                KR: 전체 전략 구성입니다.
            system (SystemType):
                EN: Full system configuration used during execution.
                KR: 실행에 사용되는 전체 시스템 구성입니다.
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
                    f"전략 {strategy_id}의 다음 {cnt + 1}번째의 실행 시간은 {next_dt.isoformat()} ({tz_label})입니다."
                )

                await asyncio.sleep(delay)
                if not self.running:
                    break

                try:
                    await self._run_once_execute(
                        system=system,
                        strategy=strategy,
                        cnt=cnt+1
                    )
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
            strategy_logger.debug(f"전략 {strategy_id}의 스케줄이 강제 취소되었습니다.")
            raise

    async def execute_system(self, system: SystemType):
        """Start all background services and strategy schedules for a system.

        EN:
            Bootstraps websocket listeners, resets resolver state, and launches
            strategy tasks concurrently. Failures are captured, wrapped in
            :class:`SystemException` when necessary, and emitted via listener hooks.

        KR:
            웹소켓 리스너를 시작하고 리졸버 상태를 초기화하며 전략 태스크를 병렬로
            실행합니다. 실패 시 필요에 따라 :class:`SystemException`으로 감싸 리스너에
            전달합니다.

        Args:
            system (SystemType):
                EN: System payload defining strategies, orders, and settings.
                KR: 전략, 주문, 설정이 포함된 시스템 페이로드입니다.
        """

        system_settings = system.get("settings", {}) or {}
        system_id = system_settings.get("system_id", system.get("id", "<unknown>"))
        strategies = system.get("strategies", [])
        self.running = True
        self.plugin_resolver.reset_error_tracking()

        system_logger.info(
            f"👋 시스템 {system_id}에서 {len(strategies)}개 전략 실행을 시작합니다"
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
            system_logger.debug(f"🏁 자동화매매 {system_id}의 실행이 종료되었습니다")

    async def stop(self):
        """Cancel outstanding tasks and reset the executor state.

        EN:
            Signals all running tasks to stop, awaits their completion, and clears
            internal bookkeeping so the executor can be re-used safely.

        KR:
            실행 중인 태스크에 중지 신호를 보내고 완료를 기다린 뒤 내부 상태를
            초기화하여 실행기를 안전하게 재사용할 수 있도록 합니다.
        """
        self.running = False
        pending = sum(1 for task in self.tasks if not task.done())
        system_logger.debug(f"🛑 진행 중인 작업 {pending}을 중지 요청으로 강제 취소합니다")
        for task in self.tasks:
            if not task.done():
                task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

        # EN: Ensures no dangling tasks remain when the executor halts.
        # KR: 실행기가 중지될 때 미완료 태스크가 남지 않도록 정리합니다.
