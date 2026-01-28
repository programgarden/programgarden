"""
ProgramGarden Core - Condition Nodes

Condition evaluation nodes:
- ConditionNode: Condition plugin execution (RSI, MACD, etc.)
- LogicNode: Condition combination (and/or/xor/at_least/weighted)
"""

from typing import Optional, List, Literal, Dict, Any, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    PluginNode,
    NodeCategory,
    InputPort,
    OutputPort,
    CONDITION_RESULT_FIELDS,
    SYMBOL_LIST_FIELDS,
)


class ConditionNode(PluginNode):
    """
    Condition plugin execution node

    Executes community plugins such as RSI, MACD, BollingerBands
    
    기본 입력 (필수):
    - data: OHLCV 배열 데이터 (플랫 형식)
    
    고급 옵션 (선택, 기본값 사용 가능):
    - close_field 등: 필드명 매핑 (커스텀 데이터 소스 사용 시)
    - symbols: 종목 리스트 (data에서 자동 추출됨)
    - held_symbols, position_data: 익절/손절 조건에서 사용
    
    예시:
    {
      "data": "{{ flatten(nodes.historicaldata_1.values, 'time_series') }}",
      "plugin": "RSI",
      "fields": {"period": 14, "threshold": 30}
    }
    """

    type: Literal["ConditionNode"] = "ConditionNode"
    category: NodeCategory = NodeCategory.CONDITION
    description: str = "i18n:nodes.ConditionNode.description"

    # === 필수 입력 ===
    data: Any = Field(
        default=None,
        description="Input data array (e.g., {{ flatten(nodes.historicaldata_1.values, 'time_series') }})",
    )
    
    # === 고급: 필드 매핑 (기본값으로 충분, 커스텀 데이터 소스 사용 시만 변경) ===
    close_field: str = Field(
        default="close",
        description="Field name for close price",
    )
    open_field: str = Field(
        default="open",
        description="Field name for open price",
    )
    high_field: str = Field(
        default="high",
        description="Field name for high price",
    )
    low_field: str = Field(
        default="low",
        description="Field name for low price",
    )
    volume_field: str = Field(
        default="volume",
        description="Field name for volume",
    )
    date_field: str = Field(
        default="date",
        description="Field name for date/time",
    )
    symbol_field: str = Field(
        default="symbol",
        description="Field name for symbol identifier",
    )
    exchange_field: str = Field(
        default="exchange",
        description="Field name for exchange",
    )
    
    # === 익절/손절 플러그인 전용 입력 ===
    positions: Any = Field(
        default=None,
        description="Positions data binding - 익절/손절 플러그인용 (pnl_rate 포함)",
    )

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger"),
        InputPort(
            name="data",
            type="array",
            description="i18n:ports.data",
        ),
        InputPort(
            name="positions",
            type="position_data",
            description="i18n:ports.positions",
            required=False,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="symbols",
            type="symbol_list",
            description="i18n:ports.input_symbols",
            fields=SYMBOL_LIST_FIELDS,
        ),
        OutputPort(
            name="result",
            type="condition_result",
            description="i18n:ports.result",
            fields=CONDITION_RESULT_FIELDS,
        ),
        OutputPort(
            name="passed_symbols",
            type="symbol_list",
            description="i18n:ports.passed_symbols",
            fields=SYMBOL_LIST_FIELDS,
        ),
        OutputPort(
            name="failed_symbols",
            type="symbol_list",
            description="i18n:ports.failed_symbols",
            fields=SYMBOL_LIST_FIELDS,
        ),
        OutputPort(
            name="values",
            type="dict",
            description="i18n:ports.values",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            # === PARAMETERS: 플러그인 선택 ===
            "plugin": FieldSchema(
                name="plugin",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.plugin",
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CUSTOM_PLUGIN_SELECT,
            ),
            # === DATA: 입력 데이터 ===
            "data": FieldSchema(
                name="data",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.data",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ flatten(nodes.historicaldata_1.values, 'time_series') }}",
                example=[
                    {"symbol": "AAPL", "exchange": "NASDAQ", "date": "20260116", "close": 150.0, "open": 148.5, "high": 151.0, "low": 147.8, "volume": 1000000},
                ],
                example_binding="{{ flatten(nodes.historicaldata_1.values, 'time_series') }}",
                bindable_sources=[
                    "HistoricalDataNode.values (with flatten)",
                    "RealMarketDataNode.data",
                    "HTTPRequestNode.response",
                ],
                expected_type="list[dict]",
            ),
            # === FIELD MAPPING: 필드명 매핑 (data 바로 하단에 표시) ===
            "close_field": FieldSchema(
                name="close_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.close_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="close",
                placeholder="close",
                group="field_mapping",
            ),
            "open_field": FieldSchema(
                name="open_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.open_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="open",
                placeholder="open",
                group="field_mapping",
            ),
            "high_field": FieldSchema(
                name="high_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.high_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="high",
                placeholder="high",
                group="field_mapping",
            ),
            "low_field": FieldSchema(
                name="low_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.low_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="low",
                placeholder="low",
                group="field_mapping",
            ),
            "volume_field": FieldSchema(
                name="volume_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.volume_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="volume",
                placeholder="volume",
                group="field_mapping",
            ),
            "date_field": FieldSchema(
                name="date_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.date_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="date",
                placeholder="date",
                group="field_mapping",
            ),
            # === PLUGIN-SPECIFIC: 익절/손절 플러그인에서만 표시 ===
            # positions: v3.0.0+ 플러그인용 (ProfitTarget, StopLoss)
            "positions": FieldSchema(
                name="positions",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.positions",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.realAccount.positions }}",
                example={"AAPL": {"qty": 10, "avg_price": 150.0, "pnl_rate": 5.5}},
                example_binding="{{ nodes.realAccount.positions }}",
                bindable_sources=[
                    "RealAccountNode.positions",
                    "AccountNode.positions",
                ],
                expected_type="dict[str, any]",
                visible_when={"plugin": ["ProfitTarget", "StopLoss", "TrailingStop"]},
                help_text="보유 포지션 데이터 (수익률 포함)",
            ),
            "symbol_field": FieldSchema(
                name="symbol_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.symbol_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="symbol",
                placeholder="symbol",
                group="field_mapping",
            ),
            "exchange_field": FieldSchema(
                name="exchange_field",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.exchange_field",
                required=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                default="exchange",
                placeholder="exchange",
                group="field_mapping",
            ),
        }


