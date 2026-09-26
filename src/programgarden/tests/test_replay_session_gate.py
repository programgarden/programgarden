"""Replay uses the live session predicate with a trusted shared fixture clock."""
from unittest.mock import patch

import pytest

from programgarden.validation_replay import replay
from programgarden_core.nodes.session_gate import SessionGateNode


def graph():
    return {"id": "session-replay", "name": "Session replay", "nodes": [
        {"id": "start", "type": "StartNode"},
        {"id": "session", "type": "SessionGateNode", "timezone": "America/New_York",
         "windows": [{"start": "09:30", "end": "16:00"}],
         "days": ["mon", "tue", "wed", "thu", "fri"]},
        {"id": "gate", "type": "IfNode", "left": "{{ nodes.session.allowed }}",
         "operator": "==", "right": True},
        {"id": "work", "type": "CodeNode", "outputs": [{"name": "result", "type": "number"}],
         "code": "def execute(data, params, context):\n return {'result': 1}"},
    ], "edges": [{"from": "start", "to": "session"},
                 {"from": "session", "to": "gate"},
                 {"from": "gate", "to": "work", "from_port": "true"}]}


@pytest.mark.asyncio
@pytest.mark.parametrize("as_of,allowed", [
    ("2026-09-22T13:29:59Z", False),
    ("2026-09-22T13:30:00Z", True),
    ("2026-09-22T20:00:00Z", False),
    ("2026-09-26T15:00:00Z", False),
    ("2026-12-22T14:29:59Z", False),
    ("2026-12-22T14:30:00Z", True),
])
async def test_session_chain_uses_fixture_instant_and_real_branch(as_of, allowed):
    # The wall-clock path must never run, even for an open fixture session.
    with patch.object(SessionGateNode, "execute", side_effect=AssertionError("Wall clock is forbidden")):
        result = await replay(graph(), {"as_of": as_of})
    assert result.passed, result.errors
    assert result.outputs["session"]["allowed"] is allowed
    assert ("work" in result.executed) is allowed
    assert ("work" in result.skipped) is not allowed


@pytest.mark.asyncio
async def test_session_without_fixture_clock_cannot_pass():
    result = await replay(graph(), {})
    assert not result.passed
    assert any(e["code"] == "REPLAY_FIXTURE_REQUIRED" for e in result.errors)
    assert "work" not in result.executed


@pytest.mark.asyncio
async def test_closed_date_is_not_overridden_by_open_time():
    definition = graph()
    definition["nodes"][1]["closed_dates"] = ["2026-09-22"]
    result = await replay(definition, {"as_of": "2026-09-22T15:00:00Z"})
    assert result.passed, result.errors
    assert result.outputs["session"]["allowed"] is False
    assert "work" not in result.executed
