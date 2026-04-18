"""Phase 5/8/9: example workflow JSON validation tests.

Keeps the 67 shipped example workflows + programmer_example scripts healthy
as the codebase evolves.

Class breakdown:
- TestWorkflowStaticValidation (Phase 5): runs `WorkflowExecutor.validate()`
  on every workflow JSON in `examples/workflows/`. Any regression in node
  schemas, edge referential integrity, expression parsing, or credential
  references fails here first.
- TestWorkflowDryRunCycle (Phase 8): runs each workflow once with
  `dry_run=True` and bounded cycles. LS login is mocked so no credentials
  are required. Treats `completed`/`cancelled` as acceptable terminal
  states. Workflows that indefinitely tail realtime feeds or long bots are
  forced to stop after a short timeout.
- TestProgrammerExamples (Phase 9): smoke-imports the scripts under
  `examples/programmer_example/` to catch obvious import / collection
  breakage as the codebase evolves.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from programgarden import WorkflowExecutor


EXAMPLES_DIR = Path(__file__).parent.parent / "examples" / "workflows"
PROGRAMMER_DIR = Path(__file__).parent.parent / "examples" / "programmer_example"
WORKFLOW_FILES: List[Path] = sorted(EXAMPLES_DIR.glob("*.json"))

# Workflows that intentionally run past a single cycle (realtime feeds,
# scheduled bots). They are expected to be cancelled by the test harness
# once the timeout hits — not a failure signal.
LONG_RUNNING_WORKFLOWS = {
    "18-trigger-schedule",
    "39-realtime-futures-tick",
    "40-realtime-stock-tick",
    "55-korea-stock-schedule",
    "57-futures-paper-backtest-heavy",
    "59-trend-trailing-bot",
    "60-bollinger-reversion-bot",
    "61-hkex-futures-bot",
    "62-rsi-futures-bot",
}

# Workflows whose dry_run execution depends on mock-friendly TR responses
# that MagicMock cannot synthesize (e.g. auto-iterate from historical into
# ConditionNode with `{{ item.time_series }}` binding). The JSON itself is
# valid — these fail only in the mock harness, not in production. Revisit
# once we have a richer mock LS server.
KNOWN_MOCK_FRAGILE = {
    "29-monitor-multi-rsi",
}


def _ids(paths: List[Path]) -> List[str]:
    return [p.stem for p in paths]


def _stuff_placeholders(workflow: dict) -> dict:
    """Fill in placeholder values for every credential data entry that is
    still empty. Broker login is mocked separately so these values never
    reach any real service."""
    for cred in workflow.get("credentials", []):
        data = cred.get("data")
        if isinstance(data, list):
            for entry in data:
                if not entry.get("value"):
                    entry["value"] = "DRYRUN-PLACEHOLDER"
    return workflow


class TestWorkflowStaticValidation:
    """Every bundled example workflow must pass WorkflowExecutor.validate()."""

    def test_workflow_files_discovered(self):
        """Sanity: repo ships with 67 example workflows."""
        assert len(WORKFLOW_FILES) == 67, (
            f"expected 67 workflow JSON files, found {len(WORKFLOW_FILES)}"
        )

    @pytest.mark.parametrize("wf_path", WORKFLOW_FILES, ids=_ids(WORKFLOW_FILES))
    def test_workflow_is_valid_json(self, wf_path: Path):
        """Each workflow must be parseable JSON."""
        with open(wf_path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), f"{wf_path.name}: top-level is not an object"
        assert "nodes" in data, f"{wf_path.name}: missing 'nodes' key"
        assert "edges" in data, f"{wf_path.name}: missing 'edges' key"

    @pytest.mark.parametrize("wf_path", WORKFLOW_FILES, ids=_ids(WORKFLOW_FILES))
    def test_workflow_passes_validate(self, wf_path: Path):
        """Every workflow must pass WorkflowExecutor.validate()."""
        with open(wf_path, encoding="utf-8") as f:
            workflow = json.load(f)
        executor = WorkflowExecutor()
        result = executor.validate(workflow)
        assert result.is_valid, (
            f"{wf_path.name}: {len(result.errors)} validation error(s):\n"
            + "\n".join(f"  - {e}" for e in result.errors[:10])
        )


class TestWorkflowDryRunCycle:
    """Every workflow must reach a terminal state under dry_run + mocked LS."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("wf_path", WORKFLOW_FILES, ids=_ids(WORKFLOW_FILES))
    async def test_workflow_dry_run_cycle(self, wf_path: Path):
        if wf_path.stem in KNOWN_MOCK_FRAGILE:
            pytest.xfail(
                f"{wf_path.stem} fails under MagicMock-based LS responses; "
                "auto-iterate expression binding depends on real TR output shape"
            )

        with open(wf_path, encoding="utf-8") as f:
            workflow = _stuff_placeholders(json.load(f))

        executor = WorkflowExecutor()
        mock_ls = MagicMock()

        with patch("programgarden.executor.ensure_ls_login") as login_mock:
            login_mock.return_value = (mock_ls, True, None)
            job = await asyncio.wait_for(
                executor.execute(
                    workflow,
                    context_params={"dry_run": True, "max_cycles": 1},
                ),
                timeout=15.0,
            )

            timeout_s = 5.0 if wf_path.stem in LONG_RUNNING_WORKFLOWS else 15.0
            try:
                await asyncio.wait_for(job._task, timeout=timeout_s)
                forced_stop = False
            except asyncio.TimeoutError:
                await job.stop()
                forced_stop = True

        state = job.get_state()
        status = state.get("status")
        errors_count = state.get("stats", {}).get("errors_count", 0)

        if wf_path.stem in LONG_RUNNING_WORKFLOWS:
            assert status in {"completed", "cancelled", "stopping", "stopped"}, (
                f"{wf_path.name}: unexpected terminal status {status!r} "
                f"(forced_stop={forced_stop})"
            )
        else:
            assert status == "completed", (
                f"{wf_path.name}: expected status='completed', got {status!r} "
                f"(errors={errors_count})"
            )
            assert errors_count == 0, (
                f"{wf_path.name}: errors_count={errors_count}, "
                f"status={status}. Last error logs:\n"
                + "\n".join(
                    f"  - {log.get('message', '')[:180]}"
                    for log in state.get("logs", [])
                    if log.get("level") == "error"
                )[:5]
            )


class TestProgrammerExamples:
    """Ensure programmer_example/ scripts remain importable."""

    @pytest.mark.parametrize(
        "script_path",
        sorted(PROGRAMMER_DIR.glob("*.py")) if PROGRAMMER_DIR.exists() else [],
        ids=lambda p: p.stem,
    )
    def test_programmer_example_importable(self, script_path: Path):
        """Each programmer_example script must be importable (smoke test)."""
        if script_path.stem == "test_ai_agent_live":
            # Live script runs actual LLM calls inside guard clauses; skip
            # unless the user wires real credentials.
            if not os.getenv("OPENAI_API_KEY"):
                pytest.skip("OPENAI_API_KEY not set; live script requires it")

        spec = importlib.util.spec_from_file_location(
            script_path.stem, script_path
        )
        assert spec is not None, f"{script_path}: failed to create import spec"
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        try:
            spec.loader.exec_module(module)
        except SystemExit:
            # Some live scripts call sys.exit(1) when credentials missing.
            pass
