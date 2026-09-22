"""Replay uses the real cooldown state rather than dry-run forced pass-through."""
import pytest

from programgarden.executor import ThrottleNodeExecutor
from programgarden.validation_replay import ReplayContext, replay
from tests.test_validation_replay import code, workflow


@pytest.mark.asyncio
@pytest.mark.parametrize("pass_first", [True, False])
async def test_first_event_preserves_actual_gate(pass_first):
    graph = workflow(code("source", "5"), {"id": "gate", "type": "ThrottleNode",
        "pass_first": pass_first, "interval_sec": 5.0},
        code("sink", "data * 2", data="{{ nodes.source.result }}"))
    result = await replay(graph, {"as_of": "2026-09-22T14:00:00Z"})
    assert result.passed, result.errors
    assert ("sink" in result.executed) is pass_first
    if pass_first:
        assert result.outputs["sink"]["result"] == 10
    else:
        assert result.outputs["gate"]["_throttled"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,expected", [("skip", 3), ("latest", 2)])
async def test_same_context_replays_cooldown_and_pending_data(mode, expected):
    context = ReplayContext("fixture-run", "fixture-workflow", context_params={"dry_run": True})
    executor = ThrottleNodeExecutor()
    config = {"mode": mode, "interval_sec": 5.0, "pass_first": True}
    observations = []
    for second, value in [(0, 1), (4, 2), (5, 3)]:
        context.validation_as_of = f"2026-09-22T14:00:{second:02}Z"
        observations.append(await executor.execute("gate", "ThrottleNode",
            {**config, "_realtime_data": {"result": value}}, context))
    assert observations[0]["result"] == 1
    assert observations[1]["_throttled"] is True
    assert observations[2]["result"] == expected
    assert observations[2]["_throttle_stats"]["skipped_count"] == 1
    assert observations[2]["_throttle_stats"]["last_passed_at"] == "2026-09-22T14:00:05+00:00"


@pytest.mark.asyncio
async def test_clock_is_required_even_for_first_event():
    result = await replay(workflow({"id": "gate", "type": "ThrottleNode"}), {})
    assert not result.passed
    assert any(e["code"] == "REPLAY_FIXTURE_REQUIRED" for e in result.errors)


@pytest.mark.asyncio
async def test_waiting_branch_cannot_be_bypassed_at_a_join():
    graph = workflow(code("source", "5"), {"id": "gate", "type": "ThrottleNode", "pass_first": False},
                     code("blocked"), code("join"))
    graph["nodes"].append(code("independent", "42"))
    graph["edges"] += [{"from": "start", "to": "independent"}, {"from": "independent", "to": "join"}]
    result = await replay(graph, {"as_of": "2026-09-22T14:00:00Z"})
    assert result.passed, result.errors
    assert result.outputs["independent"]["result"] == 42
    assert {"blocked", "join"} <= set(result.skipped)
    assert not {"blocked", "join"} & set(result.executed)
