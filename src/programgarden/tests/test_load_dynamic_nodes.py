"""
load_dynamic_nodes() + execute() 자동 감지 테스트

WorkflowExecutor.load_dynamic_nodes()와
execute() 내 dynamic_nodes 자동 로드 기능을 검증합니다.
"""

import pytest
import asyncio
from typing import Dict, Any, List

from programgarden.executor import WorkflowExecutor, GenericNodeExecutor
from programgarden.context import ExecutionContext
from programgarden_core.registry import DynamicNodeRegistry


# ─────────────────────────────────────────────────
# 테스트용 코드 문자열 상수
# ─────────────────────────────────────────────────

# Dynamic_MyRSI 노드 코드
RSI_NODE_CODE = (
    "from programgarden_core.nodes.base import BaseNode, NodeCategory, OutputPort\n"
    "from typing import List\n"
    "\n"
    "class MyRSINode(BaseNode):\n"
    "    type: str = 'Dynamic_MyRSI'\n"
    "    category: NodeCategory = NodeCategory.CONDITION\n"
    "    period: int = 14\n"
    "    _outputs: List[OutputPort] = [\n"
    "        OutputPort(name='rsi', type='number'),\n"
    "        OutputPort(name='signal', type='string'),\n"
    "    ]\n"
    "\n"
    "    async def execute(self, context):\n"
    "        return {'rsi': 35.5, 'signal': 'oversold'}\n"
)

# Dynamic_MyMACD 노드 코드
MACD_NODE_CODE = (
    "from programgarden_core.nodes.base import BaseNode, NodeCategory, OutputPort\n"
    "from typing import List\n"
    "\n"
    "class MyMACDNode(BaseNode):\n"
    "    type: str = 'Dynamic_MyMACD'\n"
    "    category: NodeCategory = NodeCategory.CONDITION\n"
    "    fast_period: int = 12\n"
    "    slow_period: int = 26\n"
    "    _outputs: List[OutputPort] = [\n"
    "        OutputPort(name='macd', type='number'),\n"
    "        OutputPort(name='signal_line', type='number'),\n"
    "    ]\n"
    "\n"
    "    async def execute(self, context):\n"
    "        return {'macd': 1.23, 'signal_line': 1.10}\n"
)

# 타입 불일치 노드 코드 (dynamic_type과 실제 type 값이 다름)
MISMATCHED_NODE_CODE = (
    "from programgarden_core.nodes.base import BaseNode, NodeCategory, OutputPort\n"
    "from typing import List\n"
    "\n"
    "class WrongTypeNode(BaseNode):\n"
    "    type: str = 'Dynamic_WrongType'\n"
    "    category: NodeCategory = NodeCategory.CONDITION\n"
    "    _outputs: List[OutputPort] = []\n"
    "\n"
    "    async def execute(self, context):\n"
    "        return {}\n"
)


# ─────────────────────────────────────────────────
# Payload 헬퍼
# ─────────────────────────────────────────────────

def make_rsi_payload(dynamic_type: str = "Dynamic_MyRSI") -> Dict[str, Any]:
    return {
        "dynamic_type": dynamic_type,
        "dynamic_node_code": RSI_NODE_CODE,
        "category": "condition",
        "outputs": [
            {"name": "rsi", "type": "number"},
            {"name": "signal", "type": "string"},
        ],
    }


def make_macd_payload() -> Dict[str, Any]:
    return {
        "dynamic_type": "Dynamic_MyMACD",
        "dynamic_node_code": MACD_NODE_CODE,
        "category": "condition",
        "outputs": [
            {"name": "macd", "type": "number"},
            {"name": "signal_line", "type": "number"},
        ],
    }


# ─────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_registry():
    """각 테스트 전후 레지스트리 초기화."""
    DynamicNodeRegistry.reset_instance()
    yield
    DynamicNodeRegistry.reset_instance()


@pytest.fixture
def executor():
    """WorkflowExecutor 인스턴스."""
    return WorkflowExecutor()


@pytest.fixture
def simple_workflow_with_dynamic_rsi():
    """Dynamic_MyRSI를 포함하는 단순 워크플로우."""
    return {
        "id": "test-dynamic-workflow",
        "name": "Dynamic RSI Workflow",
        "nodes": [
            {"id": "start", "type": "StartNode"},
            {"id": "rsi", "type": "Dynamic_MyRSI", "period": 14},
        ],
        "edges": [
            {"from": "start", "to": "rsi"},
        ],
        "credentials": [],
    }


# ─────────────────────────────────────────────────
# 테스트 1: load_dynamic_nodes 단위 테스트
# ─────────────────────────────────────────────────

