"""Phase 5/8/9: example workflow JSON validation tests.

Keeps the 87 shipped example workflows + programmer_example scripts healthy
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

# Workflows that historically required forced cancellation under dry_run
# because the event loop blocked on schedule_tick / realtime ticks that
# never arrive. Since the executor now skips _event_loop in dry_run mode
# (ScheduleNode/Real* executors emit a single dry_run cycle and exit),
# every workflow is expected to reach status='completed' naturally.
LONG_RUNNING_WORKFLOWS: set[str] = set()

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
        """Sanity: repo ships with 99 example workflows."""
        assert len(WORKFLOW_FILES) == 99, (
            f"expected 99 workflow JSON files, found {len(WORKFLOW_FILES)}"
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


#: Phase 5.2 domestic-stock (Korea) examples. Unlike the legacy corpus —
#: which carries some historical unknown fields that BaseNode's
#: ``extra="allow"`` silently tolerates — these must be schema-exact: every
#: node key must be a declared model field (or an intentional executor-read
#: extra, see ``_ALLOWED_NODE_EXTRAS``). Few-shot generation copies these
#: verbatim, so a phantom field here (e.g. a ``price`` that
#: PositionSizingNode never reads) propagates into every generated workflow.
#: Scoped to 94-97 only — earlier Korea examples (50/53/55) predate this gate.
_KOREA_GATE_STEMS = {
    "94-korea-stock-order-rsi-buy",
    "95-korea-stock-strategy-condition-logic",
    "96-korea-stock-backtest-rsi-bollinger",
    "97-korea-stock-code-node-composite",
}
KOREA_EXAMPLE_FILES: List[Path] = sorted(
    p for p in EXAMPLES_DIR.glob("*-korea-*.json") if p.stem in _KOREA_GATE_STEMS
)

#: Node-level keys that are structural/presentational, not schema fields.
_NODE_META_KEYS = {"id", "type", "position", "description", "name"}

#: Per-node-type keys the executor intentionally reads via ``extra="allow"``
#: even though they are not declared Pydantic fields. These are functional
#: (the executor consumes them), unlike phantom fields that are silently
#: dropped. Keep this list tight — only add a key after confirming the
#: executor actually reads it.
_ALLOWED_NODE_EXTRAS = {
    "SplitNode": {"items"},  # executor iterates config['items']; see 69-* legacy
}


class TestKoreaExampleSchemaFields:
    """Gate: the domestic-stock examples must use only declared node fields.

    ``WorkflowExecutor.validate()`` and the dry-run cycle both pass despite
    unknown fields because ``BaseNode(model_config=extra="allow")`` swallows
    them. This class closes that gap — but only for the new Korea corpus, so
    legacy examples with historical drift are unaffected.
    """

    def test_korea_examples_present(self):
        assert len(KOREA_EXAMPLE_FILES) == 4, (
            f"expected 4 *-korea-*.json examples, found {len(KOREA_EXAMPLE_FILES)}: "
            f"{[p.name for p in KOREA_EXAMPLE_FILES]}"
        )

    @pytest.mark.parametrize(
        "wf_path", KOREA_EXAMPLE_FILES, ids=_ids(KOREA_EXAMPLE_FILES)
    )
    def test_korea_nodes_have_no_unknown_fields(self, wf_path: Path):
        import programgarden_core

        with open(wf_path, encoding="utf-8") as f:
            workflow = json.load(f)

        offenders: list[str] = []
        for node in workflow.get("nodes", []):
            node_type = node.get("type")
            cls = getattr(programgarden_core, node_type, None)
            assert cls is not None, (
                f"{wf_path.name}: node '{node.get('id')}' type "
                f"{node_type!r} not exported from programgarden_core"
            )
            model_fields = set(getattr(cls, "model_fields", {}))
            allowed_extras = _ALLOWED_NODE_EXTRAS.get(node_type, set())
            unknown = set(node) - _NODE_META_KEYS - model_fields - allowed_extras
            if unknown:
                offenders.append(
                    f"{node.get('id')} ({node_type}): {sorted(unknown)}"
                )

        assert not offenders, (
            f"{wf_path.name}: nodes reference fields absent from the node "
            f"schema (extra=\"allow\" hides these at runtime):\n"
            + "\n".join(f"  - {o}" for o in offenders)
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
