"""
WorkflowDefinition DAG 순환 참조 검증 테스트
"""

import pytest
from programgarden_core.models.workflow import WorkflowDefinition
from programgarden_core.models.edge import Edge


def make_edge(from_node: str, to_node: str) -> Edge:
    """테스트용 Edge 생성 헬퍼"""
    return Edge(**{"from": from_node, "to": to_node})


class TestDAGValidation:
    """DAG 순환 참조 검증 테스트"""

    def test_valid_dag_no_cycle(self):
        """정상 DAG - 순환 없음"""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "broker", "type": "BrokerNode"},
                {"id": "condition", "type": "ConditionNode"},
                {"id": "order", "type": "NewOrderNode"},
            ],
            edges=[
                make_edge("start", "broker"),
                make_edge("broker", "condition"),
                make_edge("condition", "order"),
            ],
        )

        errors = workflow.validate_structure()
        cycle_errors = [e for e in errors if "Circular reference" in e or "순환 참조" in e]
        assert len(cycle_errors) == 0

    def test_direct_cycle_two_nodes(self):
        """직접 순환 - A → B → A"""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "a", "type": "ConditionNode"},
                {"id": "b", "type": "ConditionNode"},
            ],
            edges=[
                make_edge("start", "a"),
                make_edge("a", "b"),
                make_edge("b", "a"),  # 순환!
            ],
        )

        errors = workflow.validate_structure()
        cycle_errors = [e for e in errors if "Circular reference" in e or "순환 참조" in e]
        assert len(cycle_errors) == 1
        assert "a" in cycle_errors[0]
        assert "b" in cycle_errors[0]

    def test_indirect_cycle_three_nodes(self):
        """간접 순환 - A → B → C → A"""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "a", "type": "ConditionNode"},
                {"id": "b", "type": "ConditionNode"},
                {"id": "c", "type": "ConditionNode"},
            ],
            edges=[
                make_edge("start", "a"),
                make_edge("a", "b"),
                make_edge("b", "c"),
                make_edge("c", "a"),  # 순환!
            ],
        )

        errors = workflow.validate_structure()
        cycle_errors = [e for e in errors if "Circular reference" in e or "순환 참조" in e]
        assert len(cycle_errors) == 1
        # 순환 경로에 a, b, c 모두 포함
        assert "a" in cycle_errors[0]
        assert "b" in cycle_errors[0]
        assert "c" in cycle_errors[0]

    def test_self_reference_cycle(self):
        """자기 참조 - A → A"""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "loop", "type": "ConditionNode"},
            ],
            edges=[
                make_edge("start", "loop"),
                make_edge("loop", "loop"),  # 자기 참조!
            ],
        )

        errors = workflow.validate_structure()
        cycle_errors = [e for e in errors if "Circular reference" in e or "순환 참조" in e]
        assert len(cycle_errors) == 1
        assert "loop" in cycle_errors[0]

    def test_complex_graph_with_cycle(self):
        """복잡한 그래프 - 다중 경로 중 일부만 순환"""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "a", "type": "ConditionNode"},
                {"id": "b", "type": "ConditionNode"},
                {"id": "c", "type": "ConditionNode"},
                {"id": "d", "type": "ConditionNode"},
                {"id": "end", "type": "NewOrderNode"},
            ],
            edges=[
                make_edge("start", "a"),
                make_edge("a", "b"),
                make_edge("a", "c"),
                make_edge("b", "d"),
                make_edge("c", "d"),
                make_edge("d", "b"),  # 순환! b → d → b
                make_edge("d", "end"),
            ],
        )

        errors = workflow.validate_structure()
        cycle_errors = [e for e in errors if "Circular reference" in e or "순환 참조" in e]
        assert len(cycle_errors) == 1

    def test_complex_graph_no_cycle(self):
        """복잡한 그래프 - 다중 경로, 순환 없음"""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "a", "type": "ConditionNode"},
                {"id": "b", "type": "ConditionNode"},
                {"id": "c", "type": "ConditionNode"},
                {"id": "d", "type": "ConditionNode"},
                {"id": "end", "type": "NewOrderNode"},
            ],
            edges=[
                make_edge("start", "a"),
                make_edge("a", "b"),
                make_edge("a", "c"),
                make_edge("b", "d"),
                make_edge("c", "d"),
                make_edge("d", "end"),
            ],
        )

        errors = workflow.validate_structure()
        cycle_errors = [e for e in errors if "Circular reference" in e or "순환 참조" in e]
        assert len(cycle_errors) == 0

    def test_disconnected_components_with_cycle(self):
        """분리된 컴포넌트 - 일부에 순환 있음"""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "a", "type": "ConditionNode"},
                # 분리된 컴포넌트 (순환)
                {"id": "x", "type": "ConditionNode"},
                {"id": "y", "type": "ConditionNode"},
            ],
            edges=[
                make_edge("start", "a"),
                # 분리된 컴포넌트의 순환
                make_edge("x", "y"),
                make_edge("y", "x"),  # 순환!
            ],
        )

        errors = workflow.validate_structure()
        cycle_errors = [e for e in errors if "Circular reference" in e or "순환 참조" in e]
        assert len(cycle_errors) == 1
        assert "x" in cycle_errors[0]
        assert "y" in cycle_errors[0]

    def test_detect_cycle_returns_path(self):
        """_detect_cycle()이 순환 경로를 정확히 반환하는지"""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "a", "type": "ConditionNode"},
                {"id": "b", "type": "ConditionNode"},
            ],
            edges=[
                make_edge("start", "a"),
                make_edge("a", "b"),
                make_edge("b", "a"),
            ],
        )

        cycle = workflow._detect_cycle()
        assert cycle is not None
        # 순환 경로는 시작과 끝이 같아야 함
        assert cycle[0] == cycle[-1]
        # 경로에 순환 노드들 포함
        assert "a" in cycle
        assert "b" in cycle

    def test_detect_cycle_returns_none_for_valid_dag(self):
        """_detect_cycle()이 유효한 DAG에서 None 반환"""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "end", "type": "NewOrderNode"},
            ],
            edges=[
                make_edge("start", "end"),
            ],
        )

        cycle = workflow._detect_cycle()
        assert cycle is None

    def test_long_cycle_five_nodes(self):
        """긴 순환 - A → B → C → D → E → A (5개 노드)"""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "a", "type": "ConditionNode"},
                {"id": "b", "type": "ConditionNode"},
                {"id": "c", "type": "ConditionNode"},
                {"id": "d", "type": "ConditionNode"},
                {"id": "e", "type": "ConditionNode"},
            ],
            edges=[
                make_edge("start", "a"),
                make_edge("a", "b"),
                make_edge("b", "c"),
                make_edge("c", "d"),
                make_edge("d", "e"),
                make_edge("e", "a"),  # 순환! 5개 노드
            ],
        )

        errors = workflow.validate_structure()
        cycle_errors = [e for e in errors if "Circular reference" in e or "순환 참조" in e]
        assert len(cycle_errors) == 1
        # 모든 순환 노드가 포함되어야 함
        assert "a" in cycle_errors[0]
        assert "b" in cycle_errors[0]
        assert "e" in cycle_errors[0]

    def test_very_long_cycle_ten_nodes(self):
        """매우 긴 순환 - 10개 노드"""
        nodes = [{"id": "start", "type": "StartNode"}]
        nodes += [{"id": f"n{i}", "type": "ConditionNode"} for i in range(10)]
        
        edges = [make_edge("start", "n0")]
        edges += [make_edge(f"n{i}", f"n{i+1}") for i in range(9)]
        edges.append(make_edge("n9", "n0"))  # 순환! n0 → n1 → ... → n9 → n0

        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            nodes=nodes,
            edges=edges,
        )

        cycle = workflow._detect_cycle()
        assert cycle is not None
        assert cycle[0] == cycle[-1]  # 시작과 끝이 같음
        assert len(cycle) == 11  # 10개 노드 + 시작점 반복

    def test_multiple_separate_cycles(self):
        """여러 개의 분리된 순환 - 첫 번째만 탐지"""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            nodes=[
                {"id": "start", "type": "StartNode"},
                # 첫 번째 순환
                {"id": "a1", "type": "ConditionNode"},
                {"id": "a2", "type": "ConditionNode"},
                # 두 번째 순환
                {"id": "b1", "type": "ConditionNode"},
                {"id": "b2", "type": "ConditionNode"},
            ],
            edges=[
                make_edge("start", "a1"),
                # 첫 번째 순환
                make_edge("a1", "a2"),
                make_edge("a2", "a1"),
                # 두 번째 순환
                make_edge("b1", "b2"),
                make_edge("b2", "b1"),
            ],
        )

        errors = workflow.validate_structure()
        cycle_errors = [e for e in errors if "Circular reference" in e or "순환 참조" in e]
        # 최소 하나의 순환이 탐지되어야 함
        assert len(cycle_errors) >= 1

    def test_nested_structure_no_cycle(self):
        """중첩 구조 - 순환 없음 (다이아몬드 패턴)"""
        workflow = WorkflowDefinition(
            id="test-workflow",
            name="Test Workflow",
            nodes=[
                {"id": "start", "type": "StartNode"},
                {"id": "a", "type": "ConditionNode"},
                {"id": "b", "type": "ConditionNode"},
                {"id": "c", "type": "ConditionNode"},
                {"id": "d", "type": "ConditionNode"},
            ],
            edges=[
                make_edge("start", "a"),
                make_edge("a", "b"),
                make_edge("a", "c"),
                make_edge("b", "d"),
                make_edge("c", "d"),  # 다이아몬드 패턴, 순환 아님
            ],
        )

        cycle = workflow._detect_cycle()
        assert cycle is None
