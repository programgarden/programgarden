from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List

import pytest

from programgarden import Programgarden
import programgarden.client as client_module
from programgarden_core.exceptions import SystemShutdownException


@dataclass
class StubTokenManager:
    modes: List[bool] = field(default_factory=list)

    def configure_trading_mode(self, mode: bool) -> None:
        self.modes.append(mode)


@dataclass
class StubLS:
    token_manager: StubTokenManager = field(default_factory=StubTokenManager)
    login_calls: List[Dict[str, Any]] = field(default_factory=list)
    _logged_in: bool = False

    def is_logged_in(self) -> bool:
        return self._logged_in

    async def async_login(self, *, appkey: str, appsecretkey: str, paper_trading: bool) -> bool:
        self.login_calls.append(
            {
                "appkey": appkey,
                "appsecretkey": appsecretkey,
                "paper_trading": paper_trading,
            }
        )
        self._logged_in = True
        return True


@dataclass
class StubExecutor:
    running: bool = False
    executed_systems: List[Dict[str, Any]] = field(default_factory=list)
    stopped: bool = False

    async def execute_system(self, system: Dict[str, Any]) -> None:
        self.executed_systems.append(system)

    async def stop(self) -> None:
        self.stopped = True


class StubListener:
    def __init__(self) -> None:
        self.exceptions: List[Exception] = []
        self.stopped = False

    def emit_exception(self, exc: Exception) -> None:
        self.exceptions.append(exc)

    def stop(self) -> None:
        self.stopped = True


def _build_korean_config() -> Dict[str, Any]:
    return {
        "설정": {
            "시스템ID": "sys-1",
            "디버그": "INFO",
        },
        "증권": {
            "회사": "ls",
            "상품": "overseas_futures",
            "앱키": "APPKEY",
            "앱시크릿": "APPSECRET",
            "모의투자": True,
        },
        "전략": [
            {
                "전략ID": "strategy-1",
                "로직": "and",
                "조건": [
                    {"condition_id": "dummy"},
                ],
                "symbols": [
                    {"symbol": "ADZ25", "exchcd": "CME"},
                ],
                "order_id": "order-1",
            }
        ],
        "주문": [
            {
                "order_id": "order-1",
                "설명": "테스트",
                "condition": {"condition_id": "OrderPlugin"},
            }
        ],
    }


def _build_english_config() -> Dict[str, Any]:
    return {
        "settings": {
            "system_id": "loop-test",
            "debug": "INFO",
        },
        "securities": {
            "company": "ls",
            "product": "overseas_futures",
            "appkey": "KEY",
            "appsecretkey": "SECRET",
        },
        "strategies": [
            {
                "id": "strategy-A",
                "logic": "and",
                "conditions": [{"condition_id": "cond-A"}],
            }
        ],
        "orders": [],
    }


def test_run_normalizes_configuration_and_executes_system(monkeypatch: pytest.MonkeyPatch) -> None:
    pg = Programgarden()

    stub_listener = StubListener()
    monkeypatch.setattr(client_module, "pg_listener", stub_listener)

    stub_ls = StubLS()
    monkeypatch.setattr(client_module.LS, "get_instance", lambda: stub_ls)

    stub_executor = StubExecutor()
    pg._executor = stub_executor
    monkeypatch.setattr(pg, "_print_banner", lambda: None)

    original_config = _build_korean_config()
    pg.run(original_config)

    assert stub_executor.executed_systems, "SystemExecutor should be invoked"
    executed = stub_executor.executed_systems[0]

    assert executed["settings"]["system_id"] == "sys-1"
    assert executed["securities"]["company"] == "ls"
    assert executed["securities"]["paper_trading"] is True

    assert stub_ls.login_calls == [
        {
            "appkey": "APPKEY",
            "appsecretkey": "APPSECRET",
            "paper_trading": True,
        }
    ]
    assert stub_ls.token_manager.modes == [True]
    assert stub_executor.stopped is True

    assert stub_listener.stopped is True
    assert any(isinstance(exc, SystemShutdownException) for exc in stub_listener.exceptions)

    assert "설정" in original_config, "Input config must stay untouched"


@pytest.mark.asyncio
async def test_run_returns_task_when_event_loop_active(monkeypatch: pytest.MonkeyPatch) -> None:
    pg = Programgarden()

    monkeypatch.setattr(client_module, "pg_listener", StubListener())
    monkeypatch.setattr(pg, "_print_banner", lambda: None)

    async def fake_execute(system: Dict[str, Any]) -> str:
        fake_execute.called_with = system
        return "done"

    fake_execute.called_with = {}  # type: ignore[attr-defined]
    monkeypatch.setattr(pg, "_execute", fake_execute)

    task = pg.run(_build_english_config())
    assert isinstance(task, asyncio.Task)

    await task
    assert fake_execute.called_with["settings"]["system_id"] == "loop-test"