class TestLoadDynamicNodes:
    """WorkflowExecutor.load_dynamic_nodes() 단위 테스트."""

    def test_load_single_node_returns_one(self, executor):
        """정상 코드 1개 로드 → 반환값 1, is_dynamic_node_ready True."""
        loaded = executor.load_dynamic_nodes([make_rsi_payload()])

        assert loaded == 1, f"로드 수 불일치: 기대 1, 실제 {loaded}"
        assert executor.is_dynamic_node_ready("Dynamic_MyRSI"), (
            "Dynamic_MyRSI가 실행 준비 완료 상태여야 함"
        )

    def test_load_multiple_nodes_returns_count(self, executor):
        """2개 동시 로드 → 반환값 2, 둘 다 ready."""
        loaded = executor.load_dynamic_nodes([
            make_rsi_payload(),
            make_macd_payload(),
        ])

        assert loaded == 2, f"로드 수 불일치: 기대 2, 실제 {loaded}"
        assert executor.is_dynamic_node_ready("Dynamic_MyRSI"), (
            "Dynamic_MyRSI ready 실패"
        )
        assert executor.is_dynamic_node_ready("Dynamic_MyMACD"), (
            "Dynamic_MyMACD ready 실패"
        )

    def test_load_empty_list_returns_zero(self, executor):
        """빈 리스트 → 반환값 0, 예외 없음."""
        loaded = executor.load_dynamic_nodes([])

        assert loaded == 0, f"빈 리스트는 0 반환해야 함, 실제: {loaded}"

    def test_missing_dynamic_type_raises_value_error(self, executor):
        """dynamic_type 누락 → ValueError."""
        payload_no_type = {
            # dynamic_type 없음
            "dynamic_node_code": RSI_NODE_CODE,
            "category": "condition",
            "outputs": [{"name": "rsi", "type": "number"}],
        }

        with pytest.raises(ValueError, match="dynamic_type"):
            executor.load_dynamic_nodes([payload_no_type])

    def test_missing_dynamic_node_code_raises_value_error(self, executor):
        """dynamic_node_code 누락 → ValueError."""
        payload_no_code = {
            "dynamic_type": "Dynamic_MyRSI",
            # dynamic_node_code 없음
            "category": "condition",
            "outputs": [{"name": "rsi", "type": "number"}],
        }

        with pytest.raises(ValueError, match="dynamic_type"):
            executor.load_dynamic_nodes([payload_no_code])

    def test_type_mismatch_in_code_raises_value_error(self, executor):
        """코드의 type 값이 dynamic_type과 불일치 → ValueError."""
        payload_mismatch = {
            "dynamic_type": "Dynamic_MyRSI",  # 요청 타입
            "dynamic_node_code": MISMATCHED_NODE_CODE,  # 실제 코드는 Dynamic_WrongType
            "category": "condition",
            "outputs": [],
        }

        with pytest.raises(ValueError, match="BaseNode"):
            executor.load_dynamic_nodes([payload_mismatch])

    @pytest.mark.asyncio
    async def test_load_then_execute_via_generic_executor(self, executor):
        """load_dynamic_nodes 후 GenericNodeExecutor로 실행 → 결과 검증."""
        executor.load_dynamic_nodes([make_rsi_payload()])

        context = ExecutionContext(
            job_id="test-job-load",
            workflow_id="test-workflow-load",
        )

        node_executor = GenericNodeExecutor()
        result = await node_executor.execute(
            node_id="rsi-node",
            node_type="Dynamic_MyRSI",
            config={"period": 14},
            context=context,
        )

        assert "error" not in result, f"예상치 못한 에러: {result.get('error')}"
        assert result["rsi"] == 35.5, f"rsi 값 불일치: {result.get('rsi')}"
        assert result["signal"] == "oversold", f"signal 값 불일치: {result.get('signal')}"

    def test_loaded_nodes_appear_in_list(self, executor):
        """load_dynamic_nodes 후 list_dynamic_node_types에 포함됨."""
        executor.load_dynamic_nodes([
            make_rsi_payload(),
            make_macd_payload(),
        ])

        types = executor.list_dynamic_node_types()
        assert "Dynamic_MyRSI" in types, "Dynamic_MyRSI가 목록에 없음"
        assert "Dynamic_MyMACD" in types, "Dynamic_MyMACD가 목록에 없음"

    def test_clear_after_load_removes_classes(self, executor):
        """load 후 clear_injected_classes → is_dynamic_node_ready False."""
        executor.load_dynamic_nodes([make_rsi_payload()])
        assert executor.is_dynamic_node_ready("Dynamic_MyRSI")

        executor.clear_injected_classes()

        assert not executor.is_dynamic_node_ready("Dynamic_MyRSI"), (
            "clear 후에는 ready가 False여야 함"
        )
        # 스키마는 남아 있어야 함
        assert "Dynamic_MyRSI" in executor.list_dynamic_node_types(), (
            "clear 후에도 스키마는 유지되어야 함"
        )


