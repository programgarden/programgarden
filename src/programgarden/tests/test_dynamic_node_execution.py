"""
동적 노드 실행 통합 테스트

WorkflowExecutor를 통한 동적 노드 등록, 주입, 실행 테스트
"""

import pytest
from typing import Dict, Any, List

from programgarden.executor import WorkflowExecutor, GenericNodeExecutor
from programgarden.resolver import WorkflowResolver
from programgarden.context import ExecutionContext
from programgarden_core.registry import (
    DynamicNodeRegistry,
    DynamicNodeSchema,
)
from programgarden_core.nodes.base import BaseNode, NodeCategory, OutputPort, InputPort


# ─────────────────────────────────────────────────
# 테스트용 노드 클래스
# ─────────────────────────────────────────────────

class DynamicRSINode(BaseNode):
    """테스트용 RSI 노드"""
    type: str = "Dynamic_RSI"
    category: NodeCategory = NodeCategory.CONDITION
    period: int = 14

    _inputs: List[InputPort] = [
        InputPort(name="data", type="array", required=True),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="rsi", type="number"),
        OutputPort(name="signal", type="string"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        return {
            "rsi": 35.5,
            "signal": "oversold",
        }


class DynamicMACDNode(BaseNode):
    """테스트용 MACD 노드"""
    type: str = "Dynamic_MACD"
    category: NodeCategory = NodeCategory.CONDITION
    fast_period: int = 12
    slow_period: int = 26

    _outputs: List[OutputPort] = [
        OutputPort(name="macd", type="number"),
        OutputPort(name="signal_line", type="number"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        return {
            "macd": 1.23,
            "signal_line": 1.10,
        }


# ─────────────────────────────────────────────────
# Fixture
# ─────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_registry():
    """각 테스트 전후 레지스트리 초기화"""
    DynamicNodeRegistry.reset_instance()
    yield
    DynamicNodeRegistry.reset_instance()


@pytest.fixture
def executor():
    """WorkflowExecutor 인스턴스"""
    return WorkflowExecutor()


@pytest.fixture
def sample_schemas():
    """테스트용 스키마 목록"""
    return [
        {
            "node_type": "Dynamic_RSI",
            "category": "condition",
            "description": "동적 RSI 지표",
            "inputs": [{"name": "data", "type": "array", "required": True}],
            "outputs": [
                {"name": "rsi", "type": "number"},
                {"name": "signal", "type": "string"},
            ],
        },
        {
            "node_type": "Dynamic_MACD",
            "category": "condition",
            "description": "동적 MACD 지표",
            "outputs": [
                {"name": "macd", "type": "number"},
                {"name": "signal_line", "type": "number"},
            ],
        },
    ]


@pytest.fixture
def workflow_with_custom_node():
    """동적 노드를 포함한 워크플로우"""
    return {
        "id": "test-workflow",
        "name": "Test Workflow",
        "version": "1.0.0",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "custom", "type": "Dynamic_RSI", "period": 14},
        ],
        "edges": [
            {"from": "start", "to": "custom"},
        ],
    }


# ─────────────────────────────────────────────────
# WorkflowExecutor API 테스트
# ─────────────────────────────────────────────────

class TestWorkflowExecutorDynamicAPI:
    """WorkflowExecutor 동적 노드 API 테스트"""

    def test_register_dynamic_schemas(self, executor, sample_schemas):
        """스키마 등록"""
        executor.register_dynamic_schemas(sample_schemas)

        assert "Dynamic_RSI" in executor.list_dynamic_node_types()
        assert "Dynamic_MACD" in executor.list_dynamic_node_types()

    def test_get_required_dynamic_types(self, executor, workflow_with_custom_node, sample_schemas):
        """필요한 동적 타입 목록 반환"""
        required = executor.get_required_dynamic_types(workflow_with_custom_node)

        assert "Dynamic_RSI" in required
        assert "StartNode" not in required  # 일반 노드는 포함 안 됨

    def test_get_required_dynamic_types_empty(self, executor):
        """동적 노드 없는 워크플로우"""
        workflow = {
            "nodes": [
                {"id": "start", "type": "StartNode"},
            ]
        }
        required = executor.get_required_dynamic_types(workflow)
        assert required == []

    def test_inject_node_classes(self, executor, sample_schemas):
        """클래스 주입"""
        executor.register_dynamic_schemas(sample_schemas)
        executor.inject_node_classes({
            "Dynamic_RSI": DynamicRSINode,
            "Dynamic_MACD": DynamicMACDNode,
        })

        assert executor.is_dynamic_node_ready("Dynamic_RSI")
        assert executor.is_dynamic_node_ready("Dynamic_MACD")

    def test_is_dynamic_node_ready_false(self, executor, sample_schemas):
        """클래스 미주입 시 준비 안 됨"""
        executor.register_dynamic_schemas(sample_schemas)

        # 스키마만 등록, 클래스 미주입
        assert not executor.is_dynamic_node_ready("Dynamic_RSI")

    def test_clear_injected_classes(self, executor, sample_schemas):
        """클래스 초기화"""
        executor.register_dynamic_schemas(sample_schemas)
        executor.inject_node_classes({"Dynamic_RSI": DynamicRSINode})

        executor.clear_injected_classes()

        # 스키마는 유지
        assert "Dynamic_RSI" in executor.list_dynamic_node_types()
        # 클래스는 제거
        assert not executor.is_dynamic_node_ready("Dynamic_RSI")


# ─────────────────────────────────────────────────
# WorkflowResolver 검증 테스트
# ─────────────────────────────────────────────────

class TestWorkflowResolverValidation:
    """WorkflowResolver 동적 노드 검증 테스트"""

    def test_validate_with_registered_schema(self, executor, sample_schemas, workflow_with_custom_node):
        """스키마 등록된 동적 노드는 검증 통과"""
        executor.register_dynamic_schemas(sample_schemas)

        result = executor.validate(workflow_with_custom_node)

        assert result.is_valid

    def test_validate_without_schema_fails(self, executor, workflow_with_custom_node):
        """스키마 미등록 동적 노드는 검증 실패"""
        # 스키마 등록 안 함

        result = executor.validate(workflow_with_custom_node)

        assert not result.is_valid
        assert any("schema not registered" in e for e in result.errors)

    def test_validate_credential_id_blocked(self, executor, sample_schemas):
        """동적 노드의 credential_id 사용 차단"""
        executor.register_dynamic_schemas(sample_schemas)

        workflow = {
            "id": "test",
            "name": "Test",
            "version": "1.0.0",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {"id": "custom", "type": "Dynamic_RSI", "credential_id": "my-cred"},
            ],
            "edges": [{"from": "start", "to": "custom"}],
        }

        result = executor.validate(workflow)

        assert not result.is_valid
        assert any("cannot use credential_id" in e for e in result.errors)


