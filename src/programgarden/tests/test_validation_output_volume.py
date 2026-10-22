"""Output-volume baseline for the 77 example workflows (plan §5.6.4).

This is a coarse regression guard: every shipped example must validate
under the default `ValidationLimits` without triggering a cap. If a future
change makes the validator dramatically chattier, this test fails first
and forces an explicit decision instead of silently shipping noisy output.

It is NOT a correctness gate for individual codes — those live in
`test_validation_errors_structured.py`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from programgarden import WorkflowExecutor

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples" / "workflows"


def _workflow_paths() -> list[Path]:
    return sorted(EXAMPLES_DIR.glob("*.json"))


@pytest.mark.parametrize("path", _workflow_paths(), ids=lambda p: p.stem)
def test_example_workflow_within_default_limits(path: Path) -> None:
    executor = WorkflowExecutor()
    definition = json.loads(path.read_text(encoding="utf-8"))
    result = executor.validate(definition)
    # No example workflow should trip the default caps.
    assert not result.truncated, (
        f"{path.stem} hit default ValidationLimits caps: {result.truncated}"
    )
    # Summary must always be populated by finalize_result.
    assert result.summary is not None
    # Channel sanity: runtime channel only fills via dry_run, never validate().
    assert result.runtime_recommendations == []
