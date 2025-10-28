from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from zoneinfo import ZoneInfo

from programgarden.system_executor import SystemExecutor
from programgarden import system_executor as system_executor_module


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

        async def _real_order_websockets(*, system: Dict[str, Any]) -> None:
            self.real_order_system = system

        self.real_order_executor = SimpleNamespace(real_order_websockets=_real_order_websockets)

    async def new_order_execute(
        self,
        *,
        system: Dict[str, Any],
        symbols_from_strategy: List[Dict[str, Any]],
        new_order: Dict[str, Any],
        order_id: str,
        order_types: List[str],
    ) -> None:
        self.new_order_calls.append(
            {
                "system_id": system["settings"]["system_id"],
                "order_id": order_id,
                "symbols": symbols_from_strategy,
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
