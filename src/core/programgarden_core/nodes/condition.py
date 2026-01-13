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
)


class ConditionNode(PluginNode):
    """
    Condition plugin execution node

    Executes community plugins such as RSI, MACD, BollingerBands
    """

    type: Literal["ConditionNode"] = "ConditionNode"
    category: NodeCategory = NodeCategory.CONDITION
    description: str = "i18n:nodes.ConditionNode.description"

    # === 포트 바인딩 필드 ({{ nodes.xxx.yyy }} 표현식 또는 평가된 값) ===
    price_data: Any = Field(
        default=None,
        description="Price data binding (e.g., {{ nodes.marketData.ohlcv }}) or evaluated dict",
    )
    volume_data: Any = Field(
        default=None,
        description="Volume data binding (e.g., {{ nodes.marketData.volume }}) or evaluated dict",
    )
    symbols: Any = Field(
        default=None,
        description="Symbol list binding (e.g., {{ nodes.watchlist.symbols }}) or evaluated list",
    )
    held_symbols: Any = Field(
        default=None,
        description="Held symbols binding (e.g., {{ nodes.account.held_symbols }}) or evaluated list",
    )
    position_data: Any = Field(
        default=None,
        description="Position data binding (e.g., {{ nodes.account.positions }}) or evaluated dict",
    )

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger"),
        InputPort(
            name="price_data",
            type="market_data",
            description="i18n:ports.price_data",
        ),
        InputPort(
            name="volume_data",
            type="market_data",
            description="i18n:ports.volume_data",
            required=False,
        ),
        InputPort(
            name="symbols",
            type="symbol_list",
            description="i18n:ports.symbols",
            required=False,
        ),
        InputPort(
            name="held_symbols",
            type="symbol_list",
            description="i18n:ports.held_symbols",
            required=False,
        ),
        InputPort(
            name="position_data",
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
        ),
        OutputPort(
            name="result",
            type="condition_result",
            description="i18n:ports.result",
        ),
        OutputPort(
            name="passed_symbols",
            type="symbol_list",
            description="i18n:ports.passed_symbols",
        ),
        OutputPort(
            name="failed_symbols",
            type="symbol_list",
            description="i18n:ports.failed_symbols",
        ),
        OutputPort(
            name="values",
            type="dict",
            description="i18n:ports.values",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 플러그인 선택 ===
            "plugin": FieldSchema(
                name="plugin",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.plugin",
                required=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
                ui_component="plugin_selector",
            ),
            # === PARAMETERS: 포트 바인딩 필드 ===
            "price_data": FieldSchema(
                name="price_data",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.price_data",
                required=True,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.realMarket.price }}",
                # 바인딩 가이드
                example={"AAPL": 150.0, "TSLA": 250.0},
                example_binding="{{ nodes.realMarket.price }}",
                bindable_sources=[
                    "RealMarketDataNode.price",
                    "MarketDataNode.price",
                    "HistoricalDataNode.ohlcv",
                ],
                expected_type="dict[str, float]",
            ),
            "volume_data": FieldSchema(
                name="volume_data",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.volume_data",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.realMarket.volume }}",
                # 바인딩 가이드
                example={"AAPL": 1000000, "TSLA": 2000000},
                example_binding="{{ nodes.realMarket.volume }}",
                bindable_sources=[
                    "RealMarketDataNode.volume",
                    "MarketDataNode.volume",
                ],
                expected_type="dict[str, float]",
            ),
            "symbols": FieldSchema(
                name="symbols",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.symbols",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.watchlist.symbols }}",
                # 바인딩 가이드
                example=["AAPL", "TSLA", "NVDA"],
                example_binding="{{ nodes.watchlist.symbols }}",
                bindable_sources=[
                    "WatchlistNode.symbols",
                    "ScreenerNode.filtered_symbols",
                ],
                expected_type="list[str]",
            ),
            "held_symbols": FieldSchema(
                name="held_symbols",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.held_symbols",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.held_symbols }}",
                # 바인딩 가이드
                example=["AAPL", "TSLA"],
                example_binding="{{ nodes.account.held_symbols }}",
                bindable_sources=[
                    "RealAccountNode.held_symbols",
                    "AccountNode.held_symbols",
                ],
                expected_type="list[str]",
            ),
            "position_data": FieldSchema(
                name="position_data",
                type=FieldType.STRING,
                description="i18n:fields.ConditionNode.position_data",
                required=False,
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.positions }}",
                # 바인딩 가이드
                example={"AAPL": {"qty": 10, "avg_price": 150.0}},
                example_binding="{{ nodes.account.positions }}",
                bindable_sources=[
                    "RealAccountNode.positions",
                    "AccountNode.positions",
                ],
                expected_type="dict[str, any]",
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
    threshold: Optional[int] = Field(
        default=None,
        description="Threshold value (for at_least, at_most, exactly operators)",
    )
    weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Weights (for weighted operator, weight per input ID)",
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
        ),
        OutputPort(
            name="passed_symbols",
            type="symbol_list",
            description="i18n:ports.passed_symbols",
        ),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory
        return {
            # === PARAMETERS: 모두 핵심 논리 연산 설정 ===
            "operator": FieldSchema(
                name="operator",
                type=FieldType.ENUM,
                description="i18n:fields.LogicNode.operator",
                default="all",
                enum_values=["all", "any", "not", "xor", "at_least", "at_most", "exactly", "weighted"],
                required=True,
                bindable=False,
                category=FieldCategory.PARAMETERS,
            ),
            "threshold": FieldSchema(
                name="threshold",
                type=FieldType.INTEGER,
                description="i18n:fields.LogicNode.threshold",
                bindable=True,
                expression_enabled=True,
                category=FieldCategory.PARAMETERS,
            ),
            "weights": FieldSchema(
                name="weights",
                type=FieldType.OBJECT,
                description="i18n:fields.LogicNode.weights",
                bindable=False,
                category=FieldCategory.PARAMETERS,
            ),
        }
