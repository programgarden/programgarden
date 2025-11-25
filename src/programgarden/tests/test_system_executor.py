from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from zoneinfo import ZoneInfo

from programgarden.system_executor import SystemExecutor
from programgarden import system_executor as system_executor_module
from programgarden_core.exceptions import PerformanceExceededException


class StubPluginResolver:
    def __init__(self) -> None:
        self.requested_ids: List[str] = []
        self.reset_called = False

    async def get_order_types(self, condition_id: str) -> List[str]:
        self.requested_ids.append(condition_id)
        return ["new_buy"]

    def reset_error_tracking(self) -> None:
        self.reset_called = True


class StubConditionExecutor:
    def __init__(self) -> None:
        self.calls: List[str] = []
        self.state_lock = asyncio.Lock()

    async def execute_condition_list(self, system: Dict[str, Any], strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.calls.append(strategy["id"])
        return [
            {
                "symbol": "ADZ25",
                "exchcd": "CME",
                "product_type": "overseas_futures",
            }
        ]


class StubBuySellExecutor:
    def __init__(self) -> None:
        self.new_order_calls: List[Dict[str, Any]] = []
        self.mode_changes: List[str] = []
        self.current_mode = "live"

        async def _real_order_websockets(*, system: Dict[str, Any]) -> None:
            self.real_order_system = system

        self.real_order_executor = SimpleNamespace(real_order_websockets=_real_order_websockets)

    def configure_execution_mode(self, mode: str) -> None:
        self.mode_changes.append(mode)
        self.current_mode = mode

    async def new_order_execute(
        self,
        *,
        system: Dict[str, Any],
        res_symbols_from_conditions: List[Dict[str, Any]],
        new_order: Dict[str, Any],
        order_id: str,
        order_types: List[str],
    ) -> None:
        self.new_order_calls.append(
            {
                "system_id": system["settings"]["system_id"],
                "order_id": order_id,
                "symbols": res_symbols_from_conditions,
                "order_types": order_types,
                "new_order": new_order,
            }
        )

    async def modify_order_execute(self, **_kwargs: Any) -> None:
        return None

    async def cancel_order_execute(self, **_kwargs: Any) -> None:
        return None


@pytest.mark.asyncio
async def test_execute_system_triggers_new_buy_flow() -> None:
    executor = SystemExecutor()
    executor.plugin_resolver = StubPluginResolver()
    executor.condition_executor = StubConditionExecutor()
    executor.buy_sell_executor = StubBuySellExecutor()

    system = {
        "settings": {"system_id": "system-1"},
        "securities": {
            "company": "ls",
            "product": "overseas_futures",
            "appkey": "key",
            "appsecretkey": "secret",
            "paper_trading": True,
        },
        "strategies": [
            {
                "id": "strategy-1",
                "logic": "and",
                "conditions": [{"condition_id": "dummy"}],
                "order_id": "order-1",
            }
        ],
        "orders": [
            {
                "order_id": "order-1",
                "condition": {"condition_id": "OrderPlugin"},
            }
        ],
    }

    await executor.execute_system(system)

    assert executor.plugin_resolver.reset_called is True
    assert executor.plugin_resolver.requested_ids == ["OrderPlugin"]
    assert executor.condition_executor.calls == ["strategy-1"]

    assert executor.buy_sell_executor.new_order_calls
    recorded = executor.buy_sell_executor.new_order_calls[0]
    assert recorded["order_id"] == "order-1"
    assert recorded["symbols"][0]["symbol"] == "ADZ25"
    assert recorded["order_types"] == ["new_buy"]

    await executor.stop()


@pytest.mark.asyncio
async def test_run_with_strategy_schedule_respects_cron(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = SystemExecutor()
    executor.running = True

    run_calls: List[str] = []

    async def fake_run_once(system: Dict[str, Any], strategy: Dict[str, Any]) -> None:
        run_calls.append(strategy["id"])

    monkeypatch.setattr(executor, "_run_once_execute", fake_run_once)

    now = datetime.now(ZoneInfo("UTC"))

    class FakeCroniterInstance:
        def __init__(self) -> None:
            self.current = now

        def get_next(self, _dt_type: Any) -> datetime:
            self.current = self.current + timedelta(seconds=1)
            return self.current

    class FakeCroniter:
        def __call__(self, *args: Any, **_kwargs: Any) -> FakeCroniterInstance:
            return FakeCroniterInstance()

        @staticmethod
        def is_valid(*_args: Any, **_kwargs: Any) -> bool:
            return True

    monkeypatch.setattr(system_executor_module, "croniter", FakeCroniter())

    sleep_delays: List[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    monkeypatch.setattr(system_executor_module.asyncio, "sleep", fake_sleep)

    strategy = {
        "id": "cron-strategy",
        "logic": "and",
        "conditions": [{"condition_id": "c"}],
        "schedule": "* * * * * *",
        "count": 2,
        "timezone": "UTC",
    }

    system = {"settings": {"system_id": "cron-system"}}

    await executor._run_with_strategy(strategy["id"], strategy, system)

    assert run_calls == ["cron-strategy", "cron-strategy"]
    assert len(sleep_delays) >= 2

    executor.tasks.clear()
    executor.running = False


@pytest.mark.asyncio
async def test_run_with_strategy_run_once_on_start(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = SystemExecutor()
    executor.running = True

    run_calls: List[str] = []

    async def fake_run_once(system: Dict[str, Any], strategy: Dict[str, Any]) -> None:
        run_calls.append(strategy["id"])

    monkeypatch.setattr(executor, "_run_once_execute", fake_run_once)

    now = datetime.now(ZoneInfo("UTC"))

    class FakeCroniterInstance:
        def __init__(self) -> None:
            self.current = now

        def get_next(self, _dt_type: Any) -> datetime:
            self.current = self.current + timedelta(seconds=1)
            return self.current

    class FakeCroniter:
        def __call__(self, *args: Any, **_kwargs: Any) -> FakeCroniterInstance:
            return FakeCroniterInstance()

        @staticmethod
        def is_valid(*_args: Any, **_kwargs: Any) -> bool:
            return True

    monkeypatch.setattr(system_executor_module, "croniter", FakeCroniter())

    async def fake_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr(system_executor_module.asyncio, "sleep", fake_sleep)

    strategy = {
        "id": "cron-strategy",
        "logic": "and",
        "conditions": [{"condition_id": "c"}],
        "schedule": "* * * * * *",
        "count": 1,
        "timezone": "UTC",
        "run_once_on_start": True,
    }

    system = {"settings": {"system_id": "cron-system"}}

    await executor._run_with_strategy(strategy["id"], strategy, system)

    assert run_calls == ["cron-strategy", "cron-strategy"]

    executor.tasks.clear()
    executor.running = False


@pytest.mark.asyncio
async def test_dry_run_mode_promotes_to_live(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = SystemExecutor()
    executor.plugin_resolver = StubPluginResolver()
    executor.condition_executor = StubConditionExecutor()
    stub_buy_sell = StubBuySellExecutor()
    executor.buy_sell_executor = stub_buy_sell

    perf_events: List[Dict[str, Any]] = []

    def capture_performance(payload: Dict[str, Any]) -> None:
        perf_events.append(payload)

    monkeypatch.setattr(system_executor_module.pg_listener, "emit_performance", capture_performance)

    system = {
        "settings": {"system_id": "dry-run-system", "dry_run_mode": "test"},
        "securities": {
            "company": "ls",
            "product": "overseas_futures",
            "appkey": "key",
            "appsecretkey": "secret",
            "paper_trading": True,
        },
        "strategies": [
            {
                "id": "strategy-dry",
                "conditions": [{"condition_id": "dummy"}],
                "order_id": "order-1",
            }
        ],
        "orders": [
            {
                "order_id": "order-1",
                "condition": {"condition_id": "OrderPlugin"},
            }
        ],
    }

    await executor.execute_system(system)

    assert stub_buy_sell.mode_changes[0] == "test"
    assert stub_buy_sell.mode_changes[-1] == "live"
    assert executor.execution_mode == "live"
    safe_event = [evt for evt in perf_events if evt.get("status") == "safe_to_live"]
    assert safe_event, "safe_to_live 이벤트가 발생해야 합니다"

    await executor.stop()


@pytest.mark.asyncio
async def test_guarded_live_raises_when_threshold_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = SystemExecutor()
    executor.plugin_resolver = StubPluginResolver()
    executor.condition_executor = StubConditionExecutor()
    executor.buy_sell_executor = StubBuySellExecutor()

    perf_events: List[Dict[str, Any]] = []

    def capture_performance(payload: Dict[str, Any]) -> None:
        perf_events.append(payload)

    monkeypatch.setattr(system_executor_module.pg_listener, "emit_performance", capture_performance)

    class FakeExecutionTimer:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self._stats = {
                "duration_seconds": 1,
                "avg_cpu_percent": 150,
                "memory_delta_mb": 10,
            }

        def __enter__(self) -> "FakeExecutionTimer":
            return self

        def __exit__(self, *_exc: Any) -> None:
            return None

        def get_result(self) -> Dict[str, Any]:
            return dict(self._stats)

    monkeypatch.setattr(system_executor_module, "ExecutionTimer", FakeExecutionTimer)

    system = {
        "settings": {
            "system_id": "guarded",
            "dry_run_mode": "guarded_live",
            "perf_thresholds": {"max_avg_cpu_percent": 50},
        },
        "securities": {
            "company": "ls",
            "product": "overseas_futures",
            "appkey": "key",
            "appsecretkey": "secret",
        },
        "strategies": [
            {
                "id": "strategy-guard",
                "conditions": [{"condition_id": "dummy"}],
                "order_id": "order-1",
            }
        ],
        "orders": [
            {
                "order_id": "order-1",
                "condition": {"condition_id": "OrderPlugin"},
            }
        ],
    }

    with pytest.raises(PerformanceExceededException):
        await executor.execute_system(system)

    throttle_events = [evt for evt in perf_events if evt.get("status") == "throttled"]
    assert throttle_events, "성능 제한 초과 이벤트가 발행돼야 합니다"

    await executor.stop()
