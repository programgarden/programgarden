"""
DynamicNodeRegistry 단위 테스트

동적 노드 스키마 등록, 클래스 주입, 검증 로직 테스트
"""

import pytest
from typing import Dict, Any, List

from programgarden_core.registry import (
    DynamicNodeRegistry,
    DynamicNodeSchema,
    DYNAMIC_NODE_PREFIX,
    is_dynamic_node_type,
)
from programgarden_core.nodes.base import BaseNode, NodeCategory, OutputPort


# ─────────────────────────────────────────────────
# 테스트용 노드 클래스
# ─────────────────────────────────────────────────

class ValidCustomNode(BaseNode):
    """유효한 커스텀 노드 (테스트용)"""
    category: NodeCategory = NodeCategory.DATA
    _outputs: List[OutputPort] = [
        OutputPort(name="rsi", type="number"),
        OutputPort(name="signal", type="string"),
    ]

    async def execute(self, context) -> Dict[str, Any]:
        return {"rsi": 50.0, "signal": "neutral"}


class MissingExecuteNode(BaseNode):
    """execute() 메서드가 없는 노드 (테스트용)"""
    category: NodeCategory = NodeCategory.DATA
    _outputs: List[OutputPort] = [
        OutputPort(name="value", type="number"),
    ]
    # execute() 메서드 없음


class WrongOutputsNode(BaseNode):
    """스키마와 다른 출력 포트를 가진 노드 (테스트용)"""
    category: NodeCategory = NodeCategory.DATA
    _outputs: List[OutputPort] = [
        OutputPort(name="wrong_port", type="string"),  # 스키마와 불일치
    ]

    async def execute(self, context) -> Dict[str, Any]:
        return {"wrong_port": "test"}


class NotABaseNode:
    """BaseNode를 상속하지 않은 클래스 (테스트용)"""
    async def execute(self, context):
        return {}


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
def sample_schema():
    """테스트용 스키마"""
    return DynamicNodeSchema(
        node_type="Custom_MyRSI",
        category="condition",
        description="커스텀 RSI 지표 노드",
        inputs=[{"name": "data", "type": "array", "required": True}],
        outputs=[
            {"name": "rsi", "type": "number"},
            {"name": "signal", "type": "string"},
        ],
        config_schema={
            "period": {"type": "integer", "default": 14}
        },
    )


# ─────────────────────────────────────────────────
# 스키마 관리 테스트
# ─────────────────────────────────────────────────

class TestSchemaRegistration:
    """스키마 등록 관련 테스트"""

    def test_register_schema_success(self, sample_schema):
        """스키마 등록 성공"""
        registry = DynamicNodeRegistry()
        registry.register_schema(sample_schema)

        assert registry.get_schema("Custom_MyRSI") is not None
        assert registry.get_schema("Custom_MyRSI").category == "condition"

    def test_register_schema_without_prefix_fails(self):
        """Custom_ prefix 없이 등록하면 실패"""
        registry = DynamicNodeRegistry()
        schema = DynamicNodeSchema(node_type="MyRSI", category="condition")

        with pytest.raises(ValueError, match="Custom_"):
            registry.register_schema(schema)

    def test_register_schemas_batch(self):
        """여러 스키마 일괄 등록"""
        registry = DynamicNodeRegistry()
        schemas = [
            DynamicNodeSchema(node_type="Custom_A", category="data"),
            DynamicNodeSchema(node_type="Custom_B", category="condition"),
        ]
        registry.register_schemas(schemas)

        assert len(registry.list_schema_types()) == 2
        assert "Custom_A" in registry.list_schema_types()
        assert "Custom_B" in registry.list_schema_types()

    def test_list_schemas(self, sample_schema):
        """스키마 목록 조회"""
        registry = DynamicNodeRegistry()
        registry.register_schema(sample_schema)

        schemas = registry.list_schemas()
        assert len(schemas) == 1
        assert schemas[0].node_type == "Custom_MyRSI"

    def test_get_schema_not_found(self):
        """미등록 스키마 조회 시 None 반환"""
        registry = DynamicNodeRegistry()
        assert registry.get_schema("Custom_NotExists") is None

    def test_is_schema_registered(self, sample_schema):
        """스키마 등록 여부 확인"""
        registry = DynamicNodeRegistry()

        assert not registry.is_schema_registered("Custom_MyRSI")
        registry.register_schema(sample_schema)
        assert registry.is_schema_registered("Custom_MyRSI")


# ─────────────────────────────────────────────────
# 클래스 주입 테스트
# ─────────────────────────────────────────────────

