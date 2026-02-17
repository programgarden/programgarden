"""
IfNode 단위 테스트

테스트 대상:
1. IfNode 모델 생성 및 필드 검증
2. FieldSchema 구조 검증
3. 출력 포트 (true, false, result) 검증
4. Edge from_port 필드 동작
"""

import pytest
from programgarden_core.nodes.infra import IfNode
from programgarden_core.nodes.base import NodeCategory
from programgarden_core.models.edge import Edge


class TestIfNodeModel:
    """IfNode 모델 테스트"""

    def test_if_node_has_correct_type(self):
        node = IfNode(id="if1")
        assert node.type == "IfNode"

    def test_if_node_category_is_infra(self):
        node = IfNode(id="if1")
        assert node.category == NodeCategory.INFRA

    def test_if_node_default_operator(self):
        node = IfNode(id="if1")
        assert node.operator == "=="

    def test_if_node_default_values(self):
        node = IfNode(id="if1")
        assert node.left is None
        assert node.right is None

    def test_if_node_custom_values(self):
        node = IfNode(id="if1", left=100, operator=">=", right=50)
        assert node.left == 100
        assert node.operator == ">="
        assert node.right == 50

    def test_if_node_all_operators(self):
        operators = [
            "==", "!=", ">", ">=", "<", "<=",
            "in", "not_in",
            "contains", "not_contains",
            "is_empty", "is_not_empty",
        ]
        for op in operators:
            node = IfNode(id="if1", operator=op)
            assert node.operator == op

    def test_if_node_input_ports(self):
        node = IfNode(id="if1")
        input_names = [p.name for p in node._inputs]
        assert "trigger" in input_names

    def test_if_node_output_ports(self):
        node = IfNode(id="if1")
        output_names = [p.name for p in node._outputs]
        assert "true" in output_names
        assert "false" in output_names
        assert "result" in output_names

    def test_if_node_description_is_i18n(self):
        node = IfNode(id="if1")
        assert node.description.startswith("i18n:")


class TestIfNodeFieldSchema:
    """IfNode FieldSchema 테스트"""

    def test_field_schema_has_all_fields(self):
        schema = IfNode.get_field_schema()
        assert "left" in schema
        assert "operator" in schema
        assert "right" in schema

    def test_left_field_supports_expression(self):
        schema = IfNode.get_field_schema()
        left = schema["left"]
        mode = left.expression_mode
        assert (mode == "both") or (hasattr(mode, 'value') and mode.value == "both")

    def test_operator_field_is_fixed_only(self):
        schema = IfNode.get_field_schema()
        op = schema["operator"]
        mode = op.expression_mode
        assert (mode == "fixed_only") or (hasattr(mode, 'value') and mode.value == "fixed_only")

    def test_operator_has_12_enum_values(self):
        schema = IfNode.get_field_schema()
        op = schema["operator"]
        assert len(op.enum_values) == 12

    def test_right_field_visible_when(self):
        """right 필드는 is_empty/is_not_empty에서는 숨김"""
        schema = IfNode.get_field_schema()
        right = schema["right"]
        assert right.visible_when is not None
        # is_empty, is_not_empty는 visible_when에 포함되지 않음
        visible_ops = right.visible_when["operator"]
        assert "is_empty" not in visible_ops
        assert "is_not_empty" not in visible_ops
        assert "==" in visible_ops


class TestEdgeFromPort:
    """Edge from_port 필드 테스트"""

    def test_edge_from_port_explicit(self):
        """명시적 from_port 지정"""
        edge = Edge(**{"from": "if1", "to": "order", "from_port": "true"})
        assert edge.from_node == "if1"
        assert edge.to_node == "order"
        assert edge.from_port == "true"

    def test_edge_from_port_dot_notation(self):
        """dot notation에서 from_port 자동 추출"""
        edge = Edge(**{"from": "if1.true", "to": "order"})
        assert edge.from_node == "if1"
        assert edge.from_port == "true"

    def test_edge_from_port_dot_notation_false(self):
        edge = Edge(**{"from": "if1.false", "to": "notify"})
        assert edge.from_node == "if1"
        assert edge.from_port == "false"

    def test_edge_from_port_none_by_default(self):
        """from_port가 없으면 None"""
        edge = Edge(**{"from": "broker", "to": "condition"})
        assert edge.from_port is None

    def test_edge_backward_compat(self):
        """기존 엣지 호환성 - from_port 없어도 동작"""
        edge = Edge(**{"from": "start", "to": "broker"})
        assert edge.from_node == "start"
        assert edge.to_node == "broker"
        assert edge.from_port is None
        assert edge.is_dag_edge is True

    def test_edge_explicit_port_overrides_dot(self):
        """명시적 from_port가 dot notation보다 우선"""
        edge = Edge(**{"from": "if1.true", "to": "order", "from_port": "false"})
        assert edge.from_port == "false"

    def test_edge_from_node_id_property(self):
        """하위호환 property"""
        edge = Edge(**{"from": "if1", "to": "order", "from_port": "true"})
        assert edge.from_node_id == "if1"
        assert edge.to_node_id == "order"


class TestIfNodeRegistry:
    """IfNode 레지스트리 등록 테스트"""

    def test_if_node_in_registry(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        assert registry.get("IfNode") is not None

    def test_if_node_schema_in_registry(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        schema = registry.get_schema("IfNode")
        assert schema is not None
        assert schema.category == "infra"

    def test_if_node_listed_in_infra(self):
        from programgarden_core.registry.node_registry import NodeTypeRegistry
        registry = NodeTypeRegistry()
        infra_types = registry.list_types(category="infra")
        assert "IfNode" in infra_types
