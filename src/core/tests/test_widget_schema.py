"""
FieldSchema.to_config_dict() 및 NodeTypeRegistry config_schema 테스트
"""

import pytest
from programgarden_core.models.field_binding import (
    FieldSchema,
    FieldType,
    FieldCategory,
    UIComponent,
    ExpressionMode,
)
from programgarden_core.registry import NodeTypeRegistry


class TestFieldSchemaToConfigDict:
    """FieldSchema.to_config_dict() 메서드 테스트

    config_schema 형식:
    - type: 필드 타입
    - display_name: 표시 이름 (i18n 키 또는 직접 값)
    - required: 필수 여부
    - category: parameters | settings
    - expression_mode: fixed_only | expression_only | both
    """

    def test_text_input_fixed_only(self):
        """기본 텍스트 입력 필드 (FIXED_ONLY)"""
        fs = FieldSchema(
            name="test_field",
            type=FieldType.STRING,
            description="테스트 필드",
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        config = fs.to_config_dict("TestNode")

        assert config["type"] == "string"
        assert config["display_name"] == "i18n:fieldNames.TestNode.test_field"
        assert config["expression_mode"] == "fixed_only"
        assert config["description"] == "테스트 필드"
        assert config["required"] is False

    def test_number_input_with_default(self):
        """숫자 입력 필드 (기본값 포함)"""
        fs = FieldSchema(
            name="period",
            type=FieldType.INTEGER,
            description="기간",
            default=14,
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        config = fs.to_config_dict("TestNode")

        assert config["type"] == "integer"
        assert config["default"] == 14
        assert config["description"] == "기간"

    def test_enum_select(self):
        """드롭다운 선택 필드 (ENUM)"""
        fs = FieldSchema(
            name="provider",
            type=FieldType.ENUM,
            description="증권사",
            default="ls-sec.co.kr",
            enum_values=["ls-sec.co.kr"],
            enum_labels={"ls-sec.co.kr": "LS증권"},
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        config = fs.to_config_dict("BrokerNode")

        assert config["type"] == "enum"
        assert config["enum_values"] == ["ls-sec.co.kr"]
        assert config["enum_labels"] == {"ls-sec.co.kr": "LS증권"}
        assert config["default"] == "ls-sec.co.kr"

    def test_boolean_field(self):
        """체크박스 필드 (BOOLEAN)"""
        fs = FieldSchema(
            name="adjust",
            type=FieldType.BOOLEAN,
            description="수정주가 적용",
            default=True,
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        config = fs.to_config_dict("TestNode")

        assert config["type"] == "boolean"
        assert config["default"] is True

    def test_expression_only_mode(self):
        """EXPRESSION_ONLY 모드"""
        fs = FieldSchema(
            name="data",
            type=FieldType.OBJECT,
            description="입력 데이터",
            expression_mode=ExpressionMode.EXPRESSION_ONLY,
            example_binding="{{ nodes.source.values }}",
        )
        config = fs.to_config_dict("TestNode")

        assert config["expression_mode"] == "expression_only"
        assert config["example_binding"] == "{{ nodes.source.values }}"

    def test_credential_field(self):
        """Credential 선택 필드"""
        fs = FieldSchema(
            name="credential_id",
            type=FieldType.CREDENTIAL,
            description="Credential 선택",
            ui_component=UIComponent.CUSTOM_CREDENTIAL_SELECT,
            credential_types=["broker_ls_stock", "broker_ls_futures"],
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        config = fs.to_config_dict("BrokerNode")

        assert config["type"] == "credential"
        assert config["ui_component"] == "custom_credential_select"
        assert config["credential_types"] == ["broker_ls_stock", "broker_ls_futures"]

    def test_plugin_select(self):
        """플러그인 선택 필드"""
        fs = FieldSchema(
            name="plugin",
            type=FieldType.STRING,
            description="플러그인 선택",
            ui_component=UIComponent.CUSTOM_PLUGIN_SELECT,
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        config = fs.to_config_dict("ConditionNode")

        assert config["ui_component"] == "custom_plugin_select"

    def test_symbol_editor(self):
        """종목 편집기 (커스텀 위젯)"""
        fs = FieldSchema(
            name="symbols",
            type=FieldType.ARRAY,
            description="종목 리스트",
            expression_mode=ExpressionMode.BOTH,
            ui_component=UIComponent.CUSTOM_SYMBOL_EDITOR,
        )
        config = fs.to_config_dict("WatchlistNode")

        assert config["ui_component"] == "custom_symbol_editor"
        assert config["expression_mode"] == "both"

    def test_display_name_override(self):
        """display_name 직접 지정"""
        fs = FieldSchema(
            name="api_key",
            type=FieldType.STRING,
            display_name="API 키",
            description="인증용 API 키",
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        config = fs.to_config_dict("TestNode")

        # display_name이 직접 지정되면 그대로 사용
        assert config["display_name"] == "API 키"

    def test_visible_when(self):
        """visible_when 조건부 표시"""
        fs = FieldSchema(
            name="new_price",
            type=FieldType.NUMBER,
            description="정정 가격",
            expression_mode=ExpressionMode.BOTH,
            visible_when={"price_type": "limit"},
        )
        config = fs.to_config_dict("ModifyOrderNode")

        assert config["visible_when"] == {"price_type": "limit"}

    def test_sub_fields(self):
        """object_schema -> sub_fields 변환"""
        fs = FieldSchema(
            name="symbol",
            type=FieldType.OBJECT,
            description="종목",
            expression_mode=ExpressionMode.EXPRESSION_ONLY,
            object_schema=[
                {"name": "exchange", "type": "STRING"},
                {"name": "symbol", "type": "STRING"},
            ],
        )
        config = fs.to_config_dict("MarketDataNode")

        assert "sub_fields" in config
        assert len(config["sub_fields"]) == 2
        assert config["sub_fields"][0]["name"] == "exchange"

    def test_settings_category(self):
        """SETTINGS 카테고리 필드"""
        fs = FieldSchema(
            name="timeout",
            type=FieldType.INTEGER,
            description="타임아웃 (초)",
            category=FieldCategory.SETTINGS,
            default=30,
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        config = fs.to_config_dict("HTTPRequestNode")

        assert config["category"] == "settings"


class TestNodeTypeRegistryConfigSchema:
    """NodeTypeRegistry config_schema 생성 테스트"""

    def test_broker_node_config_schema(self):
        """BrokerNode의 config_schema 생성 확인"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("OverseasStockBrokerNode")

        assert schema is not None
        assert schema.config_schema is not None
        assert "provider" in schema.config_schema
        assert "credential_id" in schema.config_schema

        # provider 필드 확인
        provider = schema.config_schema["provider"]
        assert provider["type"] == "enum"
        assert provider["expression_mode"] == "fixed_only"
        assert "enum_values" in provider

    def test_watchlist_node_config_schema(self):
        """WatchlistNode의 config_schema 생성 확인"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("WatchlistNode")

        assert schema is not None
        assert "symbols" in schema.config_schema

        symbols = schema.config_schema["symbols"]
        assert symbols["ui_component"] == "custom_symbol_editor"

    def test_condition_node_config_schema(self):
        """ConditionNode의 config_schema 생성 확인"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("ConditionNode")

        assert schema is not None
        assert "plugin" in schema.config_schema
        assert "items" in schema.config_schema

        plugin = schema.config_schema["plugin"]
        assert plugin["ui_component"] == "custom_plugin_select"

    def test_throttle_node_config_schema(self):
        """ThrottleNode의 config_schema (설정 필드 포함)"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("ThrottleNode")

        assert schema is not None
        assert "mode" in schema.config_schema
        assert "interval_sec" in schema.config_schema
        assert "pass_first" in schema.config_schema

        mode = schema.config_schema["mode"]
        assert mode["type"] == "enum"
        assert "skip" in mode["enum_values"]
        assert "latest" in mode["enum_values"]

    def test_logic_node_visible_when(self):
        """LogicNode의 visible_when 확인"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("LogicNode")

        assert schema is not None
        assert "threshold" in schema.config_schema

        threshold = schema.config_schema["threshold"]
        assert "visible_when" in threshold
        assert "operator" in threshold["visible_when"]

    def test_port_display_names(self):
        """포트에 display_name이 i18n 키로 자동 생성되는지 확인"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("OverseasStockBrokerNode")

        assert schema is not None
        assert len(schema.outputs) > 0

        connection_output = schema.outputs[0]
        assert connection_output["name"] == "connection"
        assert connection_output["display_name"] == "i18n:ports.connection"

    def test_start_node_empty_config_schema(self):
        """StartNode는 설정 필드가 없어 config_schema가 빈 dict"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("StartNode")

        assert schema is not None
        assert schema.config_schema == {}

    def test_real_market_data_node_sub_fields(self):
        """RealMarketDataNode의 sub_fields 확인"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("OverseasStockRealMarketDataNode")

        assert schema is not None
        assert "symbol" in schema.config_schema

        symbol = schema.config_schema["symbol"]
        assert "sub_fields" in symbol
        assert len(symbol["sub_fields"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
