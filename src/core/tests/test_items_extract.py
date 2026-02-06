"""
Test for items { from, extract } data binding pattern

Tests the new data binding approach for ConditionNode and BacktestEngineNode:
- from: source array to iterate over
- extract: field mapping using {{ row.xxx }} for current row access
"""

import pytest
from typing import Dict, Any


class TestConditionNodeItemsSchema:
    """ConditionNode items 스키마 테스트"""

    def test_items_field_exists(self):
        """ConditionNode에 items 필드가 존재"""
        from programgarden_core.nodes.condition import ConditionNode

        schema = ConditionNode.get_field_schema()
        assert "items" in schema

    def test_items_has_from_and_extract(self):
        """items에 from과 extract 서브스키마가 존재"""
        from programgarden_core.nodes.condition import ConditionNode

        schema = ConditionNode.get_field_schema()
        items_schema = schema["items"]

        assert items_schema.object_schema is not None
        sub_names = [s.get("name") for s in items_schema.object_schema]
        assert "from" in sub_names
        assert "extract" in sub_names

    def test_legacy_data_field_removed(self):
        """레거시 data 필드가 삭제됨"""
        from programgarden_core.nodes.condition import ConditionNode

        schema = ConditionNode.get_field_schema()
        assert "data" not in schema

    def test_legacy_field_mapping_removed(self):
        """레거시 field_mapping 필드들이 삭제됨"""
        from programgarden_core.nodes.condition import ConditionNode

        schema = ConditionNode.get_field_schema()
        legacy_fields = ["close_field", "open_field", "high_field", "low_field",
                        "volume_field", "date_field", "symbol_field", "exchange_field"]
        for field in legacy_fields:
            assert field not in schema, f"Legacy field {field} should be removed"

    def test_extract_has_required_fields(self):
        """extract 서브스키마에 필수 필드 정의가 있음"""
        from programgarden_core.nodes.condition import ConditionNode

        schema = ConditionNode.get_field_schema()
        items_schema = schema["items"]

        # extract 서브스키마 찾기
        extract_schema = None
        for sub in items_schema.object_schema:
            if sub.get("name") == "extract":
                extract_schema = sub
                break

        assert extract_schema is not None
        assert "object_schema" in extract_schema

        # extract 내 필드들
        extract_fields = [f.get("name") for f in extract_schema.get("object_schema", [])]
        assert "symbol" in extract_fields
        assert "exchange" in extract_fields
        assert "date" in extract_fields
        assert "close" in extract_fields


class TestBacktestEngineNodeItemsSchema:
    """BacktestEngineNode items 스키마 테스트"""

    def test_items_field_exists(self):
        """BacktestEngineNode에 items 필드가 존재"""
        from programgarden_core.nodes.backtest import BacktestEngineNode

        schema = BacktestEngineNode.get_field_schema()
        assert "items" in schema

    def test_items_has_from_and_extract(self):
        """items에 from과 extract 서브스키마가 존재"""
        from programgarden_core.nodes.backtest import BacktestEngineNode

        schema = BacktestEngineNode.get_field_schema()
        items_schema = schema["items"]

        assert items_schema.object_schema is not None
        sub_names = [s.get("name") for s in items_schema.object_schema]
        assert "from" in sub_names
        assert "extract" in sub_names

    def test_legacy_data_field_removed(self):
        """레거시 data 필드가 삭제됨"""
        from programgarden_core.nodes.backtest import BacktestEngineNode

        schema = BacktestEngineNode.get_field_schema()
        assert "data" not in schema

    def test_extract_has_ohlcv_fields(self):
        """extract 서브스키마에 OHLCV 필드들이 있음"""
        from programgarden_core.nodes.backtest import BacktestEngineNode

        schema = BacktestEngineNode.get_field_schema()
        items_schema = schema["items"]

        # extract 서브스키마 찾기
        extract_schema = None
        for sub in items_schema.object_schema:
            if sub.get("name") == "extract":
                extract_schema = sub
                break

        assert extract_schema is not None
        extract_fields = [f.get("name") for f in extract_schema.get("object_schema", [])]

        # BacktestEngineNode에는 OHLCV + signal 필드가 필요
        assert "open" in extract_fields
        assert "high" in extract_fields
        assert "low" in extract_fields
        assert "close" in extract_fields
        assert "signal" in extract_fields


class TestPluginRequiredFields:
    """플러그인 required_fields 테스트"""

    def test_rsi_required_fields(self):
        """RSI 플러그인에 required_fields가 정의됨"""
        from programgarden_core.registry import PluginRegistry

        # 플러그인 레지스트리 초기화
        try:
            import programgarden_community
        except ImportError:
            pytest.skip("programgarden_community not installed")

        registry = PluginRegistry()
        schema = registry.get_schema("RSI")

        if schema:
            assert hasattr(schema, 'required_fields')
            assert "symbol" in schema.required_fields
            assert "exchange" in schema.required_fields
            assert "date" in schema.required_fields
            assert "close" in schema.required_fields

    def test_macd_required_fields(self):
        """MACD 플러그인에 required_fields가 정의됨"""
        from programgarden_core.registry import PluginRegistry

        try:
            import programgarden_community
        except ImportError:
            pytest.skip("programgarden_community not installed")

        registry = PluginRegistry()
        schema = registry.get_schema("MACD")

        if schema:
            assert hasattr(schema, 'required_fields')
            assert "symbol" in schema.required_fields
            assert "close" in schema.required_fields

    def test_volume_spike_required_fields(self):
        """VolumeSpike 플러그인에 volume 필드가 필수"""
        from programgarden_core.registry import PluginRegistry

        try:
            import programgarden_community
        except ImportError:
            pytest.skip("programgarden_community not installed")

        registry = PluginRegistry()
        schema = registry.get_schema("VolumeSpike")

        if schema:
            assert hasattr(schema, 'required_fields')
            assert "volume" in schema.required_fields

    def test_positions_based_plugin_no_required_fields(self):
        """ProfitTarget, StopLoss 플러그인은 items 불필요 (positions 사용)"""
        from programgarden_core.registry import PluginRegistry

        try:
            import programgarden_community
        except ImportError:
            pytest.skip("programgarden_community not installed")

        registry = PluginRegistry()

        for plugin_id in ["ProfitTarget", "StopLoss"]:
            schema = registry.get_schema(plugin_id)
            if schema:
                # positions 기반 플러그인은 required_fields가 비어있음
                assert hasattr(schema, 'required_fields')
                assert schema.required_fields == []


class TestPluginSchemaDefaults:
    """PluginSchema 기본값 테스트"""

    def test_plugin_schema_has_required_fields_attribute(self):
        """PluginSchema에 required_fields와 optional_fields 속성이 있음"""
        from programgarden_core.registry.plugin_registry import PluginSchema, PluginCategory

        schema = PluginSchema(
            id="test",
            category=PluginCategory.TECHNICAL,
        )

        assert hasattr(schema, 'required_fields')
        assert hasattr(schema, 'optional_fields')

    def test_plugin_schema_default_required_fields(self):
        """PluginSchema 기본 required_fields는 symbol, exchange, date, close"""
        from programgarden_core.registry.plugin_registry import PluginSchema, PluginCategory

        schema = PluginSchema(
            id="test",
            category=PluginCategory.TECHNICAL,
        )

        # 기본값 확인
        assert "symbol" in schema.required_fields
        assert "exchange" in schema.required_fields
        assert "date" in schema.required_fields
        assert "close" in schema.required_fields


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
