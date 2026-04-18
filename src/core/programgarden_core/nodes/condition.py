"""
ProgramGarden Core - Condition Nodes

Condition evaluation nodes:
- ConditionNode: Condition plugin execution (RSI, MACD, etc.)
- LogicNode: Condition combination (and/or/xor/at_least/weighted)
"""

from typing import Optional, List, Literal, Dict, Any, TYPE_CHECKING, ClassVar
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

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Run a condition plugin (RSI, MACD, Bollinger, Ichimoku, KDJ, Aroon, Heikin-Ashi, VortexIndicator, HurstExponent, SupportResistanceLevels, LevelTouch, TurtleBreakout, MagicFormula, …) against per-symbol OHLCV data",
            "Filter a watchlist down to symbols that meet a technical / fundamental condition",
            "Gate downstream OrderNodes behind a plugin-backed signal",
        ],
        "when_not_to_use": [
            "Simple scalar comparison — use IfNode (plugin-free, lower overhead)",
            "Compose multiple already-computed condition results — use LogicNode (AND / OR / weighted) instead",
            "Plugins that manage state (HWM, drawdown) belong in risk-category flows — check the plugin's `risk_features` declaration first",
        ],
        "typical_scenarios": [
            "HistoricalDataNode → ConditionNode(plugin='RSI', threshold=30, direction='below') → NewOrderNode",
            "HistoricalDataNode → ConditionNode(plugin='Bollinger') → LogicNode(and, ...) → order",
            "AccountNode.positions → ConditionNode(plugin='StopLoss', positions=...) → CancelOrderNode",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Plugin registry exposes 77+ community strategies (technical + position management)",
        "`items.from` + `items.extract` normalizes OHLCV into the per-row shape every plugin expects",
        "`positions` input path powers position-management plugins (StopLoss, ProfitTarget, TrailingStop, SharpeRatio)",
        "`is_tool_enabled=True` — AIAgentNode can invoke ConditionNode directly as a tool",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Passing raw OHLCV dicts as `data` when the plugin expects `items`",
            "reason": "Modern plugins iterate over `items.from` after extracting per-row fields; the legacy `data` binding does not trigger extraction.",
            "alternative": "Always use `items: { from: '{{ item.time_series }}', extract: { symbol, exchange, date, close, … } }`.",
        },
        {
            "pattern": "Using ConditionNode to combine two already-evaluated signals",
            "reason": "ConditionNode evaluates one plugin against its input. Combining signals needs Boolean logic.",
            "alternative": "Wire the two ConditionNodes into a LogicNode (mode='and' / 'or' / 'weighted').",
        },
        {
            "pattern": "Binding `positions` with the old dict-keyed format",
            "reason": "Position data was unified to `list[dict]` in v1.20.1; old dict-keyed payloads are rejected by binding_validator.",
            "alternative": "Provide positions as `[{symbol, exchange, quantity, avg_price, pnl_rate, …}, …]`.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "RSI oversold filter on a watchlist",
            "description": "Historical daily bars feed a RSI(14) plugin with threshold 30 below; downstream table renders the passing symbols.",
            "workflow_snippet": {
                "id": "condition-rsi-filter",
                "name": "RSI oversold filter",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {
                        "id": "watchlist",
                        "type": "WatchlistNode",
                        "symbols": [
                            {"symbol": "AAPL", "exchange": "NASDAQ"},
                            {"symbol": "MSFT", "exchange": "NASDAQ"},
                            {"symbol": "NVDA", "exchange": "NASDAQ"},
                        ],
                    },
                    {
                        "id": "historical",
                        "type": "OverseasStockHistoricalDataNode",
                        "symbol": "{{ item }}",
                        "period": "1d",
                        "start_date": "20260301",
                        "end_date": "20260401",
                    },
                    {
                        "id": "rsi",
                        "type": "ConditionNode",
                        "plugin": "RSI",
                        "items": {
                            "from": "{{ item.time_series }}",
                            "extract": {
                                "symbol": "{{ item.symbol }}",
                                "exchange": "{{ item.exchange }}",
                                "date": "{{ row.date }}",
                                "close": "{{ row.close }}",
                            },
                        },
                        "fields": {"period": 14, "threshold": 30, "direction": "below"},
                    },
                    {"id": "table", "type": "TableDisplayNode", "title": "RSI oversold", "data": "{{ nodes.rsi.passed_symbols }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "historical"},
                    {"from": "historical", "to": "rsi"},
                    {"from": "rsi", "to": "table"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "rsi.passed_symbols lists any of AAPL / MSFT / NVDA whose latest RSI(14) < 30; the table renders them.",
        },
        {
            "title": "StopLoss position management",
            "description": "Account positions feed a StopLoss plugin; when the loss threshold is breached the cancel/close path fires.",
            "workflow_snippet": {
                "id": "condition-stop-loss",
                "name": "StopLoss plugin",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {
                        "id": "stop_loss",
                        "type": "ConditionNode",
                        "plugin": "StopLoss",
                        "positions": "{{ nodes.account.positions }}",
                        "fields": {"threshold_pct": -3.0},
                    },
                    {"id": "if_triggered", "type": "IfNode", "left": "{{ nodes.stop_loss.is_condition_met }}", "operator": "==", "right": True},
                    {"id": "summary", "type": "SummaryDisplayNode", "title": "Stop-loss triggered", "data": {"symbols": "{{ nodes.stop_loss.passed_symbols }}"}},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "stop_loss"},
                    {"from": "stop_loss", "to": "if_triggered"},
                    {"from": "if_triggered", "to": "summary", "from_port": "true"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "StopLoss plugin evaluates each position's pnl_rate; when any position drops below -3% the IfNode routes to a summary display of the affected symbols.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Two input paths: (1) OHLCV flows through `items.from` + `items.extract`. (2) Position plugins read `positions` directly (list[dict]). Plugin parameters go under `fields`.",
        "output_consumption": "`result` output has `is_condition_met` boolean, `passed_symbols` array, `details` per-symbol breakdown. Bind `{{ nodes.cond.passed_symbols }}` for downstream iteration.",
        "common_combinations": [
            "OverseasStockHistoricalDataNode → ConditionNode(plugin='RSI') → NewOrderNode",
            "ConditionNode → LogicNode(and) → OrderNode",
            "AccountNode → ConditionNode(plugin='StopLoss', positions=…) → CancelOrderNode",
        ],
        "pitfalls": [
            "Always use the `items.from` / `items.extract` form for OHLCV plugins; the legacy `data` field is unsupported",
            "Node id must not contain hyphens — the expression evaluator parses `-` as subtraction",
            "Position-management plugins require positions as `list[dict]` (symbol/exchange/quantity/pnl_rate); dict-keyed format is rejected",
        ],
    }

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

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Combine multiple ConditionNode results into one boolean signal",
            "Require N-of-M indicators to agree before placing an order (`at_least` with a threshold)",
            "Weigh different signals (e.g. RSI 0.5 + MACD 0.3 + Volume 0.2) and require a weighted score above a cutoff",
        ],
        "when_not_to_use": [
            "Single-signal workflow — skip LogicNode and route ConditionNode directly downstream",
            "Symbol intersection / union only — consider SymbolFilterNode for raw symbol set math",
        ],
        "typical_scenarios": [
            "RSI ConditionNode + MACD ConditionNode → LogicNode(operator='all') → NewOrderNode",
            "3 indicator ConditionNodes → LogicNode(operator='at_least', threshold=2) → order",
            "5 strategy ConditionNodes → LogicNode(operator='weighted', threshold=0.6, conditions=[{weight:0.4}, {weight:0.3}, …]) → order",
        ],
    }
    _features: ClassVar[List[str]] = [
        "8 operators: all / any / not / xor / at_least / at_most / exactly / weighted",
        "Consumes ConditionNode results (multiple=True input, min_connections=2) — the executor wires them by edge",
        "Outputs both `result` (composite) and `passed_symbols` (intersection / union depending on operator)",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using LogicNode with a single upstream condition",
            "reason": "LogicNode requires min_connections=2 and adds no value when combining one signal.",
            "alternative": "Consume the ConditionNode directly. Use LogicNode only when you have at least 2 conditions to combine.",
        },
        {
            "pattern": "operator='weighted' with no weights provided",
            "reason": "Default weight is equal per condition, which makes weighted degenerate into at_least with threshold=% agreement. Intent becomes unclear.",
            "alternative": "Populate `conditions: [{weight: 0.4}, {weight: 0.3}, {weight: 0.3}]` matching the upstream order and pick `threshold` intentionally.",
        },
        {
            "pattern": "Feeding LogicNode with raw OHLCV instead of ConditionNode results",
            "reason": "LogicNode expects `condition_result` inputs (is_condition_met / passed_symbols), not arbitrary dicts.",
            "alternative": "Insert a ConditionNode per indicator first, then combine those results through LogicNode.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "AND-combine RSI + MACD",
            "description": "Two condition branches produce independent signals; LogicNode(all) passes only symbols that meet both.",
            "workflow_snippet": {
                "id": "logic-and-rsi-macd",
                "name": "LogicNode all (RSI + MACD)",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "watchlist", "type": "WatchlistNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]},
                    {
                        "id": "historical",
                        "type": "OverseasStockHistoricalDataNode",
                        "symbol": "{{ item }}",
                        "period": "1d",
                        "start_date": "20260301",
                        "end_date": "20260401",
                    },
                    {
                        "id": "rsi",
                        "type": "ConditionNode",
                        "plugin": "RSI",
                        "items": {
                            "from": "{{ item.time_series }}",
                            "extract": {
                                "symbol": "{{ item.symbol }}",
                                "exchange": "{{ item.exchange }}",
                                "date": "{{ row.date }}",
                                "close": "{{ row.close }}",
                            },
                        },
                        "fields": {"period": 14, "threshold": 30, "direction": "below"},
                    },
                    {
                        "id": "macd",
                        "type": "ConditionNode",
                        "plugin": "MACD",
                        "items": {
                            "from": "{{ item.time_series }}",
                            "extract": {
                                "symbol": "{{ item.symbol }}",
                                "exchange": "{{ item.exchange }}",
                                "date": "{{ row.date }}",
                                "close": "{{ row.close }}",
                            },
                        },
                        "fields": {"fast": 12, "slow": 26, "signal": 9, "direction": "bullish_cross"},
                    },
                    {"id": "logic", "type": "LogicNode", "operator": "all"},
                    {"id": "display", "type": "TableDisplayNode", "title": "RSI AND MACD", "data": "{{ nodes.logic.passed_symbols }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "historical"},
                    {"from": "historical", "to": "rsi"},
                    {"from": "historical", "to": "macd"},
                    {"from": "rsi", "to": "logic"},
                    {"from": "macd", "to": "logic"},
                    {"from": "logic", "to": "display"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "logic.passed_symbols contains the intersection of RSI and MACD passing symbols; table displays the final set.",
        },
        {
            "title": "at_least 2-of-3 signal agreement",
            "description": "Three independent signals feed LogicNode(at_least, threshold=2); symbols pass when at least two signals agree.",
            "workflow_snippet": {
                "id": "logic-at-least-2-of-3",
                "name": "LogicNode at_least 2-of-3",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "watchlist", "type": "WatchlistNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]},
                    {
                        "id": "historical",
                        "type": "OverseasStockHistoricalDataNode",
                        "symbol": "{{ item }}",
                        "period": "1d",
                        "start_date": "20260301",
                        "end_date": "20260401",
                    },
                    {
                        "id": "rsi",
                        "type": "ConditionNode",
                        "plugin": "RSI",
                        "items": {"from": "{{ item.time_series }}", "extract": {"symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}", "date": "{{ row.date }}", "close": "{{ row.close }}"}},
                        "fields": {"period": 14, "threshold": 30, "direction": "below"},
                    },
                    {
                        "id": "bollinger",
                        "type": "ConditionNode",
                        "plugin": "BollingerBands",
                        "items": {"from": "{{ item.time_series }}", "extract": {"symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}", "date": "{{ row.date }}", "close": "{{ row.close }}"}},
                        "fields": {"period": 20, "std": 2.0, "direction": "below_lower"},
                    },
                    {
                        "id": "kdj",
                        "type": "ConditionNode",
                        "plugin": "KDJ",
                        "items": {"from": "{{ item.time_series }}", "extract": {"symbol": "{{ item.symbol }}", "exchange": "{{ item.exchange }}", "date": "{{ row.date }}", "close": "{{ row.close }}", "high": "{{ row.high }}", "low": "{{ row.low }}"}},
                        "fields": {"k_period": 9, "d_period": 3, "j_period": 3, "direction": "oversold"},
                    },
                    {"id": "logic", "type": "LogicNode", "operator": "at_least", "threshold": 2},
                    {"id": "display", "type": "TableDisplayNode", "title": "≥2 signals agree", "data": "{{ nodes.logic.passed_symbols }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "historical"},
                    {"from": "historical", "to": "rsi"},
                    {"from": "historical", "to": "bollinger"},
                    {"from": "historical", "to": "kdj"},
                    {"from": "rsi", "to": "logic"},
                    {"from": "bollinger", "to": "logic"},
                    {"from": "kdj", "to": "logic"},
                    {"from": "logic", "to": "display"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "logic.passed_symbols contains symbols where at least 2 out of RSI / Bollinger / KDJ returned passed=true.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "At least 2 ConditionNode inputs must be connected (multiple=True, min_connections=2). Operator determines how they are combined.",
        "output_consumption": "`result` carries the composite condition_result (is_condition_met + passed_symbols). `passed_symbols` is the convenience array for downstream iteration.",
        "common_combinations": [
            "ConditionNode(RSI) + ConditionNode(MACD) → LogicNode(all) → NewOrderNode",
            "3 ConditionNodes → LogicNode(at_least, threshold=2) → order",
            "Weighted: 5 ConditionNodes → LogicNode(weighted, threshold=0.6, conditions=[{weight:.3}, ...]) → order",
        ],
        "pitfalls": [
            "At least 2 input edges are required — the executor rejects LogicNode with a single upstream",
            "Operators at_least / at_most / exactly / weighted need `threshold`; the other operators ignore it",
            "When passing weights, the `conditions` list order must match the upstream edge order (first edge = conditions[0])",
        ],
    }

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