class TestClassInjection:
    """클래스 주입 관련 테스트"""

    def test_inject_node_class_success(self, sample_schema):
        """클래스 주입 성공"""
        registry = DynamicNodeRegistry()
        registry.register_schema(sample_schema)

        registry.inject_node_class("Custom_MyRSI", ValidCustomNode)

        assert registry.get_node_class("Custom_MyRSI") is not None
        assert registry.is_class_injected("Custom_MyRSI")

    def test_inject_without_schema_fails(self):
        """스키마 없이 클래스 주입 시 실패"""
        registry = DynamicNodeRegistry()

        with pytest.raises(ValueError, match="스키마가 등록되지 않은"):
            registry.inject_node_class("Custom_MyRSI", ValidCustomNode)

    def test_inject_non_basenode_fails(self, sample_schema):
        """BaseNode를 상속하지 않은 클래스 주입 시 실패"""
        registry = DynamicNodeRegistry()
        registry.register_schema(sample_schema)

        with pytest.raises(TypeError, match="BaseNode를 상속"):
            registry.inject_node_class("Custom_MyRSI", NotABaseNode)

    def test_inject_without_execute_fails(self, sample_schema):
        """execute() 메서드가 없는 클래스 주입 시 실패"""
        registry = DynamicNodeRegistry()
        registry.register_schema(sample_schema)

        with pytest.raises(TypeError, match="execute\\(\\) 메서드"):
            registry.inject_node_class("Custom_MyRSI", MissingExecuteNode)

    def test_inject_with_wrong_outputs_fails(self, sample_schema):
        """출력 포트가 불일치하는 클래스 주입 시 실패"""
        registry = DynamicNodeRegistry()
        registry.register_schema(sample_schema)

        with pytest.raises(ValueError, match="output 포트가 클래스에 없음"):
            registry.inject_node_class("Custom_MyRSI", WrongOutputsNode)

    def test_inject_node_classes_batch(self):
        """여러 클래스 일괄 주입"""
        registry = DynamicNodeRegistry()

        # 스키마 등록
        registry.register_schema(DynamicNodeSchema(
            node_type="Custom_A",
            outputs=[{"name": "rsi", "type": "number"}, {"name": "signal", "type": "string"}],
        ))
        registry.register_schema(DynamicNodeSchema(
            node_type="Custom_B",
            outputs=[{"name": "rsi", "type": "number"}, {"name": "signal", "type": "string"}],
        ))

        # 클래스 주입
        registry.inject_node_classes({
            "Custom_A": ValidCustomNode,
            "Custom_B": ValidCustomNode,
        })

        assert registry.is_class_injected("Custom_A")
        assert registry.is_class_injected("Custom_B")

    def test_get_node_class_not_injected(self, sample_schema):
        """클래스 미주입 시 None 반환"""
        registry = DynamicNodeRegistry()
        registry.register_schema(sample_schema)

        assert registry.get_node_class("Custom_MyRSI") is None
        assert not registry.is_class_injected("Custom_MyRSI")


# ─────────────────────────────────────────────────
# 유틸리티 테스트
# ─────────────────────────────────────────────────

class TestUtilities:
    """유틸리티 메서드 테스트"""

    def test_clear_injected_classes(self, sample_schema):
        """주입된 클래스만 초기화 (스키마 유지)"""
        registry = DynamicNodeRegistry()
        registry.register_schema(sample_schema)
        registry.inject_node_class("Custom_MyRSI", ValidCustomNode)

        registry.clear_injected_classes()

        # 스키마는 유지
        assert registry.get_schema("Custom_MyRSI") is not None
        # 클래스는 제거
        assert registry.get_node_class("Custom_MyRSI") is None

    def test_unregister(self, sample_schema):
        """스키마 및 클래스 모두 제거"""
        registry = DynamicNodeRegistry()
        registry.register_schema(sample_schema)
        registry.inject_node_class("Custom_MyRSI", ValidCustomNode)

        result = registry.unregister("Custom_MyRSI")

        assert result is True
        assert registry.get_schema("Custom_MyRSI") is None
        assert registry.get_node_class("Custom_MyRSI") is None

    def test_unregister_not_found(self):
        """미등록 노드 제거 시 False 반환"""
        registry = DynamicNodeRegistry()
        assert registry.unregister("Custom_NotExists") is False

    def test_clear_all(self, sample_schema):
        """모든 스키마 및 클래스 초기화"""
        registry = DynamicNodeRegistry()
        registry.register_schema(sample_schema)
        registry.inject_node_class("Custom_MyRSI", ValidCustomNode)

        registry.clear_all()

        assert len(registry.list_schema_types()) == 0
        assert registry.get_node_class("Custom_MyRSI") is None


# ─────────────────────────────────────────────────
# 헬퍼 함수 테스트
# ─────────────────────────────────────────────────

class TestHelperFunctions:
    """헬퍼 함수 테스트"""

    def test_is_dynamic_node_type(self):
        """동적 노드 타입 판별"""
        assert is_dynamic_node_type("Custom_MyRSI") is True
        assert is_dynamic_node_type("Custom_MACD") is True
        assert is_dynamic_node_type("OverseasStockBrokerNode") is False
        assert is_dynamic_node_type("ConditionNode") is False

    def test_dynamic_node_prefix(self):
        """Prefix 상수 확인"""
        assert DYNAMIC_NODE_PREFIX == "Custom_"


# ─────────────────────────────────────────────────
# 싱글톤 패턴 테스트
# ─────────────────────────────────────────────────

class TestSingleton:
    """싱글톤 패턴 테스트"""

    def test_singleton_instance(self, sample_schema):
        """싱글톤 인스턴스 확인"""
        registry1 = DynamicNodeRegistry()
        registry2 = DynamicNodeRegistry()

        registry1.register_schema(sample_schema)

        # 같은 인스턴스
        assert registry1 is registry2
        # 데이터 공유
        assert registry2.get_schema("Custom_MyRSI") is not None

    def test_reset_instance(self, sample_schema):
        """인스턴스 리셋 테스트"""
        registry1 = DynamicNodeRegistry()
        registry1.register_schema(sample_schema)

        DynamicNodeRegistry.reset_instance()

        registry2 = DynamicNodeRegistry()
        assert registry2.get_schema("Custom_MyRSI") is None
