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

    items { from, extract } 방식:
    - from: 반복할 배열 지정 (예: {{ nodes.historical.value.time_series }})
    - extract: 각 행에서 추출할 필드 정의 (row 키워드로 현재 행 접근)

    예시:
    {
      "plugin": "RSI",
      "items": {
        "from": "{{ nodes.historical.value.time_series }}",
        "extract": {
          "symbol": "{{ nodes.split.item.symbol }}",
          "exchange": "{{ nodes.split.item.exchange }}",
          "date": "{{ row.date }}",
          "close": "{{ row.close }}"
        }
      },
      "fields": {"period": 14, "threshold": 30, "direction": "below"}
    }
    """

    type: Literal["ConditionNode"] = "ConditionNode"
    category: NodeCategory = NodeCategory.CONDITION
    description: str = "i18n:nodes.ConditionNode.description"

    # === items { from, extract } 방식 ===
    items: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Data input configuration with from (source array) and extract (field mapping)",
    )

    # === 익절/손절 플러그인 전용 입력 ===
    positions: Any = Field(
        default=None,
        description="Positions data binding - 익절/손절 플러그인용 (pnl_rate 포함)",
    )

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger"),
        InputPort(
            name="items",
            type="ohlcv_data",
            description="i18n:ports.items",
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
            name="result",
            type="condition_result",
            description="i18n:ports.condition_result",
            fields=CONDITION_RESULT_FIELDS,
            example={
                "is_condition_met": True,
                "passed_symbols": [
                    {"exchange": "NASDAQ", "symbol": "AAPL"},
                ],
                "details": [
                    {"symbol": "AAPL", "exchange": "NASDAQ", "passed": True, "value": 28.5, "threshold": 30, "direction": "below"},
                ],
            },
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
                example="RSI",
                help_text="Plugin id from get_plugin_catalog (e.g. RSI, MACD, BollingerBands).",
            ),
            # === DATA: items { from, extract } 방식 ===
            "items": FieldSchema(
                name="items",
                type=FieldType.OBJECT,
                description="i18n:fields.ConditionNode.items",
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                help_text="i18n:fields.ConditionNode.items.help_text",
                object_schema=[
                    {
                        "name": "from",
                        "type": "STRING",
                        "expression_mode": "expression_only",
                        "required": True,
                        "description": "i18n:fields.ConditionNode.items.from",
                        "placeholder": "{{ nodes.historical.value.time_series }}",
                        "help_text": "반복할 배열을 지정합니다. 이 배열의 각 항목을 row로 접근할 수 있습니다.",
                    },
                    {
                        "name": "extract",
                        "type": "OBJECT",
                        "expression_mode": "fixed_only",
                        "required": True,
                        "description": "i18n:fields.ConditionNode.items.extract",
                        "help_text": "각 행에서 추출할 필드를 정의합니다. row.xxx로 현재 행의 필드에 접근합니다.",
                        "object_schema": [
                            {"name": "symbol", "type": "STRING", "expression_mode": "both", "required": True,
                             "description": "종목 코드", "placeholder": "{{ nodes.split.item.symbol }}"},
                            {"name": "exchange", "type": "STRING", "expression_mode": "both", "required": True,
                             "description": "거래소 코드", "placeholder": "{{ nodes.split.item.exchange }}"},
                            {"name": "date", "type": "STRING", "expression_mode": "both", "required": True,
                             "description": "날짜", "placeholder": "{{ row.date }}"},
                            {"name": "close", "type": "STRING", "expression_mode": "both", "required": True,
                             "description": "종가", "placeholder": "{{ row.close }}"},
                            {"name": "open", "type": "STRING", "expression_mode": "both", "required": False,
                             "description": "시가", "placeholder": "{{ row.open }}"},
                            {"name": "high", "type": "STRING", "expression_mode": "both", "required": False,
                             "description": "고가", "placeholder": "{{ row.high }}"},
                            {"name": "low", "type": "STRING", "expression_mode": "both", "required": False,
                             "description": "저가", "placeholder": "{{ row.low }}"},
                            {"name": "volume", "type": "STRING", "expression_mode": "both", "required": False,
                             "description": "거래량", "placeholder": "{{ row.volume }}"},
                        ],
                    },
                ],
                example={
                    "from": "{{ nodes.historical.value.time_series }}",
                    "extract": {
                        "symbol": "{{ nodes.split.item.symbol }}",
                        "exchange": "{{ nodes.split.item.exchange }}",
                        "date": "{{ row.date }}",
                        "close": "{{ row.close }}",
                    },
                },
            ),
            # === PLUGIN-SPECIFIC: 익절/손절 플러그인에서만 표시 ===
            "positions": FieldSchema(
                name="positions",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.positions",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.realAccount.positions }}",
                example=[{"symbol": "AAPL", "exchange": "NASDAQ", "quantity": 10, "avg_price": 150.0, "pnl_rate": 5.5}],
                example_binding="{{ nodes.realAccount.positions }}",
                bindable_sources=[
                    "RealAccountNode.positions",
                    "AccountNode.positions",
                ],
                expected_type="dict[str, any]",
                visible_when={"plugin": ["ProfitTarget", "StopLoss", "TrailingStop"]},
                help_text="보유 포지션 데이터 (수익률 포함)",
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
            example={
                "is_condition_met": True,
                "passed_symbols": [{"exchange": "NASDAQ", "symbol": "AAPL"}],
            },
        ),
        OutputPort(
            name="passed_symbols",
            type="symbol_list",
            description="i18n:ports.passed_symbols",
            fields=SYMBOL_LIST_FIELDS,
            example=[
                {"exchange": "NASDAQ", "symbol": "AAPL"},
            ],
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
                example="all",
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
                example=2,
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