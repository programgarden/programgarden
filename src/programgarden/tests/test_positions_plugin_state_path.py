"""positions 기반 조건 플러그인의 strategy_state 경로 (M3, 2026-09-12).

무엇이 깨져 있었나
------------------
``ConditionNodeExecutor`` 의 positions 기반 분기는 plugin_kwargs 를
``{"positions", "fields"}`` 로 **고정**해 ``context`` 를 넘기지 않았다. 그래서
strategy_state 를 쓰는 포지션 플러그인(PartialTakeProfit)이 라이브에서 늘
``has_state=False`` 로 떨어져 상태를 저장·복원하지 못했고, 분할 익절이 매 사이클
``level_index=0`` 으로 재발동했다(3사이클 연속 50% 매도 재현).

같은 회차에 플러그인 쪽 메서드명도 실제 트래커
(``WorkflowRiskTracker.load_state``/``save_state``/``delete_state`` — 전부 동기)에
맞췄다. 여기서는 그 둘이 합쳐져 **실행기 경로로 상태가 실제로 유지되는지**를 본다.

items/data 기반 분기와 같은 규약이므로, ``context`` 파라미터가 없는 플러그인에는
종전대로 넘기지 않는다(아래 마지막 테스트).
"""

import inspect

import pytest

from programgarden.context import ExecutionContext
from programgarden.executor import ConditionNodeExecutor


def _ctx(tmp_path, *, with_state_tracker: bool) -> ExecutionContext:
    ctx = ExecutionContext(job_id="j", workflow_id="wf", storage_dir=str(tmp_path))
    if with_state_tracker:
        # BrokerNode 가 하는 일과 같다 — 플러그인이 선언한 risk feature 로 트래커 생성.
        ctx.init_risk_tracker(
            features={"state"}, product="overseas_stock",
            provider="ls-sec.co.kr", paper_trading=False,
        )
        assert ctx.risk_tracker is not None
    return ctx


def _plugin(plugin_id):
    """resolver 와 같은 경로로 플러그인 callable 을 얻는다(resolver.py: plugin_registry.get)."""
    import programgarden_community  # noqa: F401 — 플러그인 자동 등록 트리거
    from programgarden_core.registry import PluginRegistry

    plugin = PluginRegistry().get(plugin_id)
    assert plugin is not None, f"{plugin_id} 플러그인이 등록되지 않았다"
    return plugin


async def _run(ctx, qty, pnl_rate, levels):
    return await ConditionNodeExecutor().execute(
        "cond", "ConditionNode",
        {
            "plugin": "PartialTakeProfit",
            "positions": [
                {"symbol": "AAPL", "pnl_rate": pnl_rate, "qty": qty, "market_code": "82"}
            ],
            "fields": {"levels": levels},
        },
        ctx,
        plugin=_plugin("PartialTakeProfit"),
    )


@pytest.mark.asyncio
async def test_partial_take_profit_does_not_retrigger_every_cycle(tmp_path):
    """같은 단계가 매 사이클 재발동하지 않는다 (구 동작: sell 3연속)."""
    ctx = _ctx(tmp_path, with_state_tracker=True)
    levels = [{"pnl_pct": 5, "sell_pct": 50}, {"pnl_pct": 10, "sell_pct": 30}]

    actions = []
    for _ in range(3):
        out = await _run(ctx, qty=100, pnl_rate=6.0, levels=levels)
        actions.append(out["symbol_results"][0]["action"])

    assert actions == ["sell", "hold", "hold"], f"관측: {actions}"
    assert ctx.risk_tracker.load_state("partial_tp.AAPL.completed_levels") == [0]


@pytest.mark.asyncio
async def test_second_level_sizes_off_the_stored_original_quantity(tmp_path):
    """2단계 수량은 상태에 저장된 최초 수량 기준 — 상태가 실제로 복원된다는 증거."""
    ctx = _ctx(tmp_path, with_state_tracker=True)
    levels = [{"pnl_pct": 5, "sell_pct": 50}, {"pnl_pct": 10, "sell_pct": 30}]

    first = await _run(ctx, qty=100, pnl_rate=6.0, levels=levels)
    assert first["symbol_results"][0]["sell_quantity"] == 50

    second = await _run(ctx, qty=50, pnl_rate=12.0, levels=levels)
    sr = second["symbol_results"][0]
    assert sr["level_index"] == 1
    assert sr["sell_quantity"] == 30, "최초 100주의 30% (현재 50주의 30% 가 아니다)"


@pytest.mark.asyncio
async def test_without_state_tracker_falls_back_to_stateless(tmp_path):
    """트래커가 없으면(= state feature 미선언/dry_run) 종전처럼 매번 재발동한다.

    조용한 실패가 아니라 '상태 저장소가 없을 때의 정의된 동작' 이다.
    """
    ctx = _ctx(tmp_path, with_state_tracker=False)
    levels = [{"pnl_pct": 5, "sell_pct": 50}]

    actions = [
        (await _run(ctx, qty=100, pnl_rate=6.0, levels=levels))["symbol_results"][0]["action"]
        for _ in range(2)
    ]
    assert actions == ["sell", "sell"]


