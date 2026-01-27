"""
FieldSchema.to_json_dynamic_widget() 및 NodeTypeRegistry widget_schema 테스트
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


class TestFieldSchemaToJsonDynamicWidget:
    """FieldSchema.to_json_dynamic_widget() 메서드 테스트
    
    모든 모드가 custom_expression_toggle로 통일됨:
    - FIXED_ONLY: lockedMode="fixed", 토글 비활성화
    - EXPRESSION_ONLY: lockedMode="expression", 토글 비활성화
    - BOTH: lockedMode 없음, 토글 전환 가능
    """

    def test_text_input_basic(self):
        """기본 텍스트 입력 필드 변환 (FIXED_ONLY - lockedMode)"""
        fs = FieldSchema(
            name="test_field",
            type=FieldType.STRING,
            description="테스트 필드",
            ui_component=UIComponent.TEXT_INPUT,
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()
        
        # 모든 모드가 custom_expression_toggle 반환
        assert widget["type"] == "custom_expression_toggle"
        assert widget["args"]["lockedMode"] == "fixed"  # fixed 고정
        # fixedWidget 내부 확인
        fixed_widget = widget["args"]["fixedWidget"]
        assert fixed_widget["type"] == "text_form_field"
        assert fixed_widget["args"]["decoration"]["labelText"] == "Test Field"
        # helperText는 args에서 분리 관리 (decoration에 없음)
        assert "helperText" not in fixed_widget["args"]["decoration"]
        assert widget["args"]["fixedHelperText"] == "테스트 필드"

    def test_number_input_with_default(self):
        """숫자 입력 필드 (기본값 포함, FIXED_ONLY)"""
        fs = FieldSchema(
            name="period",
            type=FieldType.INTEGER,
            description="기간",
            default=14,
            ui_component=UIComponent.NUMBER_INPUT,
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()
        
        assert widget["type"] == "custom_expression_toggle"
        assert widget["args"]["lockedMode"] == "fixed"
        fixed_widget = widget["args"]["fixedWidget"]
        assert fixed_widget["type"] == "text_form_field"
        assert fixed_widget["args"]["keyboardType"] == "number"
        assert fixed_widget["args"]["initialValue"] == "14"

    def test_select_with_enum_values(self):
        """드롭다운 선택 필드 (FIXED_ONLY)"""
        fs = FieldSchema(
            name="provider",
            type=FieldType.ENUM,
            description="증권사",
            default="ls-sec.co.kr",
            enum_values=["ls-sec.co.kr"],
            enum_labels={"ls-sec.co.kr": "LS증권"},
            ui_component=UIComponent.SELECT,
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()
        
        assert widget["type"] == "custom_expression_toggle"
        assert widget["args"]["lockedMode"] == "fixed"
        fixed_widget = widget["args"]["fixedWidget"]
        assert fixed_widget["type"] == "dropdown_button_form_field"
        assert fixed_widget["args"]["items"] == ["ls-sec.co.kr"]
        assert fixed_widget["args"]["value"] == "ls-sec.co.kr"
        assert fixed_widget["args"]["itemLabels"] == {"ls-sec.co.kr": "LS증권"}

    def test_checkbox_field(self):
        """체크박스 필드 (FIXED_ONLY)"""
        fs = FieldSchema(
            name="adjust",
            type=FieldType.BOOLEAN,
            description="수정주가 적용",
            default=True,
            ui_component=UIComponent.CHECKBOX,
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()
        
        assert widget["type"] == "custom_expression_toggle"
        assert widget["args"]["lockedMode"] == "fixed"
        fixed_widget = widget["args"]["fixedWidget"]
        assert fixed_widget["type"] == "checkbox"
        assert fixed_widget["args"]["value"] is True

    def test_expression_only_mode(self):
        """EXPRESSION_ONLY 모드 (바인딩 전용 - lockedMode="expression")"""
        fs = FieldSchema(
            name="connection",
            type=FieldType.OBJECT,
            description="브로커 연결",
            expression_mode=ExpressionMode.EXPRESSION_ONLY,
            example_binding="{{ nodes.broker.connection }}",
        )
        widget = fs.to_json_dynamic_widget()
        
        assert widget["type"] == "custom_expression_toggle"
        assert widget["args"]["lockedMode"] == "expression"  # expression 고정
        assert widget["args"]["defaultMode"] == "expression"
        # expressionWidget 내부 확인
        expr_widget = widget["args"]["expressionWidget"]
        assert expr_widget["type"] == "text_form_field"
        # prefixText/suffixText 없음 - 사용자가 {{ }}를 자유롭게 입력
        assert "prefixText" not in expr_widget["args"]["decoration"]
        assert "suffixText" not in expr_widget["args"]["decoration"]
        assert expr_widget["args"]["decoration"]["hintText"] == "{{ nodes.broker.connection }}"

    def test_binding_input_component(self):
        """BINDING_INPUT 컴포넌트 (EXPRESSION_ONLY)"""
        fs = FieldSchema(
            name="data",
            type=FieldType.STRING,
            description="입력 데이터",
            ui_component=UIComponent.BINDING_INPUT,
            expression_mode=ExpressionMode.EXPRESSION_ONLY,
            example_binding="{{ flatten(nodes.historical.values, 'time_series') }}",
        )
        widget = fs.to_json_dynamic_widget()
        
        assert widget["type"] == "custom_expression_toggle"
        assert widget["args"]["lockedMode"] == "expression"
        expr_widget = widget["args"]["expressionWidget"]
        assert expr_widget["type"] == "text_form_field"
        assert expr_widget["args"]["decoration"]["hintText"] == "{{ flatten(nodes.historical.values, 'time_series') }}"

    def test_credential_select(self):
        """Credential 선택 필드 (FIXED_ONLY)"""
        fs = FieldSchema(
            name="credential_id",
            type=FieldType.CREDENTIAL,
            description="Credential 선택",
            ui_component=UIComponent.CREDENTIAL_SELECT,
            credential_types=["broker_ls_stock", "broker_ls_futures"],
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()
        
        assert widget["type"] == "custom_expression_toggle"
        assert widget["args"]["lockedMode"] == "fixed"
        fixed_widget = widget["args"]["fixedWidget"]
        assert fixed_widget["type"] == "custom_credential_select"
        # credentialTypes는 type_id와 name을 포함한 객체 배열
        assert len(fixed_widget["args"]["credentialTypes"]) == 2
        assert fixed_widget["args"]["credentialTypes"][0]["type_id"] == "broker_ls_stock"
        assert fixed_widget["args"]["credentialTypes"][1]["type_id"] == "broker_ls_futures"
        assert fixed_widget["args"]["items"] == []  # 런타임에 채워짐

    def test_plugin_select_custom_widget(self):
        """플러그인 선택 (커스텀 위젯, FIXED_ONLY)"""
        fs = FieldSchema(
            name="plugin",
            type=FieldType.STRING,
            description="플러그인 선택",
            ui_component=UIComponent.PLUGIN_SELECT,
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()
        
        assert widget["type"] == "custom_expression_toggle"
        assert widget["args"]["lockedMode"] == "fixed"
        fixed_widget = widget["args"]["fixedWidget"]
        assert fixed_widget["type"] == "custom_plugin_select"

    def test_symbol_editor_custom_widget(self):
        """종목 편집기 (커스텀 위젯) - FIXED_ONLY 모드"""
        fs = FieldSchema(
            name="symbols",
            type=FieldType.ARRAY,
            description="종목 리스트",
            expression_mode=ExpressionMode.FIXED_ONLY,
            ui_component=UIComponent.SYMBOL_EDITOR,
        )
        widget = fs.to_json_dynamic_widget()
        
        assert widget["type"] == "custom_expression_toggle"
        assert widget["args"]["lockedMode"] == "fixed"
        fixed_widget = widget["args"]["fixedWidget"]
        assert fixed_widget["type"] == "custom_symbol_editor"

    def test_symbol_editor_both_mode(self):
        """종목 편집기 (BOTH 모드) - 토글 전환 가능"""
        fs = FieldSchema(
            name="symbols",
            type=FieldType.ARRAY,
            description="종목 리스트",
            expression_mode=ExpressionMode.BOTH,
            ui_component=UIComponent.SYMBOL_EDITOR,
        )
        widget = fs.to_json_dynamic_widget()
        
        # BOTH 모드에서는 custom_expression_toggle 반환, lockedMode 없음
        assert widget["type"] == "custom_expression_toggle"
        assert widget["args"]["fieldKey"] == "symbols"
        assert "lockedMode" not in widget["args"]  # BOTH는 토글 가능
        # fixedWidget과 expressionWidget 둘 다 있음
        assert widget["args"]["fixedWidget"]["type"] == "custom_symbol_editor"
        assert widget["args"]["expressionWidget"]["type"] == "text_form_field"

    def test_code_editor_with_language(self):
        """코드 에디터 (언어 옵션, FIXED_ONLY)"""
        fs = FieldSchema(
            name="query",
            type=FieldType.STRING,
            description="SQL 쿼리",
            ui_component=UIComponent.CODE_EDITOR,
            ui_options={"language": "sql"},
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()
        
        assert widget["type"] == "custom_expression_toggle"
        assert widget["args"]["lockedMode"] == "fixed"
        fixed_widget = widget["args"]["fixedWidget"]
        assert fixed_widget["type"] == "custom_code_editor"
        assert fixed_widget["args"]["language"] == "sql"

    def test_display_name_override(self):
        """display_name으로 라벨 오버라이드 (FIXED_ONLY)"""
        fs = FieldSchema(
            name="api_key",
            type=FieldType.STRING,
            display_name="API 키",
            description="인증용 API 키",
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()
        
        assert widget["type"] == "custom_expression_toggle"
        fixed_widget = widget["args"]["fixedWidget"]
        assert fixed_widget["args"]["decoration"]["labelText"] == "API 키"


class TestNodeTypeRegistryWidgetSchema:
    """NodeTypeRegistry widget_schema 생성 테스트"""

    def test_broker_node_widget_schema(self):
        """BrokerNode의 widget_schema 생성 확인"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("BrokerNode")
        
        assert schema is not None
        assert schema.widget_schema is not None
        assert schema.widget_schema["type"] == "column"
        assert "children" in schema.widget_schema["args"]
        
        # provider 필드 확인 (FIXED_ONLY → custom_expression_toggle with lockedMode)
        children = schema.widget_schema["args"]["children"]
        provider_widget = next(
            (w for w in children if w.get("field_key_of_pydantic") == "provider"),
            None
        )
        assert provider_widget is not None
        # 모든 필드가 custom_expression_toggle
        assert provider_widget["type"] == "custom_expression_toggle"
        assert provider_widget["args"]["lockedMode"] == "fixed"
        # fixedWidget 내부 확인
        assert provider_widget["args"]["fixedWidget"]["type"] == "dropdown_button_form_field"

    def test_watchlist_node_widget_schema(self):
        """WatchlistNode의 widget_schema 생성 확인"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("WatchlistNode")
        
        assert schema is not None
        assert schema.widget_schema is not None
        
        children = schema.widget_schema["args"]["children"]
        symbols_widget = next(
            (w for w in children if w.get("field_key_of_pydantic") == "symbols"),
            None
        )
        assert symbols_widget is not None
        # BOTH 모드라서 custom_expression_toggle 반환
        assert symbols_widget["type"] == "custom_expression_toggle"
        # fixedWidget 내부에 custom_symbol_editor 포함
        assert symbols_widget["args"]["fixedWidget"]["type"] == "custom_symbol_editor"

    def test_condition_node_widget_schema(self):
        """ConditionNode의 widget_schema 생성 확인"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("ConditionNode")
        
        assert schema is not None
        assert schema.widget_schema is not None
        
        children = schema.widget_schema["args"]["children"]
        plugin_widget = next(
            (w for w in children if w.get("field_key_of_pydantic") == "plugin"),
            None
        )
        assert plugin_widget is not None
        # FIXED_ONLY → custom_expression_toggle with lockedMode
        assert plugin_widget["type"] == "custom_expression_toggle"
        assert plugin_widget["args"]["lockedMode"] == "fixed"
        assert plugin_widget["args"]["fixedWidget"]["type"] == "custom_plugin_select"

    def test_historical_data_node_widget_schema(self):
        """HistoricalDataNode의 widget_schema 생성 확인"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("HistoricalDataNode")
        
        assert schema is not None
        assert schema.widget_schema is not None
        
        children = schema.widget_schema["args"]["children"]
        
        # start_date 필드 확인 (BOTH 모드 → lockedMode 없음)
        start_date_widget = next(
            (w for w in children if w.get("field_key_of_pydantic") == "start_date"),
            None
        )
        assert start_date_widget is not None
        assert start_date_widget["type"] == "custom_expression_toggle"
        assert "lockedMode" not in start_date_widget["args"]  # BOTH 모드
        
        # interval 필드 확인 (FIXED_ONLY → lockedMode="fixed")
        interval_widget = next(
            (w for w in children if w.get("field_key_of_pydantic") == "interval"),
            None
        )
        assert interval_widget is not None
        assert interval_widget["type"] == "custom_expression_toggle"
        assert interval_widget["args"]["lockedMode"] == "fixed"
        assert interval_widget["args"]["fixedWidget"]["type"] == "dropdown_button_form_field"

    def test_stock_modify_order_node_widget_schema_with_visible_when(self):
        """StockModifyOrderNode의 visible_when 조건부 필드 확인 (json_dynamic_widget conditional 형식)"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("StockModifyOrderNode")

        assert schema is not None
        assert schema.widget_schema is not None

        children = schema.widget_schema["args"]["children"]

        # new_price는 visible_when: {"price_type": "limit"}
        new_price_widget = next(
            (w for w in children if w.get("args", {}).get("onTrue", {}).get("field_key_of_pydantic") == "new_price"
             or w.get("field_key_of_pydantic") == "new_price"),
            None
        )
        # conditional로 감싸져 있어야 함
        assert new_price_widget is not None
        if new_price_widget["type"] == "conditional":
            # json_dynamic_widget 표준 형식: listen + conditional.values
            assert "listen" in new_price_widget
            assert "price_type" in new_price_widget["listen"]
            assert "conditional" in new_price_widget["args"]
            assert new_price_widget["args"]["conditional"]["values"]["price_type"] == "limit"
            assert "onTrue" in new_price_widget["args"]

    def test_start_node_empty_widget_schema(self):
        """StartNode는 설정 필드가 없어 widget_schema가 비어있음"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("StartNode")
        
        assert schema is not None
        # get_field_schema가 빈 dict를 반환하면 widget_schema는 None
        # 또는 children이 빈 배열
        if schema.widget_schema:
            children = schema.widget_schema.get("args", {}).get("children", [])
            assert len(children) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
