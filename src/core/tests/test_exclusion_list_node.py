"""
ExclusionListNode 단위 테스트

테스트 대상:
1. 노드 모델 생성 및 타입/카테고리 검증
2. 입출력 포트 검증
3. FieldSchema 검증
4. NodeTypeRegistry 등록 확인
5. is_tool_enabled / as_tool_schema

실행:
    cd src/core && poetry run pytest tests/test_exclusion_list_node.py -v
"""

import pytest

from programgarden_core.nodes.symbol import ExclusionListNode
from programgarden_core.nodes.base import NodeCategory


# ============================================================
# 모델 테스트
# ============================================================


class TestExclusionListNodeModel:
    """ExclusionListNode 모델 테스트"""

    def test_node_has_correct_type(self):
        node = ExclusionListNode(id="excl1")
        assert node.type == "ExclusionListNode"

    def test_node_category_is_market(self):
        node = ExclusionListNode(id="excl1")
        assert node.category == NodeCategory.MARKET

    def test_node_description_is_i18n_key(self):
        node = ExclusionListNode(id="excl1")
        assert node.description.startswith("i18n:")

    def test_node_default_symbols_empty(self):
        node = ExclusionListNode(id="excl1")
        assert node.symbols == []

    def test_node_default_dynamic_symbols_none(self):
        node = ExclusionListNode(id="excl1")
        assert node.dynamic_symbols is None

    def test_node_default_input_symbols_none(self):
        node = ExclusionListNode(id="excl1")
        assert node.input_symbols is None

    def test_node_default_reason_empty(self):
        node = ExclusionListNode(id="excl1")
        assert node.default_reason == ""

    def test_node_custom_symbols(self):
        symbols = [{"exchange": "NASDAQ", "symbol": "NVDA", "reason": "과열"}]
        node = ExclusionListNode(id="excl1", symbols=symbols)
        assert len(node.symbols) == 1
        assert node.symbols[0]["symbol"] == "NVDA"

    def test_node_custom_default_reason(self):
        node = ExclusionListNode(id="excl1", default_reason="리스크 관리")
        assert node.default_reason == "리스크 관리"

    def test_node_is_tool_enabled(self):
        assert ExclusionListNode.is_tool_enabled() is True


# ============================================================
# 포트 테스트
# ============================================================


class TestExclusionListNodePorts:
    """ExclusionListNode 입출력 포트 검증"""

    def test_output_ports_count(self):
        node = ExclusionListNode(id="excl1")
        assert len(node._outputs) == 4

    def test_output_port_excluded(self):
        node = ExclusionListNode(id="excl1")
        port = next(p for p in node._outputs if p.name == "excluded")
        assert port.type == "symbol_list"

    def test_output_port_filtered(self):
        node = ExclusionListNode(id="excl1")
        port = next(p for p in node._outputs if p.name == "filtered")
        assert port.type == "symbol_list"

    def test_output_port_count(self):
        node = ExclusionListNode(id="excl1")
        port = next(p for p in node._outputs if p.name == "count")
        assert port.type == "integer"

    def test_output_port_reasons(self):
        node = ExclusionListNode(id="excl1")
        port = next(p for p in node._outputs if p.name == "reasons")
        assert port.type == "object"

    def test_output_ports_have_i18n_descriptions(self):
        node = ExclusionListNode(id="excl1")
        for port in node._outputs:
            assert port.description.startswith("i18n:")

    def test_excluded_port_has_symbol_list_fields(self):
        """excluded, filtered 포트에 SYMBOL_LIST_FIELDS가 있는지 확인"""
        node = ExclusionListNode(id="excl1")
        excluded_port = next(p for p in node._outputs if p.name == "excluded")
        assert excluded_port.fields is not None
        assert len(excluded_port.fields) > 0

    def test_filtered_port_has_symbol_list_fields(self):
        node = ExclusionListNode(id="excl1")
        filtered_port = next(p for p in node._outputs if p.name == "filtered")
        assert filtered_port.fields is not None
        assert len(filtered_port.fields) > 0


# ============================================================
# FieldSchema 테스트
# ============================================================