@pytest.mark.asyncio
async def test_context_only_goes_to_plugins_that_declare_it(tmp_path):
    """context 를 선언하지 않은 포지션 플러그인에는 넘기지 않는다 (data 분기와 같은 규약)."""
    plugin = _plugin("StopLoss")
    assert "context" not in inspect.signature(plugin).parameters

    ctx = _ctx(tmp_path, with_state_tracker=True)
    out = await ConditionNodeExecutor().execute(
        "cond", "ConditionNode",
        {
            "plugin": "StopLoss",
            "positions": [
                {"symbol": "AAPL", "pnl_rate": -9.0, "qty": 10, "market_code": "82"}
            ],
            "fields": {"stop_loss_pct": 5},
        },
        ctx,
        plugin=plugin,
    )
    # 넘기지 않아도 정상 평가된다 (TypeError 로 죽지 않는다).
    assert out["passed_symbols"][0]["symbol"] == "AAPL"


# ──────────────────────────────────────────────────────────────────────────
# M3b(2026-09-12): 계좌가 **빈 리스트**일 때도 상태 플러그인(time_based_exit)의
# '남은 entry_date 전부 정리' 스윕이 실행기 경로에서 도달 가능해야 한다.
#
# 무엇이 깨져 있었나: positions 분기는 positions 가 빈 리스트면 플러그인을 **아예
# 호출하지 않고** 조기 return 했다. 그래서 전량 매도 → 계좌 빔 → 스윕 미실행 →
# 재매수 시 옛 entry_date 가 살아남아 hold_days 가 크게 잡혀 **거짓 exit** 가 났다.
# 고친 동작: positions 가 정확히 [] 이고 플러그인이 context 를 선언하면(= 상태 사용)
# positions=[] 로 한 번 호출해 스윕 기회를 준다. 결과는 조건 판정에 쓰지 않고
# (예외는 warning 으로 삼킴) 종전의 빈 결과를 그대로 돌려준다.
#
# context 미선언 플러그인은 종전대로 호출하지 않는다(data 분기와 같은 규약).
# ──────────────────────────────────────────────────────────────────────────

_EMPTY_RESULT = {
    "symbols": [],
    "result": False,
    "is_condition_met": False,
    "passed_symbols": [],
    "failed_symbols": [],
    "symbol_results": [],
    "values": [],
}


async def _run_empty(ctx, plugin, *, plugin_id="StopLoss", fields=None):
    """positions=[] (빈 계좌)로 positions 기반 조건을 돌린다. plugin_id 는 스키마가
    positions-based(required_data=['positions'])인 실제 플러그인 이름을 빌려 쓰고,
    실행될 callable 은 주입한 fake 다."""
    return await ConditionNodeExecutor().execute(
        "cond", "ConditionNode",
        {"plugin": plugin_id, "positions": [], "fields": fields or {}},
        ctx,
        plugin=plugin,
    )


@pytest.mark.asyncio
async def test_empty_account_sweeps_context_declaring_plugin(tmp_path):
    """(a) 계좌가 비어도(=[]), context 를 받는 상태 플러그인(time_based_exit 류)은
    positions=[] 로 한 번 호출돼 스윕 기회를 얻는다 — 실제 risk tracker 경로."""
    ctx = _ctx(tmp_path, with_state_tracker=True)
    calls = []

    def sweeping_plugin(positions, fields, context):
        calls.append({"positions": positions})
        # time_based_exit 의 스윕 흉내 — 계좌가 비면 상태를 정리한다.
        if not positions and getattr(context, "risk_tracker", None) is not None:
            context.risk_tracker.save_state("time_based_exit.swept", True)
        return {"passed_symbols": [], "failed_symbols": [], "symbol_results": [], "values": [], "result": False}

    out = await _run_empty(ctx, sweeping_plugin, fields={"max_hold_days": 5})

    assert len(calls) == 1, "빈 계좌에서 상태 플러그인이 스윕 호출되지 않았다"
    assert calls[0]["positions"] == []
    # 스윕이 실제 트래커 상태까지 도달했다(실행기 경로로 상태가 유지된다는 증거).
    assert ctx.risk_tracker.load_state("time_based_exit.swept") is True
    # 스윕 결과는 조건 판정에 반영하지 않는다 — 종전의 빈 결과 그대로.
    assert out == _EMPTY_RESULT


@pytest.mark.asyncio
async def test_empty_account_does_not_call_stateless_plugin(tmp_path):
    """(b) context 를 선언하지 않은(= 무상태) 플러그인은 빈 계좌에서 호출하지 않는다."""
    ctx = _ctx(tmp_path, with_state_tracker=True)
    calls = []

    def stateless_plugin(positions, fields):   # context 파라미터 없음
        calls.append(positions)
        return {"passed_symbols": [], "failed_symbols": [], "symbol_results": [], "values": [], "result": False}

    out = await _run_empty(ctx, stateless_plugin, fields={"stop_loss_pct": 5})

    assert calls == [], "context 미선언 플러그인을 빈 계좌에서 호출했다"
    assert out == _EMPTY_RESULT


@pytest.mark.asyncio
async def test_empty_account_sweep_exception_does_not_break_node(tmp_path):
    """(c) 빈 계좌 스윕 호출이 예외를 던져도 노드 결과는 종전의 빈 결과다(삼킨다)."""
    ctx = _ctx(tmp_path, with_state_tracker=True)
    calls = []

    def raising_plugin(positions, fields, context):
        calls.append(positions)
        raise RuntimeError("sweep boom")

    out = await _run_empty(ctx, raising_plugin, fields={"max_hold_days": 5})

    assert calls == [[]], "스윕 호출 자체가 일어나지 않았다"
    assert out == _EMPTY_RESULT, "스윕 예외가 노드 결과/흐름을 깨뜨렸다"
