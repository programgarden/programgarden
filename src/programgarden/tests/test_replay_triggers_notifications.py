"""Clock-aware startup paths and recorded notifications never run side effects."""

from unittest.mock import AsyncMock, patch

import pytest

from programgarden.context import ExecutionContext
from programgarden.replay_external import recording
from programgarden.validation_replay import replay
from programgarden_core.nodes.trigger import TradingHoursFilterNode
from tests.test_validation_replay import workflow, code

AS_OF = "2026-09-22T14:00:00Z"


def chain(node):
    return workflow(node, code(data="{{ 3 }}", value="data + 1"))


@pytest.mark.asyncio
async def test_schedule_runs_real_startup_without_timer_events():
    graph = chain({"id": "clock", "type": "ScheduleNode", "cron": "30 9 * * 1-5"})
    # LIVE starts immediately, even though this instant is not a cron tick.
    with patch.object(ExecutionContext, "emit_event", new_callable=AsyncMock) as emit:
        result = await replay(graph, {"as_of": AS_OF})
    assert result.passed, result.errors
    assert result.outputs["clock"]["trigger"] is True
    assert result.outputs["calc"]["result"] == 4
    emit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [
    {"cron": "not cron"}, {"timezone": "bad/zone"}, {"count": 0}, {"max_duration_hours": 0},
])
async def test_bad_schedule_never_certifies_downstream(change):
    node = {"id": "clock", "type": "ScheduleNode", "cron": "*/5 * * * *", **change}
    result = await replay(chain(node), {"as_of": AS_OF})
    assert not result.passed and "calc" not in result.executed


@pytest.mark.asyncio
async def test_disabled_schedule_does_not_become_a_live_trigger():
    result = await replay(chain({"id": "clock", "type": "ScheduleNode", "cron": "*/5 * * * *",
                                 "enabled": False}), {"as_of": AS_OF})
    assert result.passed, result.errors
    assert result.outputs["clock"]["trigger"] is False
    assert "calc" not in result.executed


@pytest.mark.asyncio
@pytest.mark.parametrize("instant,allowed", [
    ("2026-09-22T13:29:59Z", False), ("2026-09-22T13:30:00Z", True),
    ("2026-09-22T20:00:00Z", True), ("2026-09-22T20:01:00Z", False),
    ("2026-09-26T14:00:00Z", False), ("2026-12-22T14:30:00Z", True),
])
async def test_trading_hours_uses_live_inclusive_minute_boundary_without_waiting(instant, allowed):
    node = {"id": "hours", "type": "TradingHoursFilterNode", "start": "09:30", "end": "16:00"}
    with patch.object(TradingHoursFilterNode, "execute", side_effect=AssertionError("Wall-clock wait forbidden")):
        result = await replay(chain(node), {"as_of": instant})
    assert result.passed is allowed, result.errors
    assert ("calc" in result.executed) is allowed
    if not allowed:
        assert any(e["code"] == "REPLAY_TIME_WAIT_BLOCKED" for e in result.errors)


@pytest.mark.asyncio
@pytest.mark.parametrize("node", [
    {"id": "clock", "type": "ScheduleNode", "cron": "*/5 * * * *"},
    {"id": "hours", "type": "TradingHoursFilterNode"},
])
async def test_time_nodes_require_explicit_clock(node):
    result = await replay(chain(node), {})
    assert not result.passed
    assert any(e["code"] == "REPLAY_FIXTURE_REQUIRED" for e in result.errors)


@pytest.mark.parametrize("change", [{"start": "bad"}, {"end": "25:00"},
    {"start": "22:00", "end": "04:00"}, {"days": ["holiday"]}, {"days": []}])
def test_invalid_window_never_fails_open(change):
    from datetime import datetime
    node = TradingHoursFilterNode(id="hours", **change)
    with pytest.raises(ValueError):
        node._is_trading_hours(as_of=datetime.fromisoformat(AS_OF))


@pytest.mark.asyncio
async def test_notification_is_request_bound_and_never_calls_transport():
    from programgarden_community.nodes.messaging.telegram import TelegramNode
    node = {"id": "notify", "type": "TelegramNode", "template": "AAPL: 2 shares"}
    fixture = {"as_of": AS_OF, "nodes": {"notify": recording("TelegramNode", node,
        {"sent": True, "message_id": "fixture-message"},
        {"type": "object", "required": ["sent", "message_id"],
         "properties": {"sent": {"type": "boolean"}, "message_id": {"type": "string"}}}, as_of=AS_OF)}}
    with patch.object(TelegramNode, "execute", side_effect=AssertionError("Network send forbidden")):
        result = await replay(chain(node), fixture)
        assert result.passed, result.errors
        assert result.mode == "SIMULATION" and result.live_authorized is False
        node["template"] = "AAPL: 20 shares"
        changed = await replay(chain(node), fixture)
    assert not changed.passed and "calc" not in changed.executed
    assert any(e["code"] == "REPLAY_FIXTURE_MISMATCH" for e in changed.errors)
