"""v1.21.5 get_state() 진단 페이로드 데모.

자격증명 없이 실행 가능 (CodeNode 사용 + CodeNodeExecutor 강제 raise).
챗봇 sandbox / dry_run validator 가 받게 될 신규 진단 정보를 한눈에 확인.

실행:
    cd src/programgarden
    poetry run python examples/programmer_example/test_get_state_diagnostics_demo.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch


# 경로 설정
project_root = Path(__file__).parents[4]
sys.path.insert(0, str(project_root / "src" / "programgarden"))
sys.path.insert(0, str(project_root / "src" / "core"))
sys.path.insert(0, str(project_root / "src" / "community"))


from programgarden.executor import CodeNodeExecutor, WorkflowExecutor  # noqa: E402


# ============================================================
# Demo nodes (CodeNode)
# ============================================================


# Emits {'value': 100} on the declared 'value' port — no credentials needed.
_OK_CODE = (
    "async def execute(data, params, context):\n"
    "    return {'value': 100}"
)


def _ok(node_id: str) -> Dict[str, Any]:
    """A CodeNode that returns {'value': 100} on its 'value' output port."""
    return {
        "id": node_id,
        "type": "CodeNode",
        "outputs": [{"name": "value", "type": "number"}],
        "code": _OK_CODE,
    }


# ============================================================
# Helper
# ============================================================


def _summarize(state: Dict[str, Any], label: str) -> None:
    print(f"\n{'═' * 70}")
    print(f"  {label}")
    print(f"{'═' * 70}")
    print(f"  status                      = {state['status']}")
    print(f"  stats.errors_count          = {state['stats']['errors_count']}")
    print(f"  stats.last_error            = {state['stats'].get('last_error')!r}")

    detail = state["stats"].get("last_error_detail")
    if detail:
        print(f"  stats.last_error_detail     =")
        for k, v in detail.items():
            print(f"      .{k:<14} = {v!r}")
    else:
        print(f"  stats.last_error_detail     = {detail!r}")

    print(f"\n  nodes ({len(state['nodes'])}):")
    for node_id, entry in state["nodes"].items():
        extras = []
        if "error" in entry:
            extras.append(f"error={entry['error']!r}")
        if entry.get("duration_ms") is not None:
            extras.append(f"duration_ms={entry['duration_ms']:.1f}")
        extra_str = " | " + ", ".join(extras) if extras else ""
        print(f"    {node_id:<14} state={entry['state']:<10} type={entry['node_type']:<20}{extra_str}")

    print(f"\n  errors ({len(state['errors'])}):")
    if not state["errors"]:
        print(f"    (none — clean run)")
    for i, e in enumerate(state["errors"]):
        print(f"    [{i}] node_id={e['node_id']!r} type={e['node_type']!r}")
        print(f"        error={e['error']!r}")
        print(f"        timestamp={e['timestamp']!r}  level={e['level']!r}")


async def _run(executor: WorkflowExecutor, workflow: Dict[str, Any], *, fail_id: str = "", msg: str = ""):
    if fail_id:
        real_execute = CodeNodeExecutor.execute

        async def fake_execute(self, node_id, node_type, config, context, **kwargs):
            if node_id == fail_id:
                raise RuntimeError(msg)
            return await real_execute(self, node_id, node_type, config, context, **kwargs)

        with patch.object(CodeNodeExecutor, "execute", new=fake_execute):
            job = await executor.execute(workflow)
            try:
                await asyncio.wait_for(job._task, timeout=30.0)
            except asyncio.TimeoutError:
                await job.stop()
            return job
    else:
        job = await executor.execute(workflow)
        try:
            await asyncio.wait_for(job._task, timeout=30.0)
        except asyncio.TimeoutError:
            await job.stop()
        return job


# ============================================================
# Scenarios
# ============================================================


async def scenario_clean_run(executor: WorkflowExecutor) -> None:
    """모든 노드 정상 완료 — errors=[], last_error=None."""
    workflow = {
        "id": "demo-clean",
        "name": "Clean Run",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            _ok("node_a"),
            _ok("node_b"),
        ],
        "edges": [
            {"from": "start", "to": "node_a"},
            {"from": "node_a", "to": "node_b"},
        ],
    }
    job = await _run(executor, workflow)
    _summarize(job.get_state(), "Scenario 1: 정상 실행 (모든 노드 성공)")


async def scenario_node_failure(executor: WorkflowExecutor) -> None:
    """가운데 노드 fail — 진단 페이로드 풀세트."""
    workflow = {
        "id": "demo-fail",
        "name": "Node Failure",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            _ok("node_a"),
            _ok("node_b"),  # fail 강제
            _ok("node_c"),  # 미실행
            _ok("node_d"),  # 미실행
        ],
        "edges": [
            {"from": "start", "to": "node_a"},
            {"from": "node_a", "to": "node_b"},
            {"from": "node_b", "to": "node_c"},
            {"from": "node_c", "to": "node_d"},
        ],
    }
    job = await _run(
        executor, workflow,
        fail_id="node_b",
        msg="external API returned 500 — service degraded",
    )
    _summarize(job.get_state(), "Scenario 2: 노드 실패 (node_b fail, c/d 미실행)")


async def scenario_if_skipped(executor: WorkflowExecutor) -> None:
    """IfNode 비활성 브랜치 — D-8 SKIPPED 의미 정정."""
    workflow = {
        "id": "demo-if",
        "name": "IfNode Skipped",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "branch", "type": "IfNode", "left": 100, "operator": ">", "right": 50},
            _ok("true_path"),
            _ok("false_path"),
        ],
        "edges": [
            {"from": "start", "to": "branch"},
            {"from": "branch", "to": "true_path", "from_port": "true"},
            {"from": "branch", "to": "false_path", "from_port": "false"},
        ],
    }
    job = await _run(executor, workflow)
    _summarize(job.get_state(), "Scenario 3: IfNode 분기 (false_path SKIPPED 의미 정정)")


# ============================================================
# Main
# ============================================================


async def main() -> None:
    print("=" * 70)
    print("  v1.21.5 get_state() 진단 페이로드 데모")
    print("  외부 챗봇 sandbox / dry_run validator 가 받는 응답 schema")
    print("=" * 70)

    executor = WorkflowExecutor()

    await scenario_clean_run(executor)
    await scenario_node_failure(executor)
    await scenario_if_skipped(executor)

    print(f"\n{'═' * 70}")
    print("  완료. 신규 키 노출 확인됨:")
    print("    - state['errors'] (구조화 root cause)")
    print("    - state['nodes'][id]['state' / 'error' / 'duration_ms' / 'node_type']")
    print("    - state['stats']['last_error' / 'last_error_detail']")
    print(f"{'═' * 70}")


if __name__ == "__main__":
    asyncio.run(main())
