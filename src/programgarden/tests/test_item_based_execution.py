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

    def test_market_data_node_single_value_output(self):
        """MarketDataNode가 단일 value 출력을 하는지 확인"""
        from programgarden_core.nodes.data_stock import OverseasStockMarketDataNode

        node = OverseasStockMarketDataNode(id="test")
        output_names = [p.name for p in node._outputs]
        assert "value" in output_names
        assert "values" not in output_names

    def test_historical_data_node_single_symbol_input(self):
        """HistoricalDataNode가 단일 symbol 입력을 받는지 확인"""
        from programgarden_core.nodes.backtest_stock import OverseasStockHistoricalDataNode

        node = OverseasStockHistoricalDataNode(id="test")
        input_names = [p.name for p in node._inputs]
        assert "symbol" in input_names

    def test_condition_node_single_data_input(self):
        """ConditionNode가 단일 data 입력을 받는지 확인"""
        from programgarden_core.nodes.condition import ConditionNode

        schema = ConditionNode.get_field_schema()
        data_schema = schema["data"]
        from programgarden_core.models.field_binding import ExpressionMode
        assert data_schema.expression_mode == ExpressionMode.EXPRESSION_ONLY

    def test_condition_node_single_result_output(self):
        """ConditionNode가 단일 result 출력을 하는지 확인"""
        from programgarden_core.nodes.condition import ConditionNode

        node = ConditionNode(id="test", plugin="RSI")
        output_names = [p.name for p in node._outputs]
        assert "result" in output_names
        # 이전 배열 출력들이 제거되었는지 확인
        assert "passed_symbols" not in output_names
        assert "failed_symbols" not in output_names

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
