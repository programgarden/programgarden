"""
OverseasStockFundamentalNode 단위 테스트

테스트 대상:
1. 노드 모델 생성 및 타입/카테고리 검증
2. 출력 포트 필드 검증 (FUNDAMENTAL_DATA_FIELDS)
3. FieldSchema 검증
4. NodeTypeRegistry 등록 확인
5. is_tool_enabled 확인
"""

import pytest
from programgarden_core.nodes.fundamental_stock import OverseasStockFundamentalNode
from programgarden_core.nodes.base import (
    NodeCategory,
    ProductScope,
    BrokerProvider,
    FUNDAMENTAL_DATA_FIELDS,
    PRICE_DATA_FIELDS,
)


class TestFundamentalNodeModel:
    """OverseasStockFundamentalNode 모델 테스트"""

    def test_node_has_correct_type(self):
        node = OverseasStockFundamentalNode(id="fund1")
        assert node.type == "OverseasStockFundamentalNode"

    def test_node_category_is_market(self):
        node = OverseasStockFundamentalNode(id="fund1")
        assert node.category == NodeCategory.MARKET

    def test_node_product_scope_is_stock(self):
        assert OverseasStockFundamentalNode._product_scope == ProductScope.STOCK

    def test_node_broker_provider_is_ls(self):
        assert OverseasStockFundamentalNode._broker_provider == BrokerProvider.LS

    def test_node_default_symbol_is_none(self):
        node = OverseasStockFundamentalNode(id="fund1")
        assert node.symbol is None

    def test_node_custom_symbol(self):
        node = OverseasStockFundamentalNode(
            id="fund1",
            symbol={"exchange": "NASDAQ", "symbol": "AAPL"},
        )
        assert node.symbol["exchange"] == "NASDAQ"
        assert node.symbol["symbol"] == "AAPL"

    def test_node_is_tool_enabled(self):
        assert OverseasStockFundamentalNode.is_tool_enabled() is True

    def test_node_description_is_i18n_key(self):
        node = OverseasStockFundamentalNode(id="fund1")
        assert node.description.startswith("i18n:")


class TestFundamentalNodePorts:
    """입출력 포트 검증"""

    def test_input_ports(self):
        node = OverseasStockFundamentalNode(id="fund1")
        input_names = [p.name for p in node._inputs]
        assert "symbol" in input_names
        assert "trigger" in input_names

    def test_output_port_name(self):
        node = OverseasStockFundamentalNode(id="fund1")
        output_names = [p.name for p in node._outputs]
        assert "value" in output_names

    def test_output_port_type(self):
        node = OverseasStockFundamentalNode(id="fund1")
        value_port = next(p for p in node._outputs if p.name == "value")
        assert value_port.type == "fundamental_data"

    def test_output_port_has_fields(self):
        node = OverseasStockFundamentalNode(id="fund1")
        value_port = next(p for p in node._outputs if p.name == "value")
        assert value_port.fields is not None
        assert value_port.fields == FUNDAMENTAL_DATA_FIELDS


class TestFundamentalDataFields:
    """FUNDAMENTAL_DATA_FIELDS 상수 검증"""

    def test_has_required_fields(self):
        field_names = [f["name"] for f in FUNDAMENTAL_DATA_FIELDS]
        expected = [
            "exchange", "symbol", "name", "industry", "nation",
            "exchange_name", "current_price", "volume", "change_percent",
            "per", "eps", "market_cap", "shares_outstanding",
            "high_52w", "low_52w", "exchange_rate",
        ]
        for name in expected:
            assert name in field_names, f"Missing field: {name}"

    def test_field_count(self):
        assert len(FUNDAMENTAL_DATA_FIELDS) == 16


class TestPriceDataFieldsExtended:
    """PRICE_DATA_FIELDS에 PER/EPS 추가 검증"""

    def test_has_per_field(self):
        field_names = [f["name"] for f in PRICE_DATA_FIELDS]
        assert "per" in field_names

    def test_has_eps_field(self):
        field_names = [f["name"] for f in PRICE_DATA_FIELDS]
        assert "eps" in field_names

    def test_per_type_is_number(self):
        per_field = next(f for f in PRICE_DATA_FIELDS if f["name"] == "per")
        assert per_field["type"] == "number"

    def test_eps_type_is_number(self):
        eps_field = next(f for f in PRICE_DATA_FIELDS if f["name"] == "eps")
        assert eps_field["type"] == "number"


class TestFundamentalNodeFieldSchema:
    """FieldSchema 검증"""

    def test_field_schema_has_symbol(self):
        schema = OverseasStockFundamentalNode.get_field_schema()
        assert "symbol" in schema

    def test_symbol_field_is_object_type(self):
        schema = OverseasStockFundamentalNode.get_field_schema()
        field_type = schema["symbol"].type
        type_val = field_type.value if hasattr(field_type, 'value') else str(field_type)
        assert type_val == "object"

    def test_symbol_field_has_object_schema(self):
        schema = OverseasStockFundamentalNode.get_field_schema()
        assert schema["symbol"].object_schema is not None
        names = [s["name"] for s in schema["symbol"].object_schema]
        assert "exchange" in names
        assert "symbol" in names


class TestFundamentalNodeRegistry:
    """NodeTypeRegistry 등록 검증"""

    def test_node_registered_in_registry(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        assert registry.get("OverseasStockFundamentalNode") is not None

    def test_node_schema_available(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        schema = registry.get_schema("OverseasStockFundamentalNode")
        assert schema is not None
        assert schema.category == "market"
        assert schema.product_scope == "overseas_stock"

    def test_node_in_market_category_list(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        market_types = registry.list_types(category="market")
        assert "OverseasStockFundamentalNode" in market_types


class TestFundamentalNodeToolSchema:
    """AI Tool 스키마 검증"""

    def test_tool_schema_generation(self):
        schema = OverseasStockFundamentalNode.as_tool_schema()
        assert schema["tool_name"] == "overseas_stock_fundamental"
        assert schema["node_type"] == "OverseasStockFundamentalNode"

    def test_tool_schema_has_parameters(self):
        schema = OverseasStockFundamentalNode.as_tool_schema()
        assert "symbol" in schema["parameters"]

    def test_tool_schema_has_returns(self):
        schema = OverseasStockFundamentalNode.as_tool_schema()
        assert "value" in schema["returns"]
