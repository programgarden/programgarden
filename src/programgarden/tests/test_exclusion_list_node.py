"""
ExclusionListNode Executor + 통합 테스트

테스트 대상:
1. ExclusionListNodeExecutor 직접 실행 (다양한 입력 케이스)
2. 워크플로우 JSON 통합 테스트 (패턴 A/B/C)
3. 주문 노드 안전장치 테스트 (제외 종목 차단/우회)

실행:
    cd src/programgarden && poetry run pytest tests/test_exclusion_list_node.py -v
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from programgarden.executor import (
    WorkflowExecutor,
    ExclusionListNodeExecutor,
    NewOrderNodeExecutor,
)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_context(node_types=None, node_outputs=None):
    """ExecutionContext mock 생성

    Args:
        node_types: {node_id: node_type} 매핑
        node_outputs: {node_id: outputs_dict} 매핑
    """
    ctx = MagicMock()
    ctx.log = MagicMock()
    ctx._node_types = node_types or {}

    def get_all_outputs(nid):
        if node_outputs and nid in node_outputs:
            return node_outputs[nid]
        return {}

    ctx.get_all_outputs = MagicMock(side_effect=get_all_outputs)
    return ctx


# ---------------------------------------------------------------------------
# Part 1: ExclusionListNodeExecutor 직접 실행 테스트
# ---------------------------------------------------------------------------


class TestExclusionListExecutorRegistration:
    """ExclusionListNode executor 등록 확인"""

    def test_executor_registered(self):
        we = WorkflowExecutor()
        assert "ExclusionListNode" in we._executors

    def test_executor_is_correct_type(self):
        we = WorkflowExecutor()
        assert isinstance(we._executors["ExclusionListNode"], ExclusionListNodeExecutor)

    def test_in_no_auto_iterate(self):
        """ExclusionListNode는 auto-iterate 면제 노드에 포함"""
        from programgarden.executor import WorkflowJob
        assert "ExclusionListNode" in WorkflowJob.NO_AUTO_ITERATE_NODE_TYPES


class TestExclusionListExecutorManualOnly:
    """수동 입력만 사용하는 케이스"""

    @pytest.fixture
    def executor(self):
        return ExclusionListNodeExecutor()

    @pytest.fixture
    def ctx(self):
        return _make_mock_context()

    @pytest.mark.asyncio
    async def test_single_symbol(self, executor, ctx):
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": [{"exchange": "NASDAQ", "symbol": "NVDA", "reason": "과열 우려"}],
            },
            context=ctx,
        )
        assert result["count"] == 1
        assert result["excluded"][0]["symbol"] == "NVDA"
        assert result["excluded"][0]["exchange"] == "NASDAQ"
        assert result["reasons"]["NVDA"] == "과열 우려"

    @pytest.mark.asyncio
    async def test_multiple_symbols(self, executor, ctx):
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": [
                    {"exchange": "NASDAQ", "symbol": "NVDA", "reason": "과열"},
                    {"exchange": "NYSE", "symbol": "BA", "reason": "사고 리스크"},
                ],
            },
            context=ctx,
        )
        assert result["count"] == 2
        symbols = {s["symbol"] for s in result["excluded"]}
        assert symbols == {"NVDA", "BA"}
        assert result["reasons"]["NVDA"] == "과열"
        assert result["reasons"]["BA"] == "사고 리스크"

    @pytest.mark.asyncio
    async def test_default_reason_applied(self, executor, ctx):
        """개별 reason이 없으면 default_reason 적용"""
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}],
                "default_reason": "리스크 관리",
            },
            context=ctx,
        )
        assert result["reasons"]["AAPL"] == "리스크 관리"

    @pytest.mark.asyncio
    async def test_individual_reason_overrides_default(self, executor, ctx):
        """개별 reason이 있으면 default_reason 무시"""
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL", "reason": "실적 부진"}],
                "default_reason": "리스크 관리",
            },
            context=ctx,
        )
        assert result["reasons"]["AAPL"] == "실적 부진"

    @pytest.mark.asyncio
    async def test_string_entry_with_default_reason(self, executor, ctx):
        """문자열 입력 + default_reason"""
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": ["AAPL"],
                "default_reason": "리스크 관리",
            },
            context=ctx,
        )
        assert result["count"] == 1
        assert result["excluded"][0]["symbol"] == "AAPL"
        assert result["reasons"]["AAPL"] == "리스크 관리"


class TestExclusionListExecutorDynamicOnly:
    """동적 입력만 사용하는 케이스"""

    @pytest.fixture
    def executor(self):
        return ExclusionListNodeExecutor()

    @pytest.fixture
    def ctx(self):
        return _make_mock_context()

    @pytest.mark.asyncio
    async def test_dynamic_symbols(self, executor, ctx):
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "dynamic_symbols": [
                    {"exchange": "NASDAQ", "symbol": "TSLA"},
                    {"exchange": "NYSE", "symbol": "GE"},
                ],
            },
            context=ctx,
        )
        assert result["count"] == 2
        symbols = {s["symbol"] for s in result["excluded"]}
        assert symbols == {"TSLA", "GE"}

    @pytest.mark.asyncio
    async def test_dynamic_with_default_reason(self, executor, ctx):
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "dynamic_symbols": [{"exchange": "NASDAQ", "symbol": "TSLA"}],
                "default_reason": "보유 종목",
            },
            context=ctx,
        )
        assert result["reasons"]["TSLA"] == "보유 종목"

    @pytest.mark.asyncio
    async def test_dynamic_string_entries(self, executor, ctx):
        """동적 입력에 문자열 배열"""
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "dynamic_symbols": ["AAPL", "MSFT"],
                "default_reason": "보유 종목",
            },
            context=ctx,
        )
        assert result["count"] == 2
        symbols = {s["symbol"] for s in result["excluded"]}
        assert symbols == {"AAPL", "MSFT"}


class TestExclusionListExecutorMerge:
    """수동 + 동적 합산 (중복 제거) 케이스"""

    @pytest.fixture
    def executor(self):
        return ExclusionListNodeExecutor()

    @pytest.fixture
    def ctx(self):
        return _make_mock_context()

    @pytest.mark.asyncio
    async def test_dedup_same_symbol(self, executor, ctx):
        """같은 심볼이 수동/동적 모두 있으면 수동 우선, 중복 제거"""
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": [{"exchange": "NASDAQ", "symbol": "NVDA", "reason": "수동 제외"}],
                "dynamic_symbols": [{"exchange": "NASDAQ", "symbol": "NVDA", "reason": "동적 제외"}],
            },
            context=ctx,
        )
        assert result["count"] == 1
        assert result["reasons"]["NVDA"] == "수동 제외"  # 수동 입력 우선

    @pytest.mark.asyncio
    async def test_merge_different_symbols(self, executor, ctx):
        """서로 다른 심볼은 합산"""
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": [{"exchange": "NASDAQ", "symbol": "NVDA"}],
                "dynamic_symbols": [{"exchange": "NYSE", "symbol": "BA"}],
            },
            context=ctx,
        )
        assert result["count"] == 2
        symbols = {s["symbol"] for s in result["excluded"]}
        assert symbols == {"NVDA", "BA"}

    @pytest.mark.asyncio
    async def test_same_symbol_different_exchange(self, executor, ctx):
        """같은 심볼, 다른 거래소 → symbol 기준 중복제거 (첫 번째 수동 우선)"""
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": [{"exchange": "NYSE", "symbol": "AAPL"}],
                "dynamic_symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}],
            },
            context=ctx,
        )
        # symbol 기준 중복제거 → 1개
        assert result["count"] == 1
        assert result["excluded"][0]["exchange"] == "NYSE"  # 수동 입력 우선


class TestExclusionListExecutorFilter:
    """input_symbols 필터링 케이스"""

    @pytest.fixture
    def executor(self):
        return ExclusionListNodeExecutor()

    @pytest.fixture
    def ctx(self):
        return _make_mock_context()

    @pytest.mark.asyncio
    async def test_filter_removes_excluded(self, executor, ctx):
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": [{"exchange": "NASDAQ", "symbol": "NVDA"}],
                "input_symbols": [
                    {"exchange": "NASDAQ", "symbol": "AAPL"},
                    {"exchange": "NASDAQ", "symbol": "NVDA"},
                    {"exchange": "NYSE", "symbol": "BA"},
                ],
            },
            context=ctx,
        )
        assert result["count"] == 1  # excluded count
        filtered_symbols = {s["symbol"] for s in result["filtered"]}
        assert "NVDA" not in filtered_symbols
        assert "AAPL" in filtered_symbols
        assert "BA" in filtered_symbols
        assert len(result["filtered"]) == 2

    @pytest.mark.asyncio
    async def test_filter_no_input_symbols(self, executor, ctx):
        """input_symbols가 없으면 filtered는 빈 배열"""
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": [{"exchange": "NASDAQ", "symbol": "NVDA"}],
            },
            context=ctx,
        )
        assert result["filtered"] == []

    @pytest.mark.asyncio
    async def test_filter_all_excluded(self, executor, ctx):
        """모든 input_symbols가 제외 목록에 포함"""
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": [
                    {"exchange": "NASDAQ", "symbol": "AAPL"},
                    {"exchange": "NASDAQ", "symbol": "NVDA"},
                ],
                "input_symbols": [
                    {"exchange": "NASDAQ", "symbol": "AAPL"},
                    {"exchange": "NASDAQ", "symbol": "NVDA"},
                ],
            },
            context=ctx,
        )
        assert result["filtered"] == []

    @pytest.mark.asyncio
    async def test_filter_preserves_original_data(self, executor, ctx):
        """필터링 결과가 원본 데이터를 보존하는지 확인"""
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": [{"exchange": "NASDAQ", "symbol": "NVDA"}],
                "input_symbols": [
                    {"exchange": "NASDAQ", "symbol": "AAPL", "name": "Apple Inc"},
                ],
            },
            context=ctx,
        )
        assert len(result["filtered"]) == 1
        assert result["filtered"][0]["name"] == "Apple Inc"


class TestExclusionListExecutorEdgeCases:
    """엣지 케이스"""

    @pytest.fixture
    def executor(self):
        return ExclusionListNodeExecutor()

    @pytest.fixture
    def ctx(self):
        return _make_mock_context()

    @pytest.mark.asyncio
    async def test_empty_symbols(self, executor, ctx):
        """빈 입력"""
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={},
            context=ctx,
        )
        assert result["count"] == 0
        assert result["excluded"] == []
        assert result["filtered"] == []
        assert result["reasons"] == {}

    @pytest.mark.asyncio
    async def test_none_symbols(self, executor, ctx):
        """None 입력"""
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={"symbols": None, "dynamic_symbols": None},
            context=ctx,
        )
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_skip_empty_symbol_entries(self, executor, ctx):
        """빈 심볼은 무시"""
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": [
                    {"exchange": "NASDAQ", "symbol": ""},
                    {"exchange": "NASDAQ", "symbol": "NVDA"},
                ],
            },
            context=ctx,
        )
        assert result["count"] == 1
        assert result["excluded"][0]["symbol"] == "NVDA"

    @pytest.mark.asyncio
    async def test_no_reason_no_default(self, executor, ctx):
        """reason도 default_reason도 없으면 reasons에 포함 안 함"""
        result = await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}],
            },
            context=ctx,
        )
        assert "AAPL" not in result["reasons"]

    @pytest.mark.asyncio
    async def test_log_called(self, executor, ctx):
        """executor가 로그를 남기는지 확인"""
        await executor.execute(
            node_id="excl1",
            node_type="ExclusionListNode",
            config={
                "symbols": [{"exchange": "NASDAQ", "symbol": "NVDA"}],
            },
            context=ctx,
        )
        ctx.log.assert_called_once()
        args = ctx.log.call_args[0]
        assert args[0] == "info"
        assert "1 excluded" in args[1]


# ---------------------------------------------------------------------------
# Part 2: 워크플로우 JSON 통합 테스트
# ---------------------------------------------------------------------------


class _WorkflowTracker:
    """워크플로우 노드 상태/출력 추적"""

    def __init__(self):
        self.completed = []
        self.outputs = {}
        self.logs = []

    async def on_node_state_change(self, event):
        state = event.state.value if hasattr(event.state, "value") else str(event.state)
        if state == "completed":
            self.completed.append(event.node_id)
            if event.outputs:
                self.outputs[event.node_id] = event.outputs

    async def on_edge_state_change(self, event): pass
    async def on_log(self, event):
        self.logs.append(event)
    async def on_job_state_change(self, event): pass
    async def on_display_data(self, event): pass


class TestExclusionListWorkflow:
    """워크플로우 JSON 통합 테스트"""

    @pytest.mark.asyncio
    async def test_pattern_b_direct_filtering(self):
        """패턴 B: ExclusionListNode가 input_symbols를 직접 필터링"""
        workflow = {
            "id": "test-exclusion-b",
            "name": "패턴 B 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "watchlist",
                    "type": "WatchlistNode",
                    "symbols": [
                        {"exchange": "NASDAQ", "symbol": "AAPL"},
                        {"exchange": "NASDAQ", "symbol": "NVDA"},
                        {"exchange": "NYSE", "symbol": "BA"},
                    ],
                },
                {
                    "id": "exclusion",
                    "type": "ExclusionListNode",
                    "symbols": [
                        {"exchange": "NASDAQ", "symbol": "NVDA", "reason": "변동성 과다"},
                    ],
                    "input_symbols": "{{ nodes.watchlist.symbols }}",
                },
            ],
            "edges": [
                {"from": "start", "to": "watchlist"},
                {"from": "watchlist", "to": "exclusion"},
            ],
        }

        executor = WorkflowExecutor()
        tracker = _WorkflowTracker()
        job = await executor.execute(workflow, listeners=[tracker])
        await asyncio.wait_for(job._task, timeout=10)

        assert "exclusion" in tracker.completed

        output = job.context.get_all_outputs("exclusion")
        assert output["count"] == 1
        assert output["excluded"][0]["symbol"] == "NVDA"
        assert output["reasons"]["NVDA"] == "변동성 과다"

        filtered_symbols = {s["symbol"] for s in output["filtered"]}
        assert "AAPL" in filtered_symbols
        assert "BA" in filtered_symbols
        assert "NVDA" not in filtered_symbols

    @pytest.mark.asyncio
    async def test_pattern_a_with_symbol_filter(self):
        """패턴 A: ExclusionListNode 출력을 SymbolFilterNode에서 참조"""
        workflow = {
            "id": "test-exclusion-a",
            "name": "패턴 A 테스트",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "watchlist",
                    "type": "WatchlistNode",
                    "symbols": [
                        {"exchange": "NASDAQ", "symbol": "AAPL"},
                        {"exchange": "NASDAQ", "symbol": "NVDA"},
                        {"exchange": "NYSE", "symbol": "BA"},
                    ],
                },
                {
                    "id": "exclusion",
                    "type": "ExclusionListNode",
                    "symbols": [
                        {"exchange": "NASDAQ", "symbol": "NVDA"},
                    ],
                },
                {
                    "id": "filter",
                    "type": "SymbolFilterNode",
                    "operation": "difference",
                    "input_a": "{{ nodes.watchlist.symbols }}",
                    "input_b": "{{ nodes.exclusion.excluded }}",
                },
            ],
            "edges": [
                {"from": "start", "to": "watchlist"},
                {"from": "start", "to": "exclusion"},
                {"from": "watchlist", "to": "filter"},
                {"from": "exclusion", "to": "filter"},
            ],
        }

        executor = WorkflowExecutor()
        tracker = _WorkflowTracker()
        job = await executor.execute(workflow, listeners=[tracker])
        await asyncio.wait_for(job._task, timeout=10)

        assert "filter" in tracker.completed

        filter_output = job.context.get_all_outputs("filter")
        filtered_symbols = {s["symbol"] for s in filter_output["symbols"]}
        assert "AAPL" in filtered_symbols
        assert "BA" in filtered_symbols
        assert "NVDA" not in filtered_symbols

    @pytest.mark.asyncio
    async def test_exclusion_only_no_input(self):
        """제외 목록만 선언 (필터링 없음)"""
        workflow = {
            "id": "test-exclusion-only",
            "name": "제외 목록만",
            "nodes": [
                {"id": "start", "type": "StartNode"},
                {
                    "id": "exclusion",
                    "type": "ExclusionListNode",
                    "symbols": [
                        {"exchange": "NASDAQ", "symbol": "NVDA", "reason": "과열"},
                        {"exchange": "NYSE", "symbol": "BA", "reason": "리스크"},
                    ],
                },
            ],
            "edges": [
                {"from": "start", "to": "exclusion"},
            ],
        }

        executor = WorkflowExecutor()
        tracker = _WorkflowTracker()
        job = await executor.execute(workflow, listeners=[tracker])
        await asyncio.wait_for(job._task, timeout=10)

        output = job.context.get_all_outputs("exclusion")
        assert output["count"] == 2
        assert output["filtered"] == []
        assert len(output["reasons"]) == 2


# ---------------------------------------------------------------------------
# Part 3: 주문 노드 안전장치 테스트
# ---------------------------------------------------------------------------


class TestOrderExclusionSafeguard:
    """주문 노드의 ExclusionList 안전장치 테스트"""

    @pytest.fixture
    def order_executor(self):
        return NewOrderNodeExecutor()

    def test_check_exclusion_list_found(self, order_executor):
        """제외 종목이면 (True, reason) 반환"""
        ctx = _make_mock_context(
            node_types={"excl1": "ExclusionListNode"},
            node_outputs={
                "excl1": {
                    "excluded": [
                        {"exchange": "NASDAQ", "symbol": "NVDA"},
                        {"exchange": "NYSE", "symbol": "BA"},
                    ],
                    "reasons": {"NVDA": "과열 우려", "BA": "사고 리스크"},
                },
            },
        )
        is_excluded, reason = order_executor._check_exclusion_list("NVDA", ctx)
        assert is_excluded is True
        assert reason == "과열 우려"

    def test_check_exclusion_list_not_found(self, order_executor):
        """제외 종목이 아니면 (False, "") 반환"""
        ctx = _make_mock_context(
            node_types={"excl1": "ExclusionListNode"},
            node_outputs={
                "excl1": {
                    "excluded": [{"exchange": "NASDAQ", "symbol": "NVDA"}],
                    "reasons": {"NVDA": "과열"},
                },
            },
        )
        is_excluded, reason = order_executor._check_exclusion_list("AAPL", ctx)
        assert is_excluded is False
        assert reason == ""

    def test_check_exclusion_list_no_exclusion_node(self, order_executor):
        """ExclusionListNode가 없는 워크플로우"""
        ctx = _make_mock_context(
            node_types={"watchlist1": "WatchlistNode"},
        )
        is_excluded, reason = order_executor._check_exclusion_list("NVDA", ctx)
        assert is_excluded is False

    def test_check_exclusion_list_empty_outputs(self, order_executor):
        """ExclusionListNode가 있지만 출력이 비어있는 경우"""
        ctx = _make_mock_context(
            node_types={"excl1": "ExclusionListNode"},
            node_outputs={"excl1": {}},
        )
        is_excluded, reason = order_executor._check_exclusion_list("NVDA", ctx)
        assert is_excluded is False

    def test_check_exclusion_reason_missing(self, order_executor):
        """제외 종목이지만 reason이 없는 경우"""
        ctx = _make_mock_context(
            node_types={"excl1": "ExclusionListNode"},
            node_outputs={
                "excl1": {
                    "excluded": [{"exchange": "NASDAQ", "symbol": "NVDA"}],
                    "reasons": {},
                },
            },
        )
        is_excluded, reason = order_executor._check_exclusion_list("NVDA", ctx)
        assert is_excluded is True
        assert reason == ""

    def test_check_exclusion_list_multiple_nodes(self, order_executor):
        """여러 ExclusionListNode가 있는 경우 (하나라도 포함이면 차단)"""
        ctx = _make_mock_context(
            node_types={
                "excl1": "ExclusionListNode",
                "excl2": "ExclusionListNode",
            },
            node_outputs={
                "excl1": {
                    "excluded": [{"exchange": "NASDAQ", "symbol": "AAPL"}],
                    "reasons": {"AAPL": "리스크"},
                },
                "excl2": {
                    "excluded": [{"exchange": "NASDAQ", "symbol": "NVDA"}],
                    "reasons": {"NVDA": "과열"},
                },
            },
        )
        is_excluded1, reason1 = order_executor._check_exclusion_list("AAPL", ctx)
        assert is_excluded1 is True
        assert reason1 == "리스크"

        is_excluded2, reason2 = order_executor._check_exclusion_list("NVDA", ctx)
        assert is_excluded2 is True
        assert reason2 == "과열"