# ─────────────────────────────────────────────────
# 테스트 2: execute() dynamic_nodes 자동 감지
# ─────────────────────────────────────────────────

class TestExecuteAutoDetectDynamicNodes:
    """execute() 내 dynamic_nodes 자동 로드 기능 테스트."""

    @pytest.mark.asyncio
    async def test_execute_with_dynamic_nodes_key(
        self, executor, simple_workflow_with_dynamic_rsi
    ):
        """definition에 dynamic_nodes 포함 시 execute()만 호출해도 실행됨."""
        # dynamic_nodes 키를 워크플로우 definition에 직접 포함
        workflow_with_dynamic_nodes = {
            **simple_workflow_with_dynamic_rsi,
            "dynamic_nodes": [make_rsi_payload()],
        }

        # execute() 호출 전 아직 등록 안 됨
        assert not executor.is_dynamic_node_ready("Dynamic_MyRSI"), (
            "execute() 전에는 ready 상태가 아니어야 함"
        )

        job = await executor.execute(workflow_with_dynamic_nodes)

        assert job is not None, "job 객체가 None이면 안 됨"
        assert job.job_id is not None, "job_id가 None이면 안 됨"

        await job.stop()
        executor.clear_injected_classes()

    @pytest.mark.asyncio
    async def test_execute_without_dynamic_nodes_key(self, executor):
        """definition에 dynamic_nodes 없으면 기존 동작 그대로."""
        plain_workflow = {
            "id": "plain-workflow",
            "name": "Plain Workflow",
            "nodes": [
                {"id": "start", "type": "StartNode"},
            ],
            "edges": [],
            "credentials": [],
            # dynamic_nodes 키 없음
        }

        # dynamic_nodes 없어도 정상 실행
        job = await executor.execute(plain_workflow)

        assert job is not None, "일반 워크플로우 job이 None이면 안 됨"
        assert job.job_id is not None

        await job.stop()

    @pytest.mark.asyncio
    async def test_execute_dynamic_nodes_auto_loaded_before_compile(
        self, executor, simple_workflow_with_dynamic_rsi
    ):
        """execute() 내부에서 compile 전에 dynamic_nodes가 로드되는지 확인."""
        # 스키마 미등록 상태에서 validate()는 실패해야 함
        validation_before = executor.validate(simple_workflow_with_dynamic_rsi)
        assert not validation_before.is_valid, (
            "스키마 미등록 시 validation이 실패해야 함"
        )

        # dynamic_nodes 포함 workflow는 execute()가 자동으로 로드하므로 성공
        workflow_with_dynamic_nodes = {
            **simple_workflow_with_dynamic_rsi,
            "dynamic_nodes": [make_rsi_payload()],
        }

        # execute()가 내부에서 load_dynamic_nodes 후 compile하므로 ValueError 없이 진행
        job = await executor.execute(workflow_with_dynamic_nodes)
        assert job is not None

        await job.stop()
        executor.clear_injected_classes()

    @pytest.mark.asyncio
    async def test_execute_dynamic_nodes_multiple(self, executor):
        """execute() definition에 여러 동적 노드 포함 시 모두 로드됨."""
        workflow_multi = {
            "id": "multi-dynamic-workflow",
            "name": "Multi Dynamic Workflow",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {"id": "rsi", "type": "Dynamic_MyRSI"},
                {"id": "macd", "type": "Dynamic_MyMACD"},
            ],
            "edges": [
                {"from": "start", "to": "rsi"},
                {"from": "start", "to": "macd"},
            ],
            "credentials": [],
            "dynamic_nodes": [
                make_rsi_payload(),
                make_macd_payload(),
            ],
        }

        job = await executor.execute(workflow_multi)

        assert job is not None
        # 두 타입 모두 로드되었는지 확인
        assert executor.is_dynamic_node_ready("Dynamic_MyRSI"), (
            "Dynamic_MyRSI ready 실패"
        )
        assert executor.is_dynamic_node_ready("Dynamic_MyMACD"), (
            "Dynamic_MyMACD ready 실패"
        )

        await job.stop()
        executor.clear_injected_classes()