class TestExclusionListNodeFieldSchema:
    """ExclusionListNode FieldSchema 검증"""

    def test_field_schema_keys(self):
        schema = ExclusionListNode.get_field_schema()
        assert "symbols" in schema
        assert "dynamic_symbols" in schema
        assert "input_symbols" in schema
        assert "default_reason" in schema

    def test_symbols_field_type_is_array(self):
        schema = ExclusionListNode.get_field_schema()
        type_val = schema["symbols"].type
        val = type_val.value if hasattr(type_val, "value") else str(type_val)
        assert val == "array"

    def test_symbols_field_is_required(self):
        schema = ExclusionListNode.get_field_schema()
        assert schema["symbols"].required is True

    def test_symbols_field_has_custom_symbol_editor(self):
        schema = ExclusionListNode.get_field_schema()
        ui = schema["symbols"].ui_component
        val = ui.value if hasattr(ui, "value") else str(ui)
        assert "CUSTOM_SYMBOL_EDITOR" in val.upper()

    def test_symbols_field_ui_options_has_exchanges(self):
        schema = ExclusionListNode.get_field_schema()
        ui_opts = schema["symbols"].ui_options
        assert "exchanges" in ui_opts
        exchanges = [e["value"] for e in ui_opts["exchanges"]]
        assert "NASDAQ" in exchanges
        assert "NYSE" in exchanges

    def test_symbols_field_ui_options_has_reason_extra_field(self):
        schema = ExclusionListNode.get_field_schema()
        ui_opts = schema["symbols"].ui_options
        assert "extra_fields" in ui_opts
        reason_field = next(f for f in ui_opts["extra_fields"] if f["key"] == "reason")
        assert reason_field["type"] == "string"
        assert reason_field["required"] is False

    def test_dynamic_symbols_field_is_expression_only(self):
        schema = ExclusionListNode.get_field_schema()
        mode = schema["dynamic_symbols"].expression_mode
        val = mode.value if hasattr(mode, "value") else str(mode)
        assert "EXPRESSION_ONLY" in val.upper()

    def test_dynamic_symbols_not_required(self):
        schema = ExclusionListNode.get_field_schema()
        assert schema["dynamic_symbols"].required is False

    def test_input_symbols_field_is_expression_only(self):
        schema = ExclusionListNode.get_field_schema()
        mode = schema["input_symbols"].expression_mode
        val = mode.value if hasattr(mode, "value") else str(mode)
        assert "EXPRESSION_ONLY" in val.upper()

    def test_input_symbols_not_required(self):
        schema = ExclusionListNode.get_field_schema()
        assert schema["input_symbols"].required is False

    def test_default_reason_is_string(self):
        schema = ExclusionListNode.get_field_schema()
        type_val = schema["default_reason"].type
        val = type_val.value if hasattr(type_val, "value") else str(type_val)
        assert val == "string"

    def test_default_reason_not_required(self):
        schema = ExclusionListNode.get_field_schema()
        assert schema["default_reason"].required is False


# ============================================================
# NodeTypeRegistry 등록 테스트
# ============================================================


class TestExclusionListNodeRegistry:
    """NodeTypeRegistry 등록 검증"""

    def test_node_registered(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        assert registry.get("ExclusionListNode") is not None

    def test_node_schema(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        schema = registry.get_schema("ExclusionListNode")
        assert schema is not None
        assert schema.category == "market"
        assert schema.product_scope == "all"

    def test_node_in_market_category(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        market_types = registry.list_types(category="market")
        assert "ExclusionListNode" in market_types

    def test_node_product_scope_is_all(self):
        """ExclusionListNode의 product_scope이 'all'"""
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        schema = registry.get_schema("ExclusionListNode")
        assert schema.product_scope == "all"


# ============================================================
# AI Tool Schema 테스트
# ============================================================


class TestExclusionListNodeToolSchema:
    """AI Tool 스키마 검증"""

    def test_tool_schema_name(self):
        schema = ExclusionListNode.as_tool_schema()
        assert schema["tool_name"] == "exclusion_list"
        assert schema["node_type"] == "ExclusionListNode"

    def test_tool_schema_has_parameters(self):
        schema = ExclusionListNode.as_tool_schema()
        assert "symbols" in schema["parameters"]
        assert "default_reason" in schema["parameters"]

    def test_tool_schema_has_returns(self):
        schema = ExclusionListNode.as_tool_schema()
        assert "returns" in schema
        assert len(schema["returns"]) > 0

    def test_tool_schema_returns_include_excluded(self):
        schema = ExclusionListNode.as_tool_schema()
        assert "excluded" in schema["returns"]
        assert "filtered" in schema["returns"]
        assert "count" in schema["returns"]
        assert "reasons" in schema["returns"]
