"""
PluginRegistry 동적 플러그인 등록 테스트

register_dynamic() 충돌 방지, unregister_dynamic() 해제 검증
"""

import pytest
from programgarden_core.registry.plugin_registry import (
    PluginSchema,
    PluginCategory,
    PluginRegistry,
)


# ─────────────────────────────────────────────────
# 테스트용 플러그인 함수
# ─────────────────────────────────────────────────

async def my_custom_plugin(data, fields, **kwargs):
    return {"passed_symbols": [], "result": True, "values": []}


async def another_plugin(data, fields, **kwargs):
    return {"passed_symbols": [], "result": False, "values": []}


# ─────────────────────────────────────────────────
# Fixture
# ─────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_registry():
    """각 테스트 전후 레지스트리 초기화"""
    registry = PluginRegistry()
    original_plugins = dict(registry._plugins)
    original_schemas = dict(registry._schemas)
    yield
    registry._plugins = original_plugins
    registry._schemas = original_schemas


@pytest.fixture
def schema():
    return PluginSchema(
        id="MyDynamic",
        category=PluginCategory.TECHNICAL,
        description="동적 등록 테스트 플러그인",
        fields_schema={"period": {"type": "int", "default": 14}},
    )


# ─────────────────────────────────────────────────
# register_dynamic 테스트
# ─────────────────────────────────────────────────

class TestRegisterDynamic:
    """동적 플러그인 등록"""

    def test_register_dynamic_success(self, schema):
        """정상 등록"""
        registry = PluginRegistry()
        registry.register_dynamic("MyDynamic", my_custom_plugin, schema)

        assert registry.get("MyDynamic") is my_custom_plugin
        assert registry.get_schema("MyDynamic") is not None

    def test_register_dynamic_conflict_raises(self, schema):
        """기존 플러그인과 ID 충돌 시 ValueError"""
        registry = PluginRegistry()
        registry.register_dynamic("MyDynamic", my_custom_plugin, schema)

        schema2 = PluginSchema(id="MyDynamic", category=PluginCategory.TECHNICAL)
        with pytest.raises(ValueError, match="already registered"):
            registry.register_dynamic("MyDynamic", another_plugin, schema2)

    def test_conflict_error_includes_existing_info(self):
        """충돌 에러 메시지에 기존 플러그인 정보 포함"""
        registry = PluginRegistry()
        schema = PluginSchema(
            id="ConflictTest",
            category=PluginCategory.TECHNICAL,
            version="2.0.0",
            author="original_author",
        )
        registry.register_dynamic("ConflictTest", my_custom_plugin, schema)

        schema2 = PluginSchema(id="ConflictTest", category=PluginCategory.TECHNICAL)
        with pytest.raises(ValueError, match="version=2.0.0.*author=original_author"):
            registry.register_dynamic("ConflictTest", another_plugin, schema2)

    def test_conflict_with_community_plugin(self):
        """community 플러그인(register)과 동적 플러그인(register_dynamic) 충돌"""
        registry = PluginRegistry()
        # community 방식 등록 (기존)
        schema = PluginSchema(id="RSI_Clone", category=PluginCategory.TECHNICAL)
        registry.register("RSI_Clone", my_custom_plugin, schema)

        # 동적 등록 시도 → 충돌
        schema2 = PluginSchema(id="RSI_Clone", category=PluginCategory.TECHNICAL)
        with pytest.raises(ValueError, match="already registered"):
            registry.register_dynamic("RSI_Clone", another_plugin, schema2)

    def test_not_callable_raises(self, schema):
        """callable이 아닌 객체 전달 시 TypeError"""
        registry = PluginRegistry()
        with pytest.raises(TypeError, match="must be callable"):
            registry.register_dynamic("MyDynamic", "not_a_function", schema)

    def test_not_callable_error_includes_plugin_id(self, schema):
        """TypeError 메시지에 plugin_id 포함"""
        registry = PluginRegistry()
        with pytest.raises(TypeError, match="MyDynamic"):
            registry.register_dynamic("MyDynamic", 42, schema)

    def test_register_dynamic_appears_in_list(self, schema):
        """동적 등록 플러그인이 list_plugins에 포함"""
        registry = PluginRegistry()
        registry.register_dynamic("MyDynamic", my_custom_plugin, schema)

        plugins = registry.list_plugins(category=PluginCategory.TECHNICAL)
        ids = [p.id for p in plugins]
        assert "MyDynamic" in ids

    def test_register_dynamic_searchable(self, schema):
        """동적 등록 플러그인이 search에서 검색됨"""
        registry = PluginRegistry()
        registry.register_dynamic("MyDynamic", my_custom_plugin, schema)

        results = registry.search("MyDynamic")
        assert len(results) >= 1
        assert results[0].id == "MyDynamic"
