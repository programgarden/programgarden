"""
ProgramGarden Core - Infra Nodes

Infrastructure nodes:
- StartNode: Workflow entry point
- ThrottleNode: Data flow control
- SplitNode: Split list into individual items (item-based execution)
- AggregateNode: Aggregate individual items into a list
- IfNode: Conditional branching (if/else)
"""

from typing import Optional, List, Literal, Dict, TYPE_CHECKING, ClassVar, Any
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class StartNode(BaseNode):
    """
    Workflow entry point

    Required one per Definition. Starting point of workflow execution.
    """

    type: Literal["StartNode"] = "StartNode"
    category: NodeCategory = NodeCategory.INFRA
    description: str = "i18n:nodes.StartNode.description"
    
    # CDN 기반 노드 아이콘 URL (TODO: 실제 CDN URL로 교체)
    _img_url: ClassVar[str] = ""

    _inputs: List[InputPort] = []
    _outputs: List[OutputPort] = [
        OutputPort(
            name="start",
            type="signal",
            description="i18n:ports.start",
            example={"started_at": "2026-04-14T09:30:00-04:00"},
        ),
    ]

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Mark the explicit entry point of a workflow's main flow",
            "Provide a stable anchor node that downstream scheduling / trigger nodes can attach to",
        ],
        "when_not_to_use": [
            "Use ScheduleNode instead when the workflow needs a cron-style recurring trigger",
            "Do not use StartNode inside a sub-branch — it is only valid at the DAG root",
        ],
        "typical_scenarios": [
            "Every workflow has exactly one StartNode at the top of the main flow",
            "Start → Broker → Account / Market / Historical → Condition → Order",
            "Start → ScheduleNode → trading body (scheduled loop with an explicit root)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Zero configuration — no fields, no credentials",
        "Produces a simple trigger signal that flows through main edges",
        "Always completes instantly and never fails",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Multiple StartNodes inside a single workflow",
            "reason": "The DAG resolver treats each StartNode as a separate entry, causing duplicated cycles or ambiguous execution order.",
            "alternative": "Keep a single StartNode and fan out from it via main edges.",
        },
        {
            "pattern": "Omitting StartNode and wiring ScheduleNode as the root",
            "reason": "Works for scheduled workflows but some example templates and validators assume a StartNode anchor.",
            "alternative": "Always include a StartNode and connect it to the ScheduleNode as the first main edge.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Minimal workflow: Start → Broker → Account balance query",
            "description": "Simplest useful workflow — opens a broker connection and reads overseas stock account balance.",
            "workflow_snippet": {
                "id": "start-minimal",
                "name": "Start + account balance",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "StartNode emits a trigger signal; Broker establishes the LS session; Account returns held_symbols / balance / positions.",
        },
        {
            "title": "Start → Watchlist → MarketData (auto-iterate)",
            "description": "Start anchors a watchlist-driven market data lookup that auto-iterates over the watchlist array.",
            "workflow_snippet": {
                "id": "start-watchlist-market",
                "name": "Start + watchlist + market data",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {
                        "id": "watchlist",
                        "type": "WatchlistNode",
                        "symbols": [
                            {"symbol": "AAPL", "exchange": "NASDAQ"},
                            {"symbol": "NVDA", "exchange": "NASDAQ"},
                        ],
                    },
                    {"id": "market", "type": "OverseasStockMarketDataNode", "symbol": "{{ item }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "market"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    }
                ],
            },
            "expected_output": "Start triggers; Watchlist emits an array of 2 symbols; MarketData auto-iterates and merges 2 quote records.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "None. StartNode takes no configuration and no upstream input.",
        "output_consumption": "Emits a single 'trigger' signal on its main output. Downstream nodes just need an edge from StartNode; they do not bind to the signal via expression.",
        "common_combinations": [
            "StartNode → OverseasStockBrokerNode → OverseasStockAccountNode",
            "StartNode → ScheduleNode → (trading body)",
            "StartNode → OverseasStockBrokerNode → WatchlistNode → OverseasStockHistoricalDataNode → ConditionNode",
        ],
        "pitfalls": [
            "Exactly one StartNode per workflow; a second creates two disjoint DAG roots",
            "StartNode is purely structural — use ScheduleNode or TradingHoursFilterNode for timing control",
        ],
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        """StartNode has no configurable fields."""
        return {}


class ThrottleNode(BaseNode):
    """
    Data flow control node (Throttle)
    
    Controls the frequency of data flow from realtime nodes to prevent
    excessive execution of downstream nodes and API rate limiting.
    
    Modes:
    - skip: Ignore incoming data during cooldown
    - latest: Keep only the latest data during cooldown, execute when cooldown ends
    """
    
    type: Literal["ThrottleNode"] = "ThrottleNode"
    category: NodeCategory = NodeCategory.INFRA
    description: str = "i18n:nodes.ThrottleNode.description"
    
    _img_url: ClassVar[str] = ""
    
    # ThrottleNode specific config
    mode: Literal["skip", "latest"] = Field(
        default="latest",
        description="Cooldown mode: skip (ignore) or latest (keep newest)"
    )
    interval_sec: float = Field(
        default=5.0,
        ge=0.1,
        le=300.0,
        description="Minimum execution interval in seconds"
    )
    pass_first: bool = Field(
        default=True,
        description="Pass first data immediately without waiting"
    )
    
    _inputs: List[InputPort] = [
        InputPort(name="data", type="any", description="i18n:ports.data")
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="data", type="any", description="i18n:ports.data"),
        OutputPort(name="_throttle_stats", type="object", description="i18n:ports.throttle_stats"),
    ]

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Rate-limit high-frequency realtime feeds before expensive downstream work (AI agents, order nodes, external APIs)",
            "De-duplicate bursty signals so the strategy acts at most once per interval_sec",
            "Stabilize tick-by-tick data into a predictable cadence for charts / tables",
        ],
        "when_not_to_use": [
            "One-shot queries — ThrottleNode adds no value; omit it entirely",
            "Precise timer behavior — use ScheduleNode (cron-style) instead",
            "Fine-grained order pacing — prefer OrderNode's built-in rate_limit_interval",
        ],
        "typical_scenarios": [
            "RealMarketDataNode → ThrottleNode (mode='latest', interval_sec=30) → AIAgentNode",
            "RealOrderEventNode → ThrottleNode → TelegramNode (prevent notification flood)",
            "RealAccountNode → ThrottleNode (mode='skip') → dashboard refresh",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Two modes: 'skip' (drop during cooldown) and 'latest' (buffer newest, emit at window close)",
        "pass_first=True emits the first event immediately, useful for warm-start flows",
        "Emits _throttle_stats output for observability (received / passed / skipped counts)",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Chaining two ThrottleNodes back-to-back",
            "reason": "The second node's cooldown window compounds with the first, so effective cadence becomes harder to reason about and jittery.",
            "alternative": "Use a single ThrottleNode with the longest required interval_sec, then a plain branch.",
        },
        {
            "pattern": "Using ThrottleNode to enforce order placement pacing",
            "reason": "OrderNodes already expose rate_limit_interval which honors the LS-Sec TR rate limits; ThrottleNode ignores those.",
            "alternative": "Set rate_limit_interval and rate_limit_action on the OrderNode itself.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Throttle realtime stock ticks before an AI agent",
            "description": "RealMarketDataNode emits tick-level updates; ThrottleNode compresses them to at most one per 30 seconds before invoking an AI agent for cost-sensitive analysis.",
            "workflow_snippet": {
                "id": "throttle-realtime-to-ai",
                "name": "Throttled realtime → AI",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "realtime", "type": "OverseasStockRealMarketDataNode", "symbols": [{"symbol": "TSLA", "exchange": "NASDAQ"}]},
                    {"id": "throttle", "type": "ThrottleNode", "mode": "latest", "interval_sec": 30.0, "pass_first": True},
                    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm_cred", "provider": "openai", "model": "gpt-4o-mini"},
                    {"id": "agent", "type": "AIAgentNode", "user_prompt": "Analyze this TSLA tick: {{ nodes.throttle.data }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "realtime"},
                    {"from": "realtime", "to": "throttle"},
                    {"from": "throttle", "to": "agent"},
                    {"from": "llm", "to": "agent", "edge_type": "ai_model"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                    {"credential_id": "llm_cred", "type": "llm_openai", "data": [{"key": "api_key", "value": "", "type": "password", "label": "API Key"}]},
                ],
            },
            "expected_output": "data port emits a single tick every ~30s; _throttle_stats records the skip / pass counts between windows.",
        },
        {
            "title": "Throttle realtime futures for Telegram notifications",
            "description": "Prevents notification flood when a volatile futures product triggers many updates per second.",
            "workflow_snippet": {
                "id": "throttle-realtime-notify",
                "name": "Throttled realtime → Telegram",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasFuturesBrokerNode", "credential_id": "fut_cred"},
                    {"id": "realtime", "type": "OverseasFuturesRealMarketDataNode", "symbols": [{"symbol": "ESZ24", "exchange": "CME"}]},
                    {"id": "throttle", "type": "ThrottleNode", "mode": "skip", "interval_sec": 10.0},
                    {"id": "notify", "type": "TelegramNode", "credential_id": "tg_cred", "message": "ES tick: {{ nodes.throttle.data }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "realtime"},
                    {"from": "realtime", "to": "throttle"},
                    {"from": "throttle", "to": "notify"},
                ],
                "credentials": [
                    {"credential_id": "fut_cred", "type": "broker_ls_overseas_futureoption", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                    {"credential_id": "tg_cred", "type": "telegram_bot", "data": [{"key": "bot_token", "value": "", "type": "password", "label": "Bot Token"}, {"key": "chat_id", "value": "", "type": "text", "label": "Chat ID"}]},
                ],
            },
            "expected_output": "Telegram receives at most one message per 10s; bursts of sub-second ticks are dropped (mode='skip').",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Single 'data' input accepts any payload. In 'latest' mode the payload is replaced on each arrival; in 'skip' mode extras are dropped during cooldown.",
        "output_consumption": "Downstream binds `{{ nodes.throttle.data }}` to receive the forwarded payload. The _throttle_stats port is optional telemetry.",
        "common_combinations": [
            "OverseasStockRealMarketDataNode → ThrottleNode → AIAgentNode",
            "OverseasFuturesRealMarketDataNode → ThrottleNode → TelegramNode",
            "OverseasStockRealAccountNode → ThrottleNode → TableDisplayNode",
        ],
        "pitfalls": [
            "AIAgentNode requires ThrottleNode (or equivalent cooldown_sec) when connected to a realtime source — the executor rejects direct realtime→agent wiring",
            "pass_first=False combined with a long interval_sec delays the first emission by that interval, which can look like the workflow is frozen on startup",
        ],
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "mode": FieldSchema(
                name="mode",
                type=FieldType.ENUM,
                description="i18n:fields.ThrottleNode.mode",
                default="latest",
                enum_values=["skip", "latest"],
                enum_labels={
                    "skip": "i18n:enums.throttle_mode.skip",
                    "latest": "i18n:enums.throttle_mode.latest"
                },
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                example="latest",
                expected_type="str",
            ),
            "interval_sec": FieldSchema(
                name="interval_sec",
                type=FieldType.NUMBER,
                description="i18n:fields.ThrottleNode.interval_sec",
                default=5.0,
                min_value=0.1,
                max_value=300.0,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                placeholder="5.0",
                example=5.0,
                expected_type="float",
            ),
            "pass_first": FieldSchema(
                name="pass_first",
                type=FieldType.BOOLEAN,
                description="i18n:fields.ThrottleNode.pass_first",
                default=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CHECKBOX,
                example=True,
                expected_type="bool",
            ),
        }


class SplitNode(BaseNode):
    """
    Split list into individual items (item-based execution)

    Converts a list input into individual items, triggering downstream nodes
    once for each item. Works with AggregateNode to collect results.

    Execution modes:
    - Sequential (default): Execute items one by one with optional delay
    - Parallel: Execute all items concurrently (relies on internal throttling)
    """

    type: Literal["SplitNode"] = "SplitNode"
    category: NodeCategory = NodeCategory.INFRA
    description: str = "i18n:nodes.SplitNode.description"

    _img_url: ClassVar[str] = ""

    # SplitNode specific config
    parallel: bool = Field(
        default=False,
        description="Execute all items in parallel (default: sequential)"
    )
    delay_ms: int = Field(
        default=0,
        ge=0,
        le=60000,
        description="Delay between items in milliseconds (sequential mode only)"
    )
    continue_on_error: bool = Field(
        default=True,
        description="Continue execution even if one item fails"
    )

    _inputs: List[InputPort] = [
        InputPort(name="array", type="array", description="i18n:ports.split_array")
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="item",
            type="any",
            description="i18n:ports.split_item",
            example={"exchange": "NASDAQ", "symbol": "AAPL"},
        ),
        OutputPort(
            name="index",
            type="integer",
            description="i18n:ports.split_index",
            example=0,
        ),
        OutputPort(
            name="total",
            type="integer",
            description="i18n:ports.split_total",
            example=3,
        ),
    ]

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Explicitly fan out over an array when you want parallel execution, rate-limited delay, or continue-on-error semantics that auto-iterate does not provide",
            "Pair with AggregateNode to collect results into a new list after per-item processing",
            "When the downstream branch has multiple nodes and you need clean item/index/total bindings via `{{ nodes.split.item }}`",
        ],
        "when_not_to_use": [
            "Simple one-step-per-item flows — prefer auto-iterate (`{{ item }}`) which is implicit and needs no extra nodes",
            "When you need ordered results with no parallelism and no delay — auto-iterate already handles this",
        ],
        "typical_scenarios": [
            "WatchlistNode → SplitNode → OverseasStockFundamentalNode (per-symbol fundamental lookup)",
            "MarketUniverseNode → SplitNode (parallel=True) → OverseasStockHistoricalDataNode → AggregateNode",
            "AccountNode (positions array) → SplitNode → OrderNode (liquidate each position with delay_ms)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Sequential (default) or parallel execution modes",
        "Per-item delay_ms for rate-limiting downstream API calls",
        "continue_on_error=True keeps the loop running when one item fails",
        "Emits item / index / total outputs so downstream can branch on position",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using SplitNode when a single downstream node already auto-iterates over the array",
            "reason": "Auto-iterate is implicit and handled by the executor — adding SplitNode duplicates the iteration and doubles the workload.",
            "alternative": "Bind `{{ item }}` directly on the downstream node and delete SplitNode.",
        },
        {
            "pattern": "parallel=True for order-placement loops",
            "reason": "Placing orders concurrently without delay_ms will trip LS-Sec TR rate limits and cause spurious cancellations.",
            "alternative": "Use sequential mode with delay_ms >= 500ms for order-sensitive loops.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Per-symbol fundamental lookup with SplitNode",
            "description": "Watchlist fans out into SplitNode, then OverseasStockFundamentalNode fetches per-symbol data that downstream can display.",
            "workflow_snippet": {
                "id": "split-fundamental",
                "name": "Watchlist → Split → Fundamental",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {
                        "id": "watchlist",
                        "type": "WatchlistNode",
                        "symbols": [
                            {"symbol": "AAPL", "exchange": "NASDAQ"},
                            {"symbol": "MSFT", "exchange": "NASDAQ"},
                        ],
                    },
                    {"id": "split", "type": "SplitNode"},
                    {"id": "fundamental", "type": "OverseasStockFundamentalNode", "symbol": "{{ nodes.split.item }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "split"},
                    {"from": "split", "to": "fundamental"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "Fundamental node executes twice (once per watchlist entry) with item bound to {symbol, exchange}; fundamental merges PER / EPS / market_cap rows for AAPL and MSFT.",
        },
        {
            "title": "Parallel per-symbol historical with delay pacing",
            "description": "MarketUniverseNode produces a symbol list; SplitNode fans out with a 500ms delay between launches to stay within TR rate limits while still running concurrently.",
            "workflow_snippet": {
                "id": "split-historical-parallel",
                "name": "Universe → Split (parallel) → Historical",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "universe", "type": "MarketUniverseNode", "exchange": "NASDAQ", "top_n": 10},
                    {"id": "split", "type": "SplitNode", "parallel": False, "delay_ms": 500, "continue_on_error": True},
                    {
                        "id": "historical",
                        "type": "OverseasStockHistoricalDataNode",
                        "symbol": "{{ nodes.split.item }}",
                        "period": "1d",
                        "start_date": "20260301",
                        "end_date": "20260401",
                    },
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "universe"},
                    {"from": "universe", "to": "split"},
                    {"from": "split", "to": "historical"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "Historical node runs once per top-N symbol with 500ms pacing; any single failure is logged but the remaining items continue.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "`array` input — typically bound implicitly by the upstream array output. No explicit config needed; SplitNode infers the iteration from the DAG.",
        "output_consumption": "Downstream binds `{{ nodes.split.item }}` for the current element, `{{ nodes.split.index }}` for the 0-based position, and `{{ nodes.split.total }}` for the count.",
        "common_combinations": [
            "WatchlistNode → SplitNode → OverseasStockFundamentalNode",
            "MarketUniverseNode → SplitNode (parallel) → OverseasStockHistoricalDataNode → AggregateNode",
            "AccountNode.positions → SplitNode → OrderNode (liquidate each)",
        ],
        "pitfalls": [
            "Explicit SplitNode is redundant when the downstream node already auto-iterates on a plain `{{ item }}` binding",
            "parallel=True ignores delay_ms — use one or the other depending on whether rate limits or latency matter more",
        ],
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "parallel": FieldSchema(
                name="parallel",
                type=FieldType.BOOLEAN,
                description="i18n:fields.SplitNode.parallel",
                default=False,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CHECKBOX,
                example=False,
                expected_type="bool",
            ),
            "delay_ms": FieldSchema(
                name="delay_ms",
                type=FieldType.INTEGER,
                description="i18n:fields.SplitNode.delay_ms",
                default=0,
                min_value=0,
                max_value=60000,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                placeholder="0",
                example=500,
                expected_type="int",
                helper_text="i18n:fields.SplitNode.delay_ms_helper",
            ),
            "continue_on_error": FieldSchema(
                name="continue_on_error",
                type=FieldType.BOOLEAN,
                description="i18n:fields.SplitNode.continue_on_error",
                default=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                ui_component=UIComponent.CHECKBOX,
                example=True,
                expected_type="bool",
            ),
        }


class AggregateNode(BaseNode):
    """
    Aggregate individual items into a list

    Collects results from SplitNode branches and outputs as a list.
    Supports various aggregation modes: collect, filter, sum, avg, min, max, count, first, last.
    """

    type: Literal["AggregateNode"] = "AggregateNode"
    category: NodeCategory = NodeCategory.INFRA
    description: str = "i18n:nodes.AggregateNode.description"

    _img_url: ClassVar[str] = ""

    # AggregateNode specific config
    mode: Literal["collect", "filter", "sum", "avg", "min", "max", "count", "first", "last"] = Field(
        default="collect",
        description="Aggregation mode"
    )
    filter_field: Optional[str] = Field(
        default="passed",
        description="Field to filter by (for filter mode)"
    )
    value_field: Optional[str] = Field(
        default="value",
        description="Field to aggregate (for sum/avg/min/max modes)"
    )

    _inputs: List[InputPort] = [
        InputPort(name="item", type="any", description="i18n:ports.aggregate_item")
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="array",
            type="array",
            description="i18n:ports.aggregate_array",
            example=[
                {"exchange": "NASDAQ", "symbol": "AAPL", "rsi": 28.5},
                {"exchange": "NASDAQ", "symbol": "TSLA", "rsi": 62.1},
            ],
        ),
        OutputPort(
            name="value",
            type="number",
            description="i18n:ports.aggregate_value",
            example=45.3,
        ),
        OutputPort(
            name="count",
            type="integer",
            description="i18n:ports.aggregate_count",
            example=2,
        ),
    ]

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Collect per-item results from a SplitNode branch back into a single array",
            "Compute a scalar summary (sum / avg / min / max / count) over per-item outputs without writing a custom plugin",
            "Filter a per-item stream down to just the passing rows (mode='filter')",
        ],
        "when_not_to_use": [
            "Downstream node already auto-iterates — there is no per-item branch to collect",
            "Simple array pass-through where no aggregation is needed; use FieldMappingNode or a direct expression",
        ],
        "typical_scenarios": [
            "SplitNode → per-item ConditionNode → AggregateNode (mode='filter') → NewOrderNode for symbols that passed",
            "SplitNode → OverseasStockHistoricalDataNode → AggregateNode (mode='collect') → TableDisplayNode",
            "SplitNode → per-symbol PnL calc → AggregateNode (mode='sum', value_field='pnl') → display",
        ],
    }
    _features: ClassVar[List[str]] = [
        "9 aggregation modes: collect / filter / sum / avg / min / max / count / first / last",
        "filter_field picks which boolean field flags an item as passing (for mode='filter')",
        "value_field picks which numeric field feeds arithmetic modes (sum/avg/min/max)",
        "Dual outputs: `array` for list-shaped modes, `value` / `count` for scalar modes",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Using mode='collect' on a branch that did not go through SplitNode",
            "reason": "AggregateNode was designed as SplitNode's counterpart; without the per-item fan-out, the input is a single value and aggregation is a no-op.",
            "alternative": "Either add an upstream SplitNode, or drop AggregateNode and consume the array directly.",
        },
        {
            "pattern": "Setting mode='sum' without value_field matching the actual numeric key",
            "reason": "The default value_field='value' rarely exists in real payloads, so the sum silently returns 0.",
            "alternative": "Always set value_field to the actual numeric key (e.g. 'pnl', 'quantity', 'volume').",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Filter passing symbols and aggregate back into an array",
            "description": "SplitNode fans out symbols; per-item ConditionNode decides pass/fail; AggregateNode collects only the passing ones for downstream action.",
            "workflow_snippet": {
                "id": "aggregate-filter-passing",
                "name": "Split → Condition → Aggregate (filter)",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {
                        "id": "watchlist",
                        "type": "WatchlistNode",
                        "symbols": [
                            {"symbol": "AAPL", "exchange": "NASDAQ"},
                            {"symbol": "TSLA", "exchange": "NASDAQ"},
                            {"symbol": "NVDA", "exchange": "NASDAQ"},
                        ],
                    },
                    {"id": "split", "type": "SplitNode"},
                    {
                        "id": "historical",
                        "type": "OverseasStockHistoricalDataNode",
                        "symbol": "{{ nodes.split.item }}",
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
                    {"id": "aggregate", "type": "AggregateNode", "mode": "filter", "filter_field": "passed"},
                    {"id": "display", "type": "TableDisplayNode", "title": "Oversold symbols", "data": "{{ nodes.aggregate.array }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "watchlist"},
                    {"from": "watchlist", "to": "split"},
                    {"from": "split", "to": "historical"},
                    {"from": "historical", "to": "rsi"},
                    {"from": "rsi", "to": "aggregate"},
                    {"from": "aggregate", "to": "display"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "aggregate.array holds only the watchlist entries whose RSI condition returned passed=true; other symbols are dropped.",
        },
        {
            "title": "Sum per-symbol P&L across positions",
            "description": "Positions array fans out through SplitNode; per-item calculation produces pnl; AggregateNode sums them for a portfolio P&L.",
            "workflow_snippet": {
                "id": "aggregate-sum-pnl",
                "name": "Positions → Split → Sum P&L",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "split", "type": "SplitNode"},
                    {
                        "id": "mapper",
                        "type": "FieldMappingNode",
                        "mappings": {
                            "symbol": "{{ nodes.split.item.symbol }}",
                            "pnl": "{{ nodes.split.item.unrealized_pnl }}",
                        },
                    },
                    {"id": "agg", "type": "AggregateNode", "mode": "sum", "value_field": "pnl"},
                    {"id": "display", "type": "SummaryDisplayNode", "title": "Total P&L", "data": {"total_pnl": "{{ nodes.agg.value }}"}},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "split"},
                    {"from": "split", "to": "mapper"},
                    {"from": "mapper", "to": "agg"},
                    {"from": "agg", "to": "display"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "agg.value is the sum of unrealized_pnl across every open position; SummaryDisplayNode renders it as a single number.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "`item` input receives one value per iteration from the upstream SplitNode branch. Aggregation happens when the branch completes.",
        "output_consumption": "For array-shaped modes bind `{{ nodes.aggregate.array }}`. For scalar modes bind `{{ nodes.aggregate.value }}` (sum/avg/min/max/first/last) or `{{ nodes.aggregate.count }}` (count mode).",
        "common_combinations": [
            "SplitNode → ConditionNode → AggregateNode (mode='filter')",
            "SplitNode → HistoricalDataNode → AggregateNode (mode='collect') → TableDisplayNode",
            "SplitNode → per-item FieldMappingNode → AggregateNode (mode='sum')",
        ],
        "pitfalls": [
            "mode='filter' needs the upstream per-item output to include the filter_field (default 'passed') as a boolean",
            "Scalar modes (sum/avg/min/max) require every per-item output to include value_field — otherwise entries silently contribute 0",
        ],
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import FieldSchema, FieldType, FieldCategory, UIComponent, ExpressionMode
        return {
            "mode": FieldSchema(
                name="mode",
                type=FieldType.ENUM,
                description="i18n:fields.AggregateNode.mode",
                default="collect",
                enum_values=["collect", "filter", "sum", "avg", "min", "max", "count", "first", "last"],
                enum_labels={
                    "collect": "i18n:enums.aggregate_mode.collect",
                    "filter": "i18n:enums.aggregate_mode.filter",
                    "sum": "i18n:enums.aggregate_mode.sum",
                    "avg": "i18n:enums.aggregate_mode.avg",
                    "min": "i18n:enums.aggregate_mode.min",
                    "max": "i18n:enums.aggregate_mode.max",
                    "count": "i18n:enums.aggregate_mode.count",
                    "first": "i18n:enums.aggregate_mode.first",
                    "last": "i18n:enums.aggregate_mode.last",
                },
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                example="collect",
                expected_type="str",
            ),
            "filter_field": FieldSchema(
                name="filter_field",
                type=FieldType.STRING,
                description="i18n:fields.AggregateNode.filter_field",
                default="passed",
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                placeholder="passed",
                example="passed",
                expected_type="str",
                helper_text="i18n:fields.AggregateNode.filter_field_helper",
            ),
            "value_field": FieldSchema(
                name="value_field",
                type=FieldType.STRING,
                description="i18n:fields.AggregateNode.value_field",
                default="value",
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                placeholder="value",
                example="value",
                expected_type="str",
                helper_text="i18n:fields.AggregateNode.value_field_helper",
            ),
        }


class IfNode(BaseNode):
    """
    조건 분기 노드

    left와 right 값을 operator로 비교하여 true/false 브랜치로 실행 흐름을 분기합니다.
    조건이 참이면 true 포트로, 거짓이면 false 포트로 데이터가 전달됩니다.

    Edge에 from_port를 지정하여 분기 경로를 설정합니다:
    - {"from": "if1", "to": "order", "from_port": "true"}
    - {"from": "if1", "to": "notify", "from_port": "false"}
    """

    type: Literal["IfNode"] = "IfNode"
    category: NodeCategory = NodeCategory.INFRA
    description: str = "i18n:nodes.IfNode.description"

    _img_url: ClassVar[str] = ""

    # 비교 연산 필드
    left: Any = Field(default=None, description="왼쪽 피연산자 (표현식 바인딩 가능)")
    operator: Literal[
        "==", "!=", ">", ">=", "<", "<=",
        "in", "not_in",
        "contains", "not_contains",
        "is_empty", "is_not_empty",
    ] = Field(default="==", description="비교 연산자")
    right: Any = Field(default=None, description="오른쪽 피연산자 (표현식 바인딩 가능)")

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger"),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="true",
            type="any",
            description="i18n:ports.if_true",
            example={"passed": True, "value": "whatever left operand resolved to"},
        ),
        OutputPort(
            name="false",
            type="any",
            description="i18n:ports.if_false",
            example={"passed": False, "value": "whatever left operand resolved to"},
        ),
        OutputPort(
            name="result",
            type="boolean",
            description="i18n:ports.if_result",
            example=True,
        ),
    ]

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Branch the DAG based on a scalar comparison (balance, count, RSI, flags) without authoring a plugin",
            "Gate order placement behind a pre-condition (e.g. fear index below threshold, market open)",
            "Split display / notification paths by state (e.g. profitable → chart, losing → alert)",
        ],
        "when_not_to_use": [
            "Per-item boolean filtering of an array — use ConditionNode which supports plugin logic and items.from fanout",
            "Multi-condition boolean logic — compose with LogicNode (AND/OR of several conditions) instead of chaining IfNodes",
            "Scheduled time-window gating — use ScheduleNode or TradingHoursFilterNode for cron / market-hours semantics",
        ],
        "typical_scenarios": [
            "AccountNode.balance → IfNode (>= threshold) → true: OrderNode / false: SummaryDisplayNode (insufficient funds)",
            "FearGreedIndexNode.value → IfNode (<= 25) → true: alert / false: normal flow",
            "ConditionNode.passed → IfNode (== true) → true: NewOrderNode / false: LogNode",
        ],
    }
    _features: ClassVar[List[str]] = [
        "12 comparison operators including ==, !=, >, >=, <, <=, in, not_in, contains, not_contains, is_empty, is_not_empty",
        "Three outputs: `true` / `false` payloads + `result` boolean — edges use from_port to route",
        "Expression binding on both `left` and `right` operands — supports full `{{ nodes.X.Y }}` syntax",
        "Cascading skip — downstream of the inactive branch is auto-skipped by the executor",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Connecting IfNode output edges without `from_port`",
            "reason": "Edges default to fan-out from every output port, so both branches fire regardless of the condition.",
            "alternative": "Always set `from_port: 'true'` or `from_port: 'false'` on edges leaving IfNode, or use the dot notation `\"from\": \"if1.true\"`.",
        },
        {
            "pattern": "Node id containing a hyphen (e.g. `if-balance`)",
            "reason": "The expression evaluator parses `-` as subtraction, so `{{ nodes.if-balance.true }}` breaks.",
            "alternative": "Use snake_case or camelCase id (e.g. `if_balance`, `ifBalance`).",
        },
        {
            "pattern": "Using IfNode inside a loop where the condition depends on per-item data",
            "reason": "IfNode decides once per flow cycle, not per item; the loop iterations all see the same branch.",
            "alternative": "Use ConditionNode (plugin-backed) for per-item filtering inside auto-iterate branches.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Gate new order behind a minimum balance",
            "description": "IfNode checks the account balance; true branch places the order, false branch displays a warning.",
            "workflow_snippet": {
                "id": "if-balance-gate",
                "name": "If balance ≥ threshold → order / else notify",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "if_balance", "type": "IfNode", "left": "{{ nodes.account.balance }}", "operator": ">=", "right": 1000},
                    {"id": "order", "type": "OverseasStockNewOrderNode", "symbol": "AAPL", "exchange": "NASDAQ", "side": "buy", "quantity": 1, "price": 150.0},
                    {"id": "warn", "type": "SummaryDisplayNode", "title": "Insufficient funds", "data": {"balance": "{{ nodes.account.balance }}"}},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "account"},
                    {"from": "account", "to": "if_balance"},
                    {"from": "if_balance", "to": "order", "from_port": "true"},
                    {"from": "if_balance", "to": "warn", "from_port": "false"},
                ],
                "credentials": [
                    {"credential_id": "broker_cred", "type": "broker_ls_overseas_stock", "data": [{"key": "appkey", "value": "", "type": "password", "label": "App Key"}, {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"}]},
                ],
            },
            "expected_output": "If balance ≥ 1000 the order node executes; otherwise SummaryDisplayNode renders the insufficient-funds warning.",
        },
        {
            "title": "Extreme fear alert from external market data",
            "description": "Fear & Greed index below 25 triggers a risk alert, otherwise the normal dashboard branch continues.",
            "workflow_snippet": {
                "id": "if-fear-alert",
                "name": "If fear index ≤ 25 → alert / else dashboard",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "fgi", "type": "FearGreedIndexNode"},
                    {"id": "if_fear", "type": "IfNode", "left": "{{ nodes.fgi.value }}", "operator": "<=", "right": 25},
                    {"id": "alert", "type": "SummaryDisplayNode", "title": "Extreme fear detected", "data": {"value": "{{ nodes.fgi.value }}", "action": "Reduce exposure"}},
                    {"id": "normal", "type": "SummaryDisplayNode", "title": "Market sentiment OK", "data": {"value": "{{ nodes.fgi.value }}"}},
                ],
                "edges": [
                    {"from": "start", "to": "fgi"},
                    {"from": "fgi", "to": "if_fear"},
                    {"from": "if_fear", "to": "alert", "from_port": "true"},
                    {"from": "if_fear", "to": "normal", "from_port": "false"},
                ],
                "credentials": [],
            },
            "expected_output": "alert SummaryDisplay renders only when the fear index ≤ 25; otherwise normal SummaryDisplay renders.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Bind `left` and (usually) `right` via `{{ nodes.X.Y }}` expressions. Operators that take no right-hand side — is_empty, is_not_empty — ignore `right`.",
        "output_consumption": "Downstream edges must carry `from_port: 'true'` or `from_port: 'false'` to pick a branch. You can also bind `{{ nodes.if.result }}` as a boolean on a later node.",
        "common_combinations": [
            "AccountNode → IfNode (balance ≥ N) → OrderNode / Notification",
            "FearGreedIndexNode → IfNode (value ≤ 25) → alert branch",
            "ConditionNode.passed → IfNode (== true) → order branch",
        ],
        "pitfalls": [
            "Edges leaving IfNode MUST set from_port — without it both branches run",
            "Avoid hyphens in the node id (`if-balance` breaks expression parsing); use `if_balance` instead",
            "IfNode runs once per cycle; for per-item boolean filtering use ConditionNode (plugin-backed)",
        ],
    }

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode,
        )
        return {
            "left": FieldSchema(
                name="left",
                type=FieldType.STRING,
                description="i18n:fields.IfNode.left",
                required=True,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="{{ nodes.account.balance }}",
                example="{{ nodes.account.balance }}",
                expected_type="any",
            ),
            "operator": FieldSchema(
                name="operator",
                type=FieldType.ENUM,
                description="i18n:fields.IfNode.operator",
                default="==",
                enum_values=[
                    "==", "!=", ">", ">=", "<", "<=",
                    "in", "not_in",
                    "contains", "not_contains",
                    "is_empty", "is_not_empty",
                ],
                enum_labels={
                    "==": "i18n:enums.if_operator.eq",
                    "!=": "i18n:enums.if_operator.ne",
                    ">": "i18n:enums.if_operator.gt",
                    ">=": "i18n:enums.if_operator.gte",
                    "<": "i18n:enums.if_operator.lt",
                    "<=": "i18n:enums.if_operator.lte",
                    "in": "i18n:enums.if_operator.in",
                    "not_in": "i18n:enums.if_operator.not_in",
                    "contains": "i18n:enums.if_operator.contains",
                    "not_contains": "i18n:enums.if_operator.not_contains",
                    "is_empty": "i18n:enums.if_operator.is_empty",
                    "is_not_empty": "i18n:enums.if_operator.is_not_empty",
                },
                required=True,
                expression_mode=ExpressionMode.FIXED_ONLY,
                category=FieldCategory.PARAMETERS,
                example=">=",
            ),
            "right": FieldSchema(
                name="right",
                type=FieldType.STRING,
                description="i18n:fields.IfNode.right",
                required=False,
                expression_mode=ExpressionMode.BOTH,
                category=FieldCategory.PARAMETERS,
                placeholder="1000000",
                example="1000000",
                expected_type="any",
                visible_when={
                    "operator": [
                        "==", "!=", ">", ">=", "<", "<=",
                        "in", "not_in", "contains", "not_contains",
                    ],
                },
            ),
        }