class LogicNode(BaseNode):
    """
    Condition combination node

    Combines multiple condition results with logical operators
    """

    type: Literal["LogicNode"] = "LogicNode"
    category: NodeCategory = NodeCategory.CONDITION
    description: str = "i18n:nodes.LogicNode.description"

    # LogicNode specific config
    operator: Literal["all", "any", "not", "xor", "at_least", "at_most", "exactly", "weighted"] = Field(
        default="all",
        description="Logical operator (all=AND, any=OR, not, xor, at_least, at_most, exactly, weighted)",
    )
    threshold: Optional[float] = Field(
        default=None,
        description="Threshold value (for at_least, at_most, exactly, weighted operators)",
    )
    conditions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of conditions to combine (each condition has is_condition_met, passed_symbols, and optionally weight)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="input",
            type="condition_result",
            description="i18n:ports.result",
            multiple=True,
            min_connections=2,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="result",
            type="condition_result",
            description="i18n:ports.result",
            fields=CONDITION_RESULT_FIELDS,
        ),
        OutputPort(
            name="passed_symbols",
            type="symbol_list",
            description="i18n:ports.passed_symbols",
            fields=SYMBOL_LIST_FIELDS,
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            # === PARAMETERS: 모두 핵심 논리 연산 설정 ===
            "operator": FieldSchema(
                name="operator",
                type=FieldType.ENUM,
                description="i18n:fields.LogicNode.operator",
                default="all",
                enum_values=["all", "any", "not", "xor", "at_least", "at_most", "exactly", "weighted"],
                enum_labels={
                    "all": "i18n:enums.operator.all",
                    "any": "i18n:enums.operator.any",
                    "not": "i18n:enums.operator.not",
                    "xor": "i18n:enums.operator.xor",
                    "at_least": "i18n:enums.operator.at_least",
                    "at_most": "i18n:enums.operator.at_most",
                    "exactly": "i18n:enums.operator.exactly",
                    "weighted": "i18n:enums.operator.weighted",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                help_text="i18n:fields.LogicNode.operator.help_text",
            ),
            "threshold": FieldSchema(
                name="threshold",
                type=FieldType.NUMBER,  # weighted는 소수점 필요 (0.6 등)
                description="i18n:fields.LogicNode.threshold",
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                visible_when={"operator": ["at_least", "at_most", "exactly", "weighted"]},
                help_text="i18n:fields.LogicNode.threshold.help_text",
                placeholder="2 또는 0.6",
            ),
            "conditions": FieldSchema(
                name="conditions",
                type=FieldType.ARRAY,
                array_item_type=FieldType.OBJECT,
                description="i18n:fields.LogicNode.conditions",
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CUSTOM_OBJECT_ARRAY_TABLE,
                example=[
                    {
                        "is_condition_met": "{{ nodes.rsiCondition.result }}",
                        "passed_symbols": "{{ nodes.rsiCondition.passed_symbols }}"
                    }
                ],
                help_text="i18n:fields.LogicNode.conditions.help_text",
                object_schema=[
                    {
                        "name": "is_condition_met",
                        "type": "STRING",
                        "expression_mode": "expression_only",
                        "required": True,
                        "description": "i18n:fields.LogicNode.conditions.is_condition_met",
                        "placeholder": "{{ nodes.conditionNodeId.result }}",
                    },
                    {
                        "name": "passed_symbols",
                        "type": "STRING",
                        "expression_mode": "expression_only",
                        "required": True,
                        "description": "i18n:fields.LogicNode.conditions.passed_symbols",
                        "placeholder": "{{ nodes.conditionNodeId.passed_symbols }}",
                    },
                    {
                        "name": "weight",
                        "type": "NUMBER",
                        "expression_mode": "fixed_only",
                        "required": False,
                        "description": "i18n:fields.LogicNode.conditions.weight",
                        "placeholder": "0.5",
                        "visible_when": {"operator": ["weighted"]},
                        "default": 1.0,
                    },
                ],
            ),
        }