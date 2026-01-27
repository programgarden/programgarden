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

    expression_mode별 렌더링 규칙:
    - FIXED_ONLY: 토글 없이 직접 위젯 렌더링 (description -> args.helperText)
    - EXPRESSION_ONLY: custom_expression_toggle (lockedMode="expression")
    - BOTH: custom_expression_toggle (lockedMode 없음, 토글 전환 가능)
    """

    def test_text_input_fixed_only(self):
        """기본 텍스트 입력 필드 (FIXED_ONLY - 토글 없이 직접 렌더링)"""
        fs = FieldSchema(
            name="test_field",
            type=FieldType.STRING,
            description="테스트 필드",
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()

        # FIXED_ONLY: 직접 위젯 렌더링 (custom_expression_toggle 없음)
        assert widget["type"] == "text_form_field"
        assert widget["args"]["decoration"]["labelText"] == "Test Field"
        # description은 args.helperText로 전달
        assert widget["args"]["helperText"] == "테스트 필드"

    def test_number_input_fixed_only(self):
        """숫자 입력 필드 (기본값 포함, FIXED_ONLY)"""
        fs = FieldSchema(
            name="period",
            type=FieldType.INTEGER,
            description="기간",
            default=14,
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()

        assert widget["type"] == "text_form_field"
        assert widget["args"]["keyboardType"] == "number"
        assert widget["args"]["initialValue"] == "14"
        assert widget["args"]["helperText"] == "기간"

    def test_select_fixed_only(self):
        """드롭다운 선택 필드 (FIXED_ONLY)"""
        fs = FieldSchema(
            name="provider",
            type=FieldType.ENUM,
            description="증권사",
            default="ls-sec.co.kr",
            enum_values=["ls-sec.co.kr"],
            enum_labels={"ls-sec.co.kr": "LS증권"},
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()

        assert widget["type"] == "dropdown_button_form_field"
        assert widget["args"]["items"] == ["ls-sec.co.kr"]
        assert widget["args"]["value"] == "ls-sec.co.kr"
        assert widget["args"]["itemLabels"] == {"ls-sec.co.kr": "LS증권"}
        assert widget["args"]["helperText"] == "증권사"

    def test_checkbox_fixed_only(self):
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

        assert widget["type"] == "checkbox"
        assert widget["args"]["value"] is True
        assert widget["args"]["helperText"] == "수정주가 적용"

    def test_expression_only_mode(self):
        """EXPRESSION_ONLY 모드 (바인딩 전용 - lockedMode="expression")"""
        fs = FieldSchema(
            name="data",
            type=FieldType.OBJECT,
            description="입력 데이터",
            expression_mode=ExpressionMode.EXPRESSION_ONLY,
            example_binding="{{ nodes.source.values }}",
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
        assert expr_widget["args"]["decoration"]["hintText"] == "{{ nodes.source.values }}"

    def test_binding_input_component(self):
        """BINDING_INPUT 컴포넌트 (EXPRESSION_ONLY)"""
        fs = FieldSchema(
            name="data",
            type=FieldType.STRING,
            description="입력 데이터",
            expression_mode=ExpressionMode.EXPRESSION_ONLY,
            example_binding="{{ flatten(nodes.historical.values, 'time_series') }}",
        )
        widget = fs.to_json_dynamic_widget()

        assert widget["type"] == "custom_expression_toggle"
        assert widget["args"]["lockedMode"] == "expression"
        expr_widget = widget["args"]["expressionWidget"]
        assert expr_widget["type"] == "text_form_field"
        assert expr_widget["args"]["decoration"]["hintText"] == "{{ flatten(nodes.historical.values, 'time_series') }}"

    def test_credential_select_fixed_only(self):
        """Credential 선택 필드 (FIXED_ONLY - 토글 없이 직접 렌더링)"""
        fs = FieldSchema(
            name="credential_id",
            type=FieldType.CREDENTIAL,
            description="Credential 선택",
            ui_component=UIComponent.CUSTOM_CREDENTIAL_SELECT,
            credential_types=["broker_ls_stock", "broker_ls_futures"],
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()

        assert widget["type"] == "custom_credential_select"
        # credentialTypes는 type_id와 name을 포함한 객체 배열
        assert len(widget["args"]["credentialTypes"]) == 2
        assert widget["args"]["credentialTypes"][0]["type_id"] == "broker_ls_stock"
        assert widget["args"]["credentialTypes"][1]["type_id"] == "broker_ls_futures"
        assert widget["args"]["items"] == []  # 런타임에 채워짐
        assert widget["args"]["helperText"] == "Credential 선택"

    def test_plugin_select_fixed_only(self):
        """플러그인 선택 (커스텀 위젯, FIXED_ONLY)"""
        fs = FieldSchema(
            name="plugin",
            type=FieldType.STRING,
            description="플러그인 선택",
            ui_component=UIComponent.CUSTOM_PLUGIN_SELECT,
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()

        assert widget["type"] == "custom_plugin_select"
        assert widget["args"]["helperText"] == "플러그인 선택"

    def test_symbol_editor_fixed_only(self):
        """종목 편집기 (커스텀 위젯) - FIXED_ONLY: 토글 없이 직접 렌더링"""
        fs = FieldSchema(
            name="symbols",
            type=FieldType.ARRAY,
            description="종목 리스트",
            expression_mode=ExpressionMode.FIXED_ONLY,
            ui_component=UIComponent.CUSTOM_SYMBOL_EDITOR,
        )
        widget = fs.to_json_dynamic_widget()

        assert widget["type"] == "custom_symbol_editor"
        assert widget["args"]["helperText"] == "종목 리스트"

    def test_symbol_editor_both_mode(self):
        """종목 편집기 (BOTH 모드) - 자체 토글 위젯이라 직접 렌더링"""
        fs = FieldSchema(
            name="symbols",
            type=FieldType.ARRAY,
            description="종목 리스트",
            expression_mode=ExpressionMode.BOTH,
            ui_component=UIComponent.CUSTOM_SYMBOL_EDITOR,
        )
        widget = fs.to_json_dynamic_widget()

        # SYMBOL_EDITOR는 자체 토글 포함 -> 직접 렌더링
        assert widget["type"] == "custom_symbol_editor"
        assert widget["args"]["expressionMode"] == "both"

    def test_code_editor_fixed_only(self):
        """코드 에디터 (언어 옵션, FIXED_ONLY)"""
        fs = FieldSchema(
            name="query",
            type=FieldType.STRING,
            description="SQL 쿼리",
            ui_component=UIComponent.CUSTOM_CODE_EDITOR,
            ui_options={"language": "sql"},
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()

        assert widget["type"] == "custom_code_editor"
        assert widget["args"]["language"] == "sql"
        assert widget["args"]["helperText"] == "SQL 쿼리"

    def test_display_name_override_fixed_only(self):
        """display_name으로 라벨 오버라이드 (FIXED_ONLY)"""
        fs = FieldSchema(
            name="api_key",
            type=FieldType.STRING,
            display_name="API 키",
            description="인증용 API 키",
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()

        assert widget["type"] == "text_form_field"
        assert widget["args"]["decoration"]["labelText"] == "API 키"
        assert widget["args"]["helperText"] == "인증용 API 키"

    def test_both_mode_text_input(self):
        """BOTH 모드 텍스트 입력 - custom_expression_toggle 반환"""
        fs = FieldSchema(
            name="query",
            type=FieldType.STRING,
            description="검색어",
            expression_mode=ExpressionMode.BOTH,
            example_binding="{{ nodes.input.query }}",
        )
        widget = fs.to_json_dynamic_widget()

        assert widget["type"] == "custom_expression_toggle"
        assert "lockedMode" not in widget["args"]  # BOTH는 토글 가능
        assert widget["args"]["fixedWidget"]["type"] == "text_form_field"
        assert widget["args"]["expressionWidget"]["type"] == "text_form_field"

    def test_fixed_only_no_description(self):
        """FIXED_ONLY + description 없음 -> helperText 없음"""
        fs = FieldSchema(
            name="mode",
            type=FieldType.ENUM,
            enum_values=["A", "B"],
            expression_mode=ExpressionMode.FIXED_ONLY,
        )
        widget = fs.to_json_dynamic_widget()

        assert widget["type"] == "dropdown_button_form_field"
        assert "helperText" not in widget["args"]


class TestNodeTypeRegistryWidgetSchema:
    """NodeTypeRegistry widget_schema 생성 테스트"""

    def test_broker_node_widget_schema(self):
        """BrokerNode의 widget_schema 생성 확인"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("OverseasStockBrokerNode")

        assert schema is not None
        assert schema.widget_schema is not None
        assert schema.widget_schema["type"] == "column"
        assert "children" in schema.widget_schema["args"]

        # provider 필드 확인 (FIXED_ONLY → 직접 렌더링)
        children = schema.widget_schema["args"]["children"]
        provider_widget = next(
            (w for w in children if w.get("field_key_of_pydantic") == "provider"),
            None
        )
        assert provider_widget is not None
        assert provider_widget["type"] == "dropdown_button_form_field"

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
        # BOTH 모드 + SYMBOL_EDITOR -> 자체 토글, 직접 렌더링
        assert symbols_widget["type"] == "custom_symbol_editor"

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
        # FIXED_ONLY → 직접 렌더링
        assert plugin_widget["type"] == "custom_plugin_select"

    def test_historical_data_node_widget_schema(self):
        """OverseasStockHistoricalDataNode의 widget_schema 생성 확인"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("OverseasStockHistoricalDataNode")

        assert schema is not None
        assert schema.widget_schema is not None

        children = schema.widget_schema["args"]["children"]

        # start_date 필드 확인 (BOTH 모드 → custom_expression_toggle, lockedMode 없음)
        start_date_widget = next(
            (w for w in children if w.get("field_key_of_pydantic") == "start_date"),
            None
        )
        assert start_date_widget is not None
        assert start_date_widget["type"] == "custom_expression_toggle"
        assert "lockedMode" not in start_date_widget["args"]  # BOTH 모드

        # interval 필드 확인 (FIXED_ONLY → 직접 렌더링)
        interval_widget = next(
            (w for w in children if w.get("field_key_of_pydantic") == "interval"),
            None
        )
        assert interval_widget is not None
        assert interval_widget["type"] == "dropdown_button_form_field"

    def test_stock_modify_order_node_widget_schema_with_visible_when(self):
        """OverseasStockModifyOrderNode의 visible_when 조건부 필드 확인 (json_dynamic_widget conditional 형식)"""
        registry = NodeTypeRegistry()
        schema = registry.get_schema("OverseasStockModifyOrderNode")

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
