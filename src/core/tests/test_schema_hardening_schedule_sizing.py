"""⑭ ScheduleNode / ⑰ PositionSizingNode schema hardening (2026-08-08 e2e track).

Guards the model-level half of the "looks configured, behaves differently"
fixes:

* ⑭ ScheduleNode.cron is required with NO default (the old "*/5 * * * *"
  default let a schedule with no cron silently run every 5 minutes). The
  executor-only `count` key is now a declared model field (schema/executor
  duality removed).
* ⑰ PositionSizingNode.method is required with NO default (the old
  "fixed_percent" default silently confirmed hallucinated keys). A sentinel
  None keeps model construction working; the executor enforces at runtime.

Plan: .claude/plans/2026-08-08-e2e-improvement-track-plan.md §3.3.1 / §3.3.2.
"""

from __future__ import annotations

from programgarden_core.nodes.trigger import ScheduleNode
from programgarden_core.nodes.risk import PositionSizingNode


# ── ⑭ ScheduleNode ────────────────────────────────────────────────────────

def test_schedule_cron_field_schema_required_no_default():
    """cron is required=True with NO default — no "generation may omit it" signal."""
    fs = ScheduleNode.get_field_schema()
    assert "cron" in fs
    cron = fs["cron"]
    assert cron.required is True, "cron must be required"
    assert cron.default is None, (
        "cron must NOT carry a default — a default re-introduces the silent "
        "5-minute fallback signal"
    )


def test_schedule_model_cron_is_required():
    """Constructing a ScheduleNode without cron raises (required model field)."""
    import pytest
    with pytest.raises(Exception):
        ScheduleNode(id="s")
    # With cron it constructs fine.
    node = ScheduleNode(id="s", cron="*/5 * * * *")
    assert node.cron == "*/5 * * * *"


def test_schedule_count_is_declared_field_not_executor_only():
    """count (executor safety cap) is a declared model + schema field now."""
    node = ScheduleNode(id="s", cron="0 9 * * *")
    assert node.count == 1000  # default matches the executor's cap
    fs = ScheduleNode.get_field_schema()
    assert "count" in fs, "count must be exposed in the schema (duality removed)"
    assert fs["count"].default == 1000


def test_schedule_anti_patterns_flag_mode_schedule_keys():
    """The AI-facing anti-patterns explicitly warn against {mode, schedule}."""
    joined = " ".join(
        f"{ap.get('pattern','')} {ap.get('reason','')} {ap.get('alternative','')}"
        for ap in ScheduleNode._anti_patterns
    )
    assert "mode" in joined and "schedule" in joined
    assert "cron" in joined


# ── ⑰ PositionSizingNode ──────────────────────────────────────────────────

def test_sizing_method_field_schema_required_no_default():
    """method is required=True with NO default (the fixed_percent default was the
    silent-fallback root)."""
    fs = PositionSizingNode.get_field_schema()
    assert "method" in fs
    method = fs["method"]
    assert method.required is True
    assert method.default is None, "method must NOT carry a default"


def test_sizing_model_method_sentinel_allows_construction():
    """method uses a None sentinel so model construction keeps working
    (PositionSizingNode(id=...) is used in tests / catalog placeholders); the
    executor enforces presence at runtime, not the model."""
    node = PositionSizingNode(id="ps")
    assert node.method is None
