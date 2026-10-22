"""
PluginSchema output_fields 테스트

output_fields 필드 추가, 조회, to_localized_dict() 포함 검증
"""

import pytest
from programgarden_core.registry.plugin_registry import (
    PluginSchema,
    PluginCategory,
    PluginRegistry,
)


class TestPluginSchemaOutputFields:
    """PluginSchema.output_fields 테스트"""

    def test_output_fields_default_empty_dict(self):
        """output_fields 미지정 시 빈 dict 기본값"""
        schema = PluginSchema(id="test", category=PluginCategory.TECHNICAL)
        assert schema.output_fields == {}

    def test_output_fields_with_values(self):
        """output_fields 값 지정"""
        schema = PluginSchema(
            id="RSI",
            category=PluginCategory.TECHNICAL,
            output_fields={
                "rsi": {"type": "float", "description": "RSI value (0-100)"},
                "current_price": {"type": "float", "description": "Latest closing price"},
            },
        )
        assert len(schema.output_fields) == 2
        assert schema.output_fields["rsi"]["type"] == "float"
        assert "RSI" in schema.output_fields["rsi"]["description"]

    def test_output_fields_various_types(self):
        """다양한 type 값 지원"""
        schema = PluginSchema(
            id="test",
            category=PluginCategory.TECHNICAL,
            output_fields={
                "value": {"type": "float", "description": "A float value"},
                "count": {"type": "int", "description": "An integer count"},
                "name": {"type": "str", "description": "A string name"},
                "active": {"type": "bool", "description": "A boolean flag"},
                "items": {"type": "list", "description": "A list of items"},
                "data": {"type": "dict", "description": "A dictionary"},
            },
        )
        assert len(schema.output_fields) == 6
        assert schema.output_fields["count"]["type"] == "int"
        assert schema.output_fields["active"]["type"] == "bool"


class TestGetOutputFieldDescription:
    """get_output_field_description() 테스트"""

    def test_existing_field(self):
        """존재하는 필드의 설명 조회"""
        schema = PluginSchema(
            id="RSI",
            category=PluginCategory.TECHNICAL,
            output_fields={
                "rsi": {"type": "float", "description": "RSI value (0-100)"},
            },
        )
        assert schema.get_output_field_description("rsi") == "RSI value (0-100)"

    def test_nonexistent_field(self):
        """존재하지 않는 필드 → 빈 문자열"""
        schema = PluginSchema(id="test", category=PluginCategory.TECHNICAL)
        assert schema.get_output_field_description("nonexistent") == ""

    def test_field_without_description(self):
        """description 키 없는 필드 → 빈 문자열"""
        schema = PluginSchema(
            id="test",
            category=PluginCategory.TECHNICAL,
            output_fields={"val": {"type": "float"}},
        )
        assert schema.get_output_field_description("val") == ""

    def test_empty_output_fields(self):
        """output_fields가 빈 dict일 때"""
        schema = PluginSchema(
            id="test",
            category=PluginCategory.TECHNICAL,
            output_fields={},
        )
        assert schema.get_output_field_description("anything") == ""


class TestToLocalizedDictOutputFields:
    """to_localized_dict()에 output_fields 포함 확인"""

    def test_output_fields_included(self):
        """to_localized_dict() 결과에 output_fields 포함"""
        schema = PluginSchema(
            id="RSI",
            category=PluginCategory.TECHNICAL,
            output_fields={
                "rsi": {"type": "float", "description": "RSI value"},
            },
        )
        result = schema.to_localized_dict("en")
        assert "output_fields" in result
        assert result["output_fields"]["rsi"]["type"] == "float"

    def test_empty_output_fields_included(self):
        """output_fields 빈 dict도 포함"""
        schema = PluginSchema(id="test", category=PluginCategory.TECHNICAL)
        result = schema.to_localized_dict("en")
        assert "output_fields" in result
        assert result["output_fields"] == {}

    def test_model_dump_includes_output_fields(self):
        """model_dump()에도 output_fields 포함"""
        schema = PluginSchema(
            id="test",
            category=PluginCategory.TECHNICAL,
            output_fields={"val": {"type": "int", "description": "test"}},
        )
        dumped = schema.model_dump()
        assert "output_fields" in dumped
        assert dumped["output_fields"]["val"]["type"] == "int"


class TestPluginRegistryWithOutputFields:
    """PluginRegistry에서 output_fields 전달 테스트"""

    def setup_method(self):
        """테스트 전 레지스트리 초기화"""
        PluginRegistry._instance = None

    def test_register_and_retrieve_output_fields(self):
        """등록 후 스키마 조회 시 output_fields 보존"""
        registry = PluginRegistry()
        schema = PluginSchema(
            id="TestPlugin",
            category=PluginCategory.TECHNICAL,
            output_fields={
                "indicator": {"type": "float", "description": "Indicator value"},
            },
        )
        registry.register("TestPlugin", lambda: None, schema)

        retrieved = registry.get_schema("TestPlugin")
        assert retrieved is not None
        assert "indicator" in retrieved.output_fields
        assert retrieved.output_fields["indicator"]["type"] == "float"

    def test_list_plugins_with_locale_includes_output_fields(self):
        """list_plugins(locale=...) 결과에 output_fields 포함"""
        registry = PluginRegistry()
        schema = PluginSchema(
            id="TestPlugin2",
            category=PluginCategory.TECHNICAL,
            output_fields={
                "value": {"type": "float", "description": "Test value"},
            },
        )
        registry.register("TestPlugin2", lambda: None, schema)

        plugins = registry.list_plugins(locale="en")
        found = [p for p in plugins if p["id"] == "TestPlugin2"]
        assert len(found) == 1
        assert "output_fields" in found[0]
        assert "value" in found[0]["output_fields"]

    def teardown_method(self):
        """테스트 후 레지스트리 초기화"""
        PluginRegistry._instance = None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
