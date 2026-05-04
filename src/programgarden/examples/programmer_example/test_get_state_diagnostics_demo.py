"""v1.21.5 get_state() 진단 페이로드 데모.

자격증명 없이 실행 가능 (Dynamic_ 노드 사용 + GenericNodeExecutor 강제 raise).
챗봇 sandbox / dry_run validator 가 받게 될 신규 진단 정보를 한눈에 확인.

실행:
    cd src/programgarden
    poetry run python examples/programmer_example/test_get_state_diagnostics_demo.py
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch


# 경로 설정
project_root = Path(__file__).parents[4]
sys.path.insert(0, str(project_root / "src" / "programgarden"))
sys.path.insert(0, str(project_root / "src" / "core"))
sys.path.insert(0, str(project_root / "src" / "community"))


from programgarden.executor import GenericNodeExecutor, WorkflowExecutor  # noqa: E402
from programgarden_core.nodes.base import (  # noqa: E402
    BaseNode,
    NodeCategory,
    OutputPort,
)


# ============================================================
# Demo nodes
# ============================================================


class DemoOkNode(BaseNode):
    type: str = "Dynamic_DemoOk"
    category: NodeCategory = NodeCategory.CONDITION
    label: str = "ok"
    _outputs: List[OutputPort] = [OutputPort(name="value", type="number")]

    async def execute(self, context) -> Dict[str, Any]:
        return {"value": 100}


class DemoFailNode(BaseNode):
    type: str = "Dynamic_DemoFail"
    category: NodeCategory = NodeCategory.CONDITION
    _outputs: List[OutputPort] = [OutputPort(name="value", type="number")]

    async def execute(self, context) -> Dict[str, Any]:
        return {"value": 0}


SCHEMAS = [
    {"node_type": "Dynamic_DemoOk", "category": "condition",
     "outputs": [{"name": "value", "type": "number"}]},
    {"node_type": "Dynamic_DemoFail", "category": "condition",
     "outputs": [{"name": "value", "type": "number"}]},
]
CLASSES = {"Dynamic_DemoOk": DemoOkNode, "Dynamic_DemoFail": DemoFailNode}


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
        real_execute = GenericNodeExecutor.execute

        async def fake_execute(self, node_id, node_type, config, context, **kwargs):
            if node_id == fail_id:
                raise RuntimeError(msg)
            return await real_execute(self, node_id, node_type, config, context, **kwargs)

        with patch.object(GenericNodeExecutor, "execute", new=fake_execute):
            job = await executor.execute(workflow)
            try:
                await asyncio.wait_for(job._task, timeout=5.0)
            except asyncio.TimeoutError:
                await job.stop()
            return job
    else:
        job = await executor.execute(workflow)
        try:
            await asyncio.wait_for(job._task, timeout=5.0)
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
            {"id": "node_a", "type": "Dynamic_DemoOk"},
            {"id": "node_b", "type": "Dynamic_DemoOk"},
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
            {"id": "node_a", "type": "Dynamic_DemoOk"},
            {"id": "node_b", "type": "Dynamic_DemoOk"},  # fail 강제
            {"id": "node_c", "type": "Dynamic_DemoOk"},  # 미실행
            {"id": "node_d", "type": "Dynamic_DemoOk"},  # 미실행
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
            {"id": "true_path", "type": "Dynamic_DemoOk", "label": "executed"},
            {"id": "false_path", "type": "Dynamic_DemoOk", "label": "skipped"},
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
    executor.register_dynamic_schemas(SCHEMAS)
    executor.inject_node_classes(CLASSES)

    try:
        await scenario_clean_run(executor)
        await scenario_node_failure(executor)
        await scenario_if_skipped(executor)
    finally:
        executor.clear_injected_classes()

    print(f"\n{'═' * 70}")
    print("  완료. 신규 키 노출 확인됨:")
    print("    - state['errors'] (구조화 root cause)")
    print("    - state['nodes'][id]['state' / 'error' / 'duration_ms' / 'node_type']")
    print("    - state['stats']['last_error' / 'last_error_detail']")
    print(f"{'═' * 70}")


if __name__ == "__main__":
    asyncio.run(main())
