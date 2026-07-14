"""
Item-based Execution Tests

item-based execution 테스트:
- SplitNode: 배열을 개별 아이템으로 분리
- AggregateNode: 아이템 결과를 배열로 수집
- Branch execution: Split → [nodes] → Aggregate 패턴
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

from programgarden_core.nodes.infra import SplitNode, AggregateNode
from programgarden_core.nodes.symbol import WatchlistNode
from programgarden_core.nodes.base import BaseNode


class TestSplitNodeSchema:
    """SplitNode 스키마 테스트"""

    def test_split_node_has_correct_type(self):
        """SplitNode type이 올바른지 확인"""
        node = SplitNode(id="split1")
        assert node.type == "SplitNode"

    def test_split_node_default_values(self):
        """SplitNode 기본값 확인"""
        node = SplitNode(id="split1")
        assert node.parallel is False
        assert node.delay_ms == 0
        assert node.continue_on_error is True

    def test_split_node_input_ports(self):
        """SplitNode 입력 포트 확인"""
        node = SplitNode(id="split1")
        input_names = [p.name for p in node._inputs]
        assert "array" in input_names

    def test_split_node_output_ports(self):
        """SplitNode 출력 포트 확인"""
        node = SplitNode(id="split1")
        output_names = [p.name for p in node._outputs]
        assert "item" in output_names
        assert "index" in output_names
        assert "total" in output_names


class TestAggregateNodeSchema:
    """AggregateNode 스키마 테스트"""

    def test_aggregate_node_has_correct_type(self):
        """AggregateNode type이 올바른지 확인"""
        node = AggregateNode(id="agg1")
        assert node.type == "AggregateNode"

    def test_aggregate_node_default_values(self):
        """AggregateNode 기본값 확인"""
        node = AggregateNode(id="agg1")
        assert node.mode == "collect"
        assert node.filter_field == "passed"
        assert node.value_field == "value"

    def test_aggregate_node_modes(self):
        """AggregateNode 지원 모드 확인"""
        valid_modes = ["collect", "filter", "sum", "avg", "min", "max", "count", "first", "last"]
        for mode in valid_modes:
            node = AggregateNode(id="agg1", mode=mode)
            assert node.mode == mode

    def test_aggregate_node_input_ports(self):
        """AggregateNode 입력 포트 확인"""
        node = AggregateNode(id="agg1")
        input_names = [p.name for p in node._inputs]
        assert "item" in input_names

    def test_aggregate_node_output_ports(self):
        """AggregateNode 출력 포트 확인"""
        node = AggregateNode(id="agg1")
        output_names = [p.name for p in node._outputs]
        assert "array" in output_names
        assert "value" in output_names
        assert "count" in output_names


class TestSplitNodeFieldSchema:
    """SplitNode FieldSchema 테스트"""

    def test_split_node_field_schema(self):
        """SplitNode get_field_schema() 호출 확인"""
        schema = SplitNode.get_field_schema()
        assert "parallel" in schema
        assert "delay_ms" in schema
        assert "continue_on_error" in schema

    def test_split_node_parallel_field(self):
        """parallel 필드 스키마 확인"""
        schema = SplitNode.get_field_schema()
        parallel_schema = schema["parallel"]
        assert parallel_schema.default is False

    def test_split_node_delay_ms_field(self):
        """delay_ms 필드 스키마 확인"""
        schema = SplitNode.get_field_schema()
        delay_schema = schema["delay_ms"]
        assert delay_schema.default == 0
        assert delay_schema.min_value == 0
        assert delay_schema.max_value == 60000


class TestAggregateNodeFieldSchema:
    """AggregateNode FieldSchema 테스트"""

    def test_aggregate_node_field_schema(self):
        """AggregateNode get_field_schema() 호출 확인"""
        schema = AggregateNode.get_field_schema()
        assert "mode" in schema
        assert "filter_field" in schema
        assert "value_field" in schema

    def test_aggregate_node_mode_enum(self):
        """mode 필드 enum 값 확인"""
        schema = AggregateNode.get_field_schema()
        mode_schema = schema["mode"]
        expected_modes = ["collect", "filter", "sum", "avg", "min", "max", "count", "first", "last"]
        assert mode_schema.enum_values == expected_modes


class TestItemBasedNodeSchemas:
    """Item-based 변경된 노드 스키마 테스트"""

    def test_market_data_node_single_symbol_input(self):
        """MarketDataNode가 단일 symbol 입력을 받는지 확인"""
        from programgarden_core.nodes.data_stock import OverseasStockMarketDataNode

        node = OverseasStockMarketDataNode(id="test")
        input_names = [p.name for p in node._inputs]
        assert "symbol" in input_names
        assert "symbols" not in input_names

    def test_market_data_node_value_output(self):
        """MarketDataNode 가 단일 value + 배열 values 둘 다 노출하는지 확인.

        v1.21.11+: strict port 검증을 위해 runtime 이 emit 하는 모든 키를 schema 에 선언.
        - value: 단일 시세 (예전부터 선언)
        - values: 배열 (runtime 의 실제 반환값, 워크플로우에서 직접 접근)
        """
        from programgarden_core.nodes.data_stock import OverseasStockMarketDataNode

        node = OverseasStockMarketDataNode(id="test")
        output_names = [p.name for p in node._outputs]
        assert "value" in output_names
        assert "values" in output_names

    def test_historical_data_node_single_symbol_input(self):
        """HistoricalDataNode가 단일 symbol 입력을 받는지 확인"""
        from programgarden_core.nodes.backtest_stock import OverseasStockHistoricalDataNode

        node = OverseasStockHistoricalDataNode(id="test")
        input_names = [p.name for p in node._inputs]
        assert "symbol" in input_names

    def test_condition_node_single_data_input(self):
        """ConditionNode가 items { from, extract } 입력을 받는지 확인"""
        from programgarden_core.nodes.condition import ConditionNode

        schema = ConditionNode.get_field_schema()
        items_schema = schema["items"]
        from programgarden_core.models.field_binding import ExpressionMode, FieldType
        assert items_schema.type == FieldType.OBJECT
        assert items_schema.object_schema is not None
        # items.from, items.extract 스키마 확인
        assert any(s.get("name") == "from" for s in items_schema.object_schema)
        assert any(s.get("name") == "extract" for s in items_schema.object_schema)

    def test_condition_node_output_ports_match_runtime(self):
        """ConditionNode schema 가 runtime emit 키 전부 선언하는지 확인.

        v1.21.11+: strict port 검증을 위해 runtime 의 6 keys 전부 schema 화.
        - result, is_condition_met (boolean), symbols (input echo)
        - passed_symbols, failed_symbols, symbol_results, values
        """
        from programgarden_core.nodes.condition import ConditionNode

        node = ConditionNode(id="test", plugin="RSI")
        output_names = {p.name for p in node._outputs}
        assert {"result", "is_condition_met", "symbols", "passed_symbols", "failed_symbols", "symbol_results", "values"} <= output_names

    def test_new_order_node_single_order_input(self):
        """NewOrderNode가 단일 order 입력을 받는지 확인"""
        from programgarden_core.nodes.order import OverseasStockNewOrderNode

        node = OverseasStockNewOrderNode(id="test")
        input_names = [p.name for p in node._inputs]
        assert "order" in input_names
        assert "orders" not in input_names

    def test_position_sizing_node_single_symbol_input(self):
        """PositionSizingNode가 단일 symbol 입력을 받는지 확인"""
        from programgarden_core.nodes.risk import PositionSizingNode

        node = PositionSizingNode(id="test")
        input_names = [p.name for p in node._inputs]
        assert "symbol" in input_names
        assert "symbols" not in input_names

    def test_position_sizing_node_single_order_output(self):
        """PositionSizingNode가 단일 order 출력을 하는지 확인"""
        from programgarden_core.nodes.risk import PositionSizingNode

        node = PositionSizingNode(id="test")
        output_names = [p.name for p in node._outputs]
        assert "order" in output_names
        assert "orders" not in output_names


class TestNodeRegistry:
    """노드 레지스트리 테스트"""

    def test_split_node_registered(self):
        """SplitNode가 레지스트리에 등록되었는지 확인"""
        from programgarden_core.registry.node_registry import NodeTypeRegistry

        registry = NodeTypeRegistry()
        node_types = registry.list_types()

        assert "SplitNode" in node_types

    def test_aggregate_node_registered(self):
        """AggregateNode가 레지스트리에 등록되었는지 확인"""
        from programgarden_core.registry.node_registry import NodeTypeRegistry

        registry = NodeTypeRegistry()
        node_types = registry.list_types()

        assert "AggregateNode" in node_types

    def test_split_node_in_infra_category(self):
        """SplitNode가 infra 카테고리에 있는지 확인"""
        from programgarden_core.registry.node_registry import NodeTypeRegistry

        registry = NodeTypeRegistry()
        infra_types = registry.list_types(category="infra")

        assert "SplitNode" in infra_types
        assert "AggregateNode" in infra_types


class TestSplitBranchArrayResolution:
    """SplitNode branch flow 의 배열 해석 — 2026-07-14 런타임 배선 결함1 회귀 테스트.

    계약 테스트(test_output_schema_contract)는 executor 의 return dict 를 AST 로 본다.
    그러나 Split→Aggregate branch flow 에서는 SplitNodeExecutor.execute 가 **아예 호출되지
    않고** WorkflowJob._execute_split_branch / _execute_branch_for_item 이 출력을 직접 set 한다.
    AST 계약 테스트가 구조적으로 못 보는 그 실제 경로를 여기서 행위로 검증한다.
    """

    @staticmethod
    def _mk_job(upstream_outputs: Dict[str, Any], split_config: Dict[str, Any]):
        from programgarden.executor import WorkflowJob
        from programgarden.context import ExecutionContext

        ctx = ExecutionContext(job_id="j", workflow_id="w")
        for port, val in upstream_outputs.items():
            ctx.set_output("up", port, val)

        class _Edge:
            def __init__(self, f, t):
                self.from_node_id, self.to_node_id = f, t

        job = MagicMock(spec=WorkflowJob)
        job.context = ctx
        job._execute_split_branch = WorkflowJob._execute_split_branch.__get__(job)
        job._get_branch_nodes = MagicMock(return_value={"rm"})
        wf = MagicMock()
        wf.edges = [_Edge("up", "split"), _Edge("split", "rm"), _Edge("rm", "agg")]
        wf.execution_order = ["up", "split", "rm", "agg"]
        wf.nodes = {}
        job.workflow = wf
        ctx.notify_node_state = AsyncMock()

        captured: Dict[str, Any] = {"items": []}

        async def _fbi(split_id, branch_order, item, index, total):
            captured["items"].append(item)
            captured["total"] = total
            return item

        job._execute_branch_for_item = _fbi
        job._execute_aggregate_node = AsyncMock()

        split_node = MagicMock()
        cfg = {"parallel": False, "delay_ms": 0, "continue_on_error": True}
        cfg.update(split_config)
        split_node.config = cfg
        return job, ctx, split_node, captured

    @pytest.mark.asyncio
    async def test_declared_items_port_is_actually_emitted(self):
        """선언한 `items` 출력 포트가 branch flow 에서 실제로 채워진다.

        이전엔 SplitNodeExecutor.execute 가 호출 안 돼 items 가 늘 비어 있었고,
        `{{ nodes.split.items }}` 를 바인딩한 하류는 조용히 빈 데이터를 받았다.
        선언되지 않은 legacy `_array` 별칭은 방출하지 않는다(선언==런타임).
        """
        held = [{"exchange": "82", "symbol": "AUID"}, {"exchange": "82", "symbol": "TSLA"}]
        job, ctx, split_node, _ = self._mk_job({"symbols": held}, {})
        await job._execute_split_branch("split", split_node, {"split": "agg"}, {"rm"})
        assert ctx.get_output("split", "items") == held
        # 미선언 내부 별칭 _array 는 더 이상 방출하지 않는다.
        assert ctx.get_output("split", "_array") is None

    @pytest.mark.asyncio
    async def test_explicit_array_binding_is_honored_over_upstream(self):
        """config.array 바인딩이 상류보다 **우선**한다(이전엔 구동부가 config 를 무시했다).

        상류에 held_symbols(2) 와 positions(3) 가 모두 있고 positions 가 먼저여도,
        array={{ held_symbols }} 를 명시하면 held_symbols(2건)를 순회해야 한다.
        """
        held = [{"symbol": "A"}, {"symbol": "B"}]
        pos = [{"symbol": "A"}, {"symbol": "B"}, {"symbol": "C"}]
        job, ctx, split_node, cap = self._mk_job(
            {"positions": pos, "held_symbols": held},
            {"array": "{{ nodes.up.held_symbols }}"},
        )
        await job._execute_split_branch("split", split_node, {"split": "agg"}, {"rm"})
        assert cap["total"] == 2
        assert cap["items"] == held

    @pytest.mark.asyncio
    async def test_ambiguous_multi_array_upstream_raises(self):
        """상류가 다중 배열(계좌: held_symbols/positions)인데 바인딩이 없으면 조용히 첫
        리스트를 집지 말고 사유가 담긴 예외로 실패한다."""
        job, ctx, split_node, _ = self._mk_job(
            {"held_symbols": [{"symbol": "A"}], "positions": [{"symbol": "A"}]},
            {},
        )
        with pytest.raises(RuntimeError, match="ambiguous"):
            await job._execute_split_branch("split", split_node, {"split": "agg"}, {"rm"})

    @pytest.mark.asyncio
    async def test_no_array_source_raises(self):
        """상류에 어떤 배열 포트도 없으면(스칼라만) 사유가 담긴 예외로 실패한다."""
        job, ctx, split_node, _ = self._mk_job({"price": 100.0, "count": 1}, {})
        with pytest.raises(RuntimeError, match="no array to split"):
            await job._execute_split_branch("split", split_node, {"split": "agg"}, {"rm"})

    @pytest.mark.asyncio
    async def test_single_array_upstream_still_works_without_binding(self):
        """단일 배열 상류(Watchlist→symbols)는 바인딩 없이도 그대로 동작(무회귀)."""
        syms = [{"symbol": "AAPL"}, {"symbol": "MSFT"}]
        job, ctx, split_node, cap = self._mk_job({"symbols": syms, "count": 2}, {})
        await job._execute_split_branch("split", split_node, {"split": "agg"}, {"rm"})
        assert cap["total"] == 2
        assert cap["items"] == syms


class TestThrottleMetaDoesNotLeakAsData:
    """ThrottleNode 내부 메타(_throttle_stats)가 데이터로 새지 않는다 —
    2026-07-14 런타임 배선 결함2 회귀 테스트 (생산자+소비자 양쪽)."""

    @staticmethod
    def _ctx():
        from programgarden.context import ExecutionContext

        ctx = ExecutionContext(job_id="j", workflow_id="w")

        async def _noop(**k):
            return None

        ctx.notify_node_state = _noop
        return ctx

    @pytest.mark.asyncio
    async def test_pending_throttle_emits_no_public_data(self):
        """상류 데이터가 없으면(pending) throttle 은 공개 데이터 포트를 내지 않는다.

        예전엔 outputs={} 에 _throttle_stats 만 실어 방출했다(passed:True 껍데기)."""
        from programgarden.executor import ThrottleNodeExecutor, _public_outputs

        out = await ThrottleNodeExecutor().execute(
            "throttle", "ThrottleNode",
            {"mode": "latest", "interval_sec": 5.0, "pass_first": True},
            self._ctx(),
        )
        assert _public_outputs(out) == {}, "pending 시 공개 포트가 없어야 한다"
        assert out["_throttle_stats"]["passed"] is False

    @pytest.mark.asyncio
    async def test_real_data_passes_through_without_stats_as_public(self):
        """실데이터가 있으면 그대로 통과하되 _throttle_stats 는 공개 데이터가 아니다."""
        from programgarden.executor import ThrottleNodeExecutor, _public_outputs

        out = await ThrottleNodeExecutor().execute(
            "throttle", "ThrottleNode",
            {"mode": "latest", "interval_sec": 5.0, "pass_first": True,
             "_realtime_data": {"price": 123.45, "symbol": "AUID"}},
            self._ctx(),
        )
        public = _public_outputs(out)
        assert public == {"price": 123.45, "symbol": "AUID"}
        assert "_throttle_stats" not in public

    def test_public_outputs_strips_underscore_ports(self):
        from programgarden.executor import _public_outputs

        assert _public_outputs(
            {"price": 1, "_throttle_stats": {"passed": True}, "_throttled": True}
        ) == {"price": 1}

    def test_branch_result_selection_ignores_meta_only_outputs(self):
        """branch 결과 선택은 공개 포트만 본다 — 메타만 있으면 item 으로 폴백."""
        from programgarden.executor import _public_outputs

        def pick(outputs, item):
            public = _public_outputs(outputs) if outputs else {}
            if public:
                return public.get("result") or public.get("value") or next(iter(public.values()), item)
            return item

        item = {"symbol": "AUID"}
        # 메타만 → item 폴백 (통계 아님)
        assert pick({"_throttle_stats": {"passed": True}}, item) == item
        # 실데이터 → 실데이터
        assert pick({"price": 99.0, "_throttle_stats": {}}, item) == 99.0


class TestBranchSkipsMetaOnlyItems:
    """메타만 낸 branch 아이템은 Aggregate 에 기여하지 않는다(skip) — 결함2 후속.

    ThrottleNode 가 이번 사이클을 throttling 중이면(공개 출력 없음) 그 아이템은 실데이터가
    없다 → 표에 가격 없는/이질적인 행이 끼면 안 된다."""

    @staticmethod
    def _job_with_stub_executor(node_outputs_by_type):
        from programgarden.executor import WorkflowJob
        from programgarden.context import ExecutionContext
        from unittest.mock import AsyncMock, MagicMock

        ctx = ExecutionContext(job_id="j", workflow_id="w")

        async def _noop(**k):
            return None

        ctx.notify_node_state = _noop
        ctx.notify_edge_state = _noop

        job = MagicMock(spec=WorkflowJob)
        job.context = ctx
        job._execute_branch_for_item = WorkflowJob._execute_branch_for_item.__get__(job)
        job._resolve_config_expressions = lambda cfg, nid: cfg
        job._auto_inject_connection = lambda nid, node, cfg: cfg

        class _Node:
            def __init__(self, t):
                self.node_type = t
                self.config = {}
                self.plugin = None
                self.fields = None

        wf = MagicMock()
        wf.edges = []
        wf.nodes = {t + "_node": _Node(t) for t in node_outputs_by_type}
        job.workflow = wf

        exec_stub = MagicMock()

        async def _exec_node(node_id, node_type, **kw):
            return node_outputs_by_type[node_type]

        exec_stub.execute_node = _exec_node
        job.executor = exec_stub
        return job, ctx

    @pytest.mark.asyncio
    async def test_meta_only_branch_item_is_skipped(self):
        from programgarden.executor import _SKIP_BRANCH_ITEM

        # throttle 이 throttling 중 → 내부 메타만
        job, _ = self._job_with_stub_executor(
            {"ThrottleNode": {"_throttled": True, "_throttle_stats": {"passed": False}}}
        )
        r = await job._execute_branch_for_item(
            split_id="split", branch_order=["ThrottleNode_node"],
            item={"symbol": "AUID"}, index=0, total=1,
        )
        assert r is _SKIP_BRANCH_ITEM

    @pytest.mark.asyncio
    async def test_real_data_branch_item_is_kept(self):
        from programgarden.executor import _SKIP_BRANCH_ITEM

        job, _ = self._job_with_stub_executor(
            {"ThrottleNode": {"price": 123.45, "_throttle_stats": {"passed": True}}}
        )
        r = await job._execute_branch_for_item(
            split_id="split", branch_order=["ThrottleNode_node"],
            item={"symbol": "AUID"}, index=0, total=1,
        )
        assert r is not _SKIP_BRANCH_ITEM
        assert r == 123.45


class TestRealtimePendingProducesNoRow:
    """real_market 이 pending(_pending 신호)일 때 하류가 빈 행을 그리지 않는다 — 결함2-pending.

    수용 기준: 표에 실제 체결가 행 or 정직한 빈 표만. 빈 dict/내부구조 행 0.
    """

    @pytest.mark.asyncio
    async def test_pending_upstream_yields_no_public_through_throttle(self):
        from programgarden.context import ExecutionContext
        from programgarden.executor import ThrottleNodeExecutor, _public_outputs

        ctx = ExecutionContext(job_id="j", workflow_id="w")

        async def _noop(**k):
            return None

        ctx.notify_node_state = _noop
        # real_market pending → 내부 _pending 신호만 (공개 데이터 포트 없음)
        ctx.set_output("rm", "_pending", True)
        ctx._workflow_edges = [{"from": "rm", "to": "throttle"}]

        out = await ThrottleNodeExecutor().execute(
            "throttle", "ThrottleNode",
            {"mode": "latest", "interval_sec": 5.0, "pass_first": True}, ctx,
        )
        # throttle 이 흘릴 실데이터가 없어 공개 출력이 없다 → branch 가 skip → 행 없음
        assert _public_outputs(out) == {}

    @pytest.mark.asyncio
    async def test_real_tick_passes_through(self):
        from programgarden.context import ExecutionContext
        from programgarden.executor import ThrottleNodeExecutor, _public_outputs

        ctx = ExecutionContext(job_id="j", workflow_id="w")

        async def _noop(**k):
            return None

        ctx.notify_node_state = _noop
        ctx.set_output("rm", "ohlcv_data", {"AUID": [{"close": 100.0}]})
        ctx._workflow_edges = [{"from": "rm", "to": "throttle"}]

        out = await ThrottleNodeExecutor().execute(
            "throttle", "ThrottleNode",
            {"mode": "latest", "interval_sec": 5.0, "pass_first": True}, ctx,
        )
        assert "ohlcv_data" in _public_outputs(out)
