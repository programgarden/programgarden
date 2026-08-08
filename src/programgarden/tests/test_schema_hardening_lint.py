"""⑭ ScheduleNode / ⑰ PositionSizingNode schema-hardening save-chokepoint lint
+ runtime hard-errors (2026-08-08 e2e track).

Covers the programgarden-side half of §3.3.1 / §3.3.2:

* Unknown-key lint (semantic rule R5, ErrorCode.UNKNOWN_NODE_FIELD) — opt-in,
  off by default, blocking under STRICT. Detects hallucinated / typo'd node
  config keys that ``extra="allow"`` silently accepts and the executor never
  reads (ScheduleNode {mode,schedule} instead of cron; PositionSizingNode
  size_type instead of method).
* Executor hard-errors — ScheduleNode with no cron and PositionSizingNode with
  no method raise explicitly instead of silently falling back to "*/5 * * * *"
  / "fixed_percent".
* Backward compatibility — a stored DSL carrying {mode,schedule} and no cron
  must still LOAD (deserialize + plain validate); only the save chokepoint
  (validate_deep + STRICT) and the executor block it.

Plan: .claude/plans/2026-08-08-e2e-improvement-track-plan.md §3.3.1 / §3.3.2.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from programgarden import ProgramGarden
from programgarden.semantic_rules import (
    analyze_workflow_semantics,
    normalize_severities,
    STRICT_SEMANTIC_SEVERITIES,
    DEFAULT_SEMANTIC_SEVERITIES,
    RULE_UNKNOWN_NODE_FIELD,
)
from programgarden_core import ErrorCode, WorkflowDefinition


def _codes(infos):
    return [str(i.code) for i in infos]


def _fields_for(infos, node_id):
    return {
        i.location.field_path
        for i in infos
        if str(i.code) == ErrorCode.UNKNOWN_NODE_FIELD.value
        and i.location.node_id == node_id
    }


# ── R5 registration / defaults ────────────────────────────────────────────

def test_r5_registered_and_strict_blocks():
    assert RULE_UNKNOWN_NODE_FIELD in STRICT_SEMANTIC_SEVERITIES
    assert STRICT_SEMANTIC_SEVERITIES[RULE_UNKNOWN_NODE_FIELD] == "error"
    # off in the all-off default
    assert normalize_severities(None)[RULE_UNKNOWN_NODE_FIELD] == "off"


def test_r5_off_by_default_no_findings():
    wf = {"nodes": [{"id": "c", "type": "ScheduleNode",
                     "mode": "interval", "schedule": {"every": "5m"}}], "edges": []}
    assert analyze_workflow_semantics(wf, DEFAULT_SEMANTIC_SEVERITIES) == []
    # None config == all off
    assert analyze_workflow_semantics(wf, None) == []


# ── ⑭ {mode, schedule} detection ──────────────────────────────────────────

def test_r5_detects_schedule_mode_and_schedule_keys():
    wf = {"nodes": [
        {"id": "cron", "type": "ScheduleNode", "mode": "interval",
         "schedule": {"every": "5m"}},  # no cron — the P2-style hallucination
    ], "edges": []}
    infos = analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES)
    assert all(c == ErrorCode.UNKNOWN_NODE_FIELD.value for c in _codes(infos))
    assert _fields_for(infos, "cron") == {"mode", "schedule"}
    # every finding is blocking under STRICT
    assert all(str(i.severity) in ("error", "ErrorSeverity.ERROR") for i in infos)


def test_r5_canonical_schedule_not_flagged():
    """A ScheduleNode using only canonical keys is clean."""
    wf = {"nodes": [
        {"id": "cron", "type": "ScheduleNode", "cron": "*/5 * * * *",
         "timezone": "America/New_York", "enabled": True,
         "max_duration_hours": 24.0, "count": 1000},
    ], "edges": []}
    assert analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES) == []


# ── ⑰ 3-fold sizing violation ─────────────────────────────────────────────

def test_r5_detects_three_fold_sizing_violation():
    """P2-style sizing payload with 3 schema-outside keys — all detected at the
    save chokepoint (STRICT). Canonical is `method` (+ its family), not
    size_type / amount / allocation."""
    wf = {"nodes": [
        {"id": "sizing", "type": "PositionSizingNode",
         "size_type": "fixed",      # should be `method`
         "amount": 1000,            # should be `fixed_amount`
         "allocation": 0.1,         # not a field at all
         "balance": "{{ nodes.acct.balance }}"},  # canonical — NOT flagged
    ], "edges": []}
    infos = analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES)
    assert all(c == ErrorCode.UNKNOWN_NODE_FIELD.value for c in _codes(infos))
    assert _fields_for(infos, "sizing") == {"size_type", "amount", "allocation"}


def test_r5_canonical_sizing_not_flagged():
    wf = {"nodes": [
        {"id": "sizing", "type": "PositionSizingNode", "method": "fixed_percent",
         "max_percent": 10.0, "balance": "{{ nodes.acct.balance }}",
         "symbols": "{{ nodes.cond.passed_symbols }}"},
    ], "edges": []}
    assert analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES) == []


def test_r5_credential_id_reserved_not_flagged():
    """`credential_id` is the canonical credential-binding key (`nodes[].credential_id`
    + top-level `credentials[]`): the executor's universal node-creation layer consumes
    it for every node type, so no per-node schema declares it. R5 must treat it as
    reserved — the real P2 payload carries it on account/order nodes, and flagging it
    would block every credential-bound workflow at the strict save gate."""
    wf = {"nodes": [
        {"id": "acct", "type": "OverseasFuturesAccountNode",
         "credential_id": "da406e2a-9b50-40d2-91ea-6f95a4f726f7"},
        {"id": "buy", "type": "OverseasFuturesNewOrderNode",
         "credential_id": "da406e2a-9b50-40d2-91ea-6f95a4f726f7",
         "order": "{{ nodes.sizing.order }}"},
    ], "edges": []}
    infos = analyze_workflow_semantics(wf, STRICT_SEMANTIC_SEVERITIES)
    assert not [
        i for i in infos
        if str(i.code) == ErrorCode.UNKNOWN_NODE_FIELD.value
        and i.location.field_path == "credential_id"
    ]


# ── validate_deep integration (save chokepoint) ───────────────────────────

def test_validate_deep_strict_detects_schedule_hallucination():
    pg = ProgramGarden()
    wf = {
        "id": "w", "name": "w",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "cron", "type": "ScheduleNode", "mode": "interval",
             "schedule": {"every": "5m"}},
        ],
        "edges": [{"from": "start", "to": "cron"}],
    }
    res = pg.validate_deep(wf, semantic_rules=STRICT_SEMANTIC_SEVERITIES, timeout=15.0)
    assert not res.is_valid
    unknown_fields = _fields_for(res.errors, "cron")
    assert {"mode", "schedule"} <= unknown_fields
    # default pass (no semantic_rules) does NOT introduce the code
    res_default = pg.validate_deep(wf, timeout=15.0)
    assert ErrorCode.UNKNOWN_NODE_FIELD.value not in _codes(res_default.errors)


# ── executor hard-errors (silent fallback no longer reproducible) ──────────

@pytest.mark.asyncio
async def test_schedule_executor_raises_without_cron():
    from programgarden.executor import ScheduleNodeExecutor

    ex = ScheduleNodeExecutor()
    ctx = MagicMock()
    ctx.log = MagicMock()
    ctx._persistent_tasks = {}
    ctx.is_running = True
    ctx.is_dry_run = False

    # {mode, schedule} but no cron — the old code silently used "*/5 * * * *".
    config = {"mode": "interval", "schedule": {"every": "5m"}}
    with pytest.raises(ValueError, match="cron"):
        await ex.execute("cron", "ScheduleNode", config, ctx)


@pytest.mark.asyncio
async def test_sizing_executor_raises_without_method():
    from programgarden.executor import PositionSizingNodeExecutor

    ex = PositionSizingNodeExecutor()
    ctx = MagicMock()
    ctx.log = MagicMock()
    ctx.job_id = "t"
    ctx.is_running = True
    ctx.is_dry_run = False
    ctx.get_expression_context = MagicMock(return_value=MagicMock())

    # size_type instead of method — the old code silently used "fixed_percent".
    config = {
        "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}],
        "balance": {"orderable_amount": 10000.0},
        "size_type": "fixed",
        "amount": 1000,
    }
    with pytest.raises(ValueError, match="method"):
        await ex.execute("sizing", "PositionSizingNode", config, ctx)


# ── backward compatibility: stored DSL must still LOAD ─────────────────────

def test_legacy_dsl_with_mode_schedule_and_no_cron_still_loads():
    """A stored DSL carrying {mode,schedule} and no cron must NOT die at load.
    Deserialization keeps nodes as dicts, and plain validate() (no semantic
    rules) stays structurally valid — the unknown-key block is opt-in
    (save/validate_deep) only."""
    dsl = {
        "id": "legacy", "name": "legacy",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "sched", "type": "ScheduleNode", "mode": "interval",
             "schedule": {"every": "5m"}},
        ],
        "edges": [{"from": "start", "to": "sched"}],
    }
    # 1. deserialize does not raise
    wd = WorkflowDefinition(**dsl)
    assert len(wd.nodes) == 2
    # 2. plain validate stays valid → resolve/load path is unaffected
    pg = ProgramGarden()
    res = pg.validate(dsl)
    assert res.is_valid, [e.short() for e in res.errors]
    assert ErrorCode.UNKNOWN_NODE_FIELD.value not in _codes(res.errors)