# ─────────────────────────────────────────────────
# GenericNodeExecutor 테스트
# ─────────────────────────────────────────────────

class TestGenericNodeExecutorDynamic:
    """GenericNodeExecutor 동적 노드 실행 테스트"""

    @pytest.mark.asyncio
    async def test_execute_dynamic_node(self, executor, sample_schemas):
        """동적 노드 실행 성공"""
        executor.register_dynamic_schemas(sample_schemas)
        executor.inject_node_classes({"Dynamic_RSI": DynamicRSINode})

        # Context 생성
        context = ExecutionContext(
            job_id="test-job",
            workflow_id="test-workflow",
        )

        # GenericNodeExecutor로 실행
        node_executor = GenericNodeExecutor()
        result = await node_executor.execute(
            node_id="custom",
            node_type="Dynamic_RSI",
            config={"period": 14},
            context=context,
        )

        # 에러가 없어야 함
        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert result["rsi"] == 35.5
        assert result["signal"] == "oversold"

    @pytest.mark.asyncio
    async def test_execute_without_class_injection_fails(self, executor, sample_schemas):
        """클래스 미주입 시 실행 실패"""
        executor.register_dynamic_schemas(sample_schemas)
        # 클래스 주입 안 함

        context = ExecutionContext(
            job_id="test-job",
            workflow_id="test-workflow",
        )

        node_executor = GenericNodeExecutor()
        result = await node_executor.execute(
            node_id="custom",
            node_type="Dynamic_RSI",
            config={},
            context=context,
        )

        assert "error" in result
        assert "주입되지 않음" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_unknown_node_type_fails(self, executor):
        """알 수 없는 노드 타입 실행 실패"""
        context = ExecutionContext(
            job_id="test-job",
            workflow_id="test-workflow",
        )

        node_executor = GenericNodeExecutor()
        result = await node_executor.execute(
            node_id="unknown",
            node_type="Dynamic_Unknown",
            config={},
            context=context,
        )

        assert "error" in result
        assert "Unknown node type" in result["error"]


# ─────────────────────────────────────────────────
# 전체 워크플로우 통합 테스트
# ─────────────────────────────────────────────────

class TestFullWorkflowExecution:
    """전체 워크플로우 실행 통합 테스트"""

    @pytest.mark.asyncio
    async def test_execute_workflow_with_dynamic_node(self, executor, sample_schemas, workflow_with_custom_node):
        """동적 노드 포함 워크플로우 실행"""
        # 1. 스키마 등록
        executor.register_dynamic_schemas(sample_schemas)

        # 2. 필요한 타입 확인
        required = executor.get_required_dynamic_types(workflow_with_custom_node)
        assert "Dynamic_RSI" in required

        # 3. 클래스 주입
        executor.inject_node_classes({"Dynamic_RSI": DynamicRSINode})

        # 4. 검증
        validation = executor.validate(workflow_with_custom_node)
        assert validation.is_valid

        # 5. 실행 (Job 생성만 - 실제 실행은 복잡하므로 생략)
        job = await executor.execute(workflow_with_custom_node)
        assert job is not None
        assert job.job_id is not None

        # 6. 정리
        await job.stop()
        executor.clear_injected_classes()
