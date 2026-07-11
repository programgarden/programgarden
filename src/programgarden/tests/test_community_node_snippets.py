"""
트랙 B — programgarden-side community 노드 snippet validate.

community 는 core 에만 의존하므로 WorkflowExecutor(=programgarden 전용)를 import
할 수 없다. programgarden 은 community + WorkflowExecutor 둘 다 가용하므로, 등록
community 노드의 `_examples[].workflow_snippet` 전수를 실제 `WorkflowExecutor.validate()`
로 검증한다. validate() 는 정적 검증이라 heavy import(quantstats/pyportfolioopt)를
태우지 않는다 — 3.14.6 단일 인터프리터에서 실행 가능.

트랙 A(community-side)가 8 ClassVar 존재/shape 를, 트랙 B(여기)가 snippet 의
실제 유효성을 강제한다. PerformanceReportNode 신규 시 snippet 오류가 즉시 잡힌다.
"""

import pytest

from programgarden import WorkflowExecutor

# community 노드 등록 (플러그인은 programgarden import 시 자동, 노드는 명시 등록 필요)
import programgarden_community.nodes as community_nodes
from programgarden_community.nodes_registry import register_all_nodes

register_all_nodes()

NODE_CLASSES = [getattr(community_nodes, name) for name in community_nodes.__all__]

# (node_name, example_index, snippet) 평탄화
_SNIPPETS = []
for _cls in NODE_CLASSES:
    for _i, _ex in enumerate(getattr(_cls, "_examples", []) or []):
        _snip = _ex.get("workflow_snippet")
        if isinstance(_snip, dict):
            _SNIPPETS.append((f"{_cls.__name__}[{_i}]", _snip))


def test_snippets_exist():
    """등록 community 노드마다 최소 1개 snippet 이 수집되어야 한다."""
    covered = {name.split("[")[0] for name, _ in _SNIPPETS}
    exported = {c.__name__ for c in NODE_CLASSES}
    assert covered == exported, f"nodes with no validatable snippet: {exported - covered}"


@pytest.mark.parametrize("case_id,snippet", _SNIPPETS, ids=[s[0] for s in _SNIPPETS])
def test_snippet_validates(case_id, snippet):
    """각 community 노드 예제 snippet 이 WorkflowExecutor.validate() 를 errors 0 으로 통과."""
    executor = WorkflowExecutor()
    result = executor.validate(snippet)
    assert len(result.errors) == 0, (
        f"{case_id}: {len(result.errors)} validation error(s):\n"
        + "\n".join(f"  - {e}" for e in result.errors[:10])
    )
