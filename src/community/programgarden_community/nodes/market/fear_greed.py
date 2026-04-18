"""
ProgramGarden Community - FearGreedIndexNode

CNN 공포/탐욕 지수 노드.
credential 불필요, 설정 없이 놓기만 하면 동작합니다.
시장 심리의 대표 지표 (0=극단적 공포, 100=극단적 탐욕).

사용 예시:
    {
        "id": "fgi",
        "type": "FearGreedIndexNode"
    }
"""

from typing import Optional, List, Literal, Dict, Any, ClassVar, Tuple, TYPE_CHECKING
from pydantic import Field

if TYPE_CHECKING:
    from programgarden_core.models.field_binding import FieldSchema

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
    RetryableError,
)
from programgarden_core.models.resilience import (
    ResilienceConfig,
    RetryConfig,
    FallbackConfig,
    FallbackMode,
)
from programgarden_core.models.connection_rule import (
    ConnectionRule,
    ConnectionSeverity,
    RateLimitConfig,
    REALTIME_SOURCE_NODE_TYPES,
)
from programgarden_core.nodes.market_external import (
    _fetch_json_with_fallback,
    _classify_retryable_error,
)


class FearGreedIndexNode(BaseNode):
    """
    CNN 공포/탐욕 지수 노드

    credential 불필요. 설정 없이 놓기만 하면 동작합니다.
    시장 심리의 대표 지표 (0=극단적 공포, 100=극단적 탐욕).

    Example DSL:
        {
            "id": "fgi",
            "type": "FearGreedIndexNode"
        }
    """

    type: Literal["FearGreedIndexNode"] = "FearGreedIndexNode"
    category: NodeCategory = NodeCategory.MARKET
    description: str = "i18n:nodes.FearGreedIndexNode.description"
    _img_url: ClassVar[str] = ""

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Gate a trading workflow based on overall market sentiment — only trade when the index is in 'Fear' or below a threshold",
            "Provide market context to an AIAgentNode so the LLM can factor sentiment into its analysis or recommendation",
            "Generate a daily sentiment log by storing the index value in SQLiteNode for trend tracking",
            "Combine with technical indicators (RSI, MACD) to require both technical signal and sentiment alignment before entering a position",
        ],
        "when_not_to_use": [
            "As a high-frequency signal source — the CNN Fear & Greed Index is a daily indicator; polling more often than every 5 minutes yields stale data",
            "For per-symbol or sector sentiment — the index reflects broad US equity market sentiment only, not individual stock mood",
            "When the CNN API is unreliable for your use case — it is an unofficial endpoint with no SLA; use resilience settings accordingly",
        ],
        "typical_scenarios": [
            "StartNode → FearGreedIndexNode → IfNode (value < 30 → extreme fear) → OverseasStockNewOrderNode (buy dip)",
            "StartNode → FearGreedIndexNode → AIAgentNode (include sentiment in LLM prompt)",
            "StartNode → FearGreedIndexNode → SQLiteNode (log daily sentiment value)",
        ],
    }
    _features: ClassVar[List[str]] = [
        "No credential or configuration required — drop into any workflow and it works out of the box",
        "Returns three outputs: 'value' (0–100 numeric score), 'label' (Extreme Fear / Fear / Neutral / Greed / Extreme Greed), and 'previous_close' for day-over-day comparison",
        "Built-in rate limiting (min 5-minute interval) prevents excessive CNN API calls during rapid workflow cycles",
        "Resilience config supports automatic retry (default 3 attempts) and configurable fallback on permanent failure",
        "is_tool_enabled=True — AI Agent can invoke this node as a tool to read current market sentiment on demand",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Calling FearGreedIndexNode every tick from a real-time data node without ThrottleNode",
            "reason": "The CNN API is an unofficial endpoint with no rate-limit guarantee. Calling it on every market tick risks IP throttling or ban.",
            "alternative": "Connect through ThrottleNode set to at least 300 seconds, or call FearGreedIndexNode only at the start of a scheduled cycle.",
        },
        {
            "pattern": "Using the Fear & Greed value as the sole entry signal without technical confirmation",
            "reason": "Sentiment indices lag price action and are noisy; trading on them alone produces excessive false signals.",
            "alternative": "Combine with at least one technical indicator (RSI, MACD, Bollinger Bands) via LogicNode to require signal alignment.",
        },
        {
            "pattern": "Treating 'label' as an enum for exact string comparison without accounting for boundary values",
            "reason": "'Neutral' covers a 10-point band (46–55). Comparing label == 'Fear' misses value=45.9 which is borderline.",
            "alternative": "Use the numeric 'value' output in IfNode comparisons (e.g. value < 30) for precise thresholding.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Buy only during extreme fear",
            "description": "Fetch the Fear & Greed index and only proceed to buy AAPL when the score is below 25 (Extreme Fear).",
            "workflow_snippet": {
                "id": "fgi_contrarian_buy",
                "name": "Fear Greed Contrarian Buy",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "fgi", "type": "FearGreedIndexNode"},
                    {"id": "gate", "type": "IfNode", "left": "{{ nodes.fgi.value }}", "operator": "<", "right": 25},
                    {"id": "order", "type": "OverseasStockNewOrderNode", "symbol": "AAPL", "exchange": "NASDAQ", "side": "buy", "order_type": "market", "quantity": 1},
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.fgi.value }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "broker", "to": "fgi"},
                    {"from": "fgi", "to": "gate"},
                    {"from": "gate", "to": "order", "from_port": "true"},
                    {"from": "gate", "to": "display", "from_port": "false"},
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
            "expected_output": "When value < 25: order placed. Otherwise: display node shows current FGI value.",
        },
        {
            "title": "Feed sentiment to AI Agent for context-aware analysis",
            "description": "Pass the Fear & Greed index to an AIAgentNode so the LLM incorporates market sentiment when evaluating a technical signal.",
            "workflow_snippet": {
                "id": "fgi_ai_context",
                "name": "Fear Greed AI Context",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "fgi", "type": "FearGreedIndexNode"},
                    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm_cred", "model": "gpt-4o-mini"},
                    {
                        "id": "agent",
                        "type": "AIAgentNode",
                        "prompt": "Market sentiment is {{ nodes.fgi.label }} (score={{ nodes.fgi.value }}). Should we buy AAPL today?",
                        "output_format": "text",
                    },
                    {"id": "display", "type": "TableDisplayNode", "data": "{{ nodes.agent.text }}"},
                ],
                "edges": [
                    {"from": "start", "to": "fgi"},
                    {"from": "fgi", "to": "agent"},
                    {"from": "llm", "to": "agent", "type": "ai_model"},
                    {"from": "agent", "to": "display"},
                ],
                "credentials": [
                    {
                        "credential_id": "llm_cred",
                        "type": "llm_openai",
                        "data": [
                            {"key": "api_key", "value": "", "type": "password", "label": "API Key"},
                        ],
                    }
                ],
            },
            "expected_output": "AIAgentNode text output containing the LLM's market opinion incorporating the Fear & Greed index.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "FearGreedIndexNode takes only an optional 'trigger' signal. No configuration is required. The node fetches the CNN Fear & Greed API on execution and returns results immediately. No upstream data input is consumed.",
        "output_consumption": "Use 'value' (float 0–100) in IfNode comparisons for precise thresholding. Use 'label' (string) for display or LLM prompt injection. Use 'previous_close' to calculate day-over-day sentiment momentum.",
        "common_combinations": [
            "FearGreedIndexNode → IfNode (sentiment gate) → OverseasStockNewOrderNode",
            "FearGreedIndexNode → AIAgentNode (sentiment context in prompt)",
            "FearGreedIndexNode → SQLiteNode (daily log) → LineChartNode",
        ],
        "pitfalls": [
            "The CNN API endpoint is unofficial and may change without notice — monitor for HTTP errors and set resilience.fallback.mode='skip' for non-critical sentiment checks.",
            "'previous_close' can be 0 if the API response omits it — always guard against division by zero when computing day-over-day change.",
            "The index is updated once per day (US market hours); do not expect intraday movement in 'value' across workflow cycles.",
        ],
    }

    # 실시간 노드에서 직접 연결 차단
    _connection_rules: ClassVar[List[ConnectionRule]] = [
        ConnectionRule(
            deny_direct_from=REALTIME_SOURCE_NODE_TYPES,
            required_intermediate="ThrottleNode",
            severity=ConnectionSeverity.WARNING,
            reason="i18n:connection_rules.realtime_to_external_api.reason",
            suggestion="i18n:connection_rules.realtime_to_external_api.suggestion",
        ),
    ]

    # L-2: CNN 비공식 API → 보수적 5분 간격
    _rate_limit: ClassVar[Optional[RateLimitConfig]] = RateLimitConfig(
        min_interval_sec=300,
        max_concurrent=1,
        on_throttle="queue",
    )

    # === SETTINGS ===
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="i18n:fields.FearGreedIndexNode.timeout_seconds",
    )

    # === Resilience ===
    resilience: ResilienceConfig = Field(
        default_factory=lambda: ResilienceConfig(
            retry=RetryConfig(enabled=True, max_retries=3),
            fallback=FallbackConfig(mode=FallbackMode.ERROR),
        ),
        description="재시도 및 실패 처리 설정",
    )

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return True

    _inputs: List[InputPort] = [
        InputPort(name="trigger", type="signal", description="i18n:ports.trigger", required=False),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(name="value", type="number", description="i18n:outputs.FearGreedIndexNode.value"),
        OutputPort(name="label", type="string", description="i18n:outputs.FearGreedIndexNode.label"),
        OutputPort(name="previous_close", type="number", description="i18n:outputs.FearGreedIndexNode.previous_close"),
    ]

    @classmethod
    def get_field_schema(cls) -> Dict[str, "FieldSchema"]:
        from programgarden_core.models.field_binding import (
            FieldSchema, FieldType, FieldCategory, ExpressionMode, UIComponent,
        )
        return {
            "timeout_seconds": FieldSchema(
                name="timeout_seconds",
                type=FieldType.NUMBER,
                description="i18n:fields.FearGreedIndexNode.timeout_seconds",
                default=30,
                min=5,
                max=120,
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
            ),
            "resilience": FieldSchema(
                name="resilience",
                type=FieldType.OBJECT,
                description="i18n:fields.FearGreedIndexNode.resilience",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CUSTOM_RESILIENCE_EDITOR,
                object_schema=[
                    {"name": "retry.enabled", "type": "BOOLEAN", "default": True, "description": "자동 재시도 활성화"},
                    {"name": "retry.max_retries", "type": "INTEGER", "default": 3, "min_value": 1, "max_value": 10, "description": "최대 재시도 횟수"},
                    {"name": "fallback.mode", "type": "ENUM", "default": "error", "enum_values": ["error", "skip", "default_value"], "description": "모든 재시도 실패 시 동작"},
                ],
                group="resilience",
            ),
        }

    async def execute(self, context: Any) -> Dict[str, Any]:
        """CNN 공포/탐욕 지수 조회 (L-1: 단일 provider, 대안 API 없음)"""
        _CNN_HEADERS = {
            "User-Agent": "Mozilla/5.0 (compatible; ProgramGarden/1.0)",
            "Accept": "application/json",
        }

        urls: List[Tuple[str, str, Optional[Dict[str, str]]]] = [
            (
                "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
                "CNN",
                _CNN_HEADERS,
            ),
        ]

        data = await _fetch_json_with_fallback(urls, self.timeout_seconds)

        # 응답 파싱
        fng = data.get("fear_and_greed", {})
        score = fng.get("score", 0)
        rating = fng.get("rating", "")
        previous_close = fng.get("previous_close", 0)

        # rating → label 매핑
        label = self._normalize_label(rating, score)

        return {
            "value": round(score, 1),
            "label": label,
            "previous_close": round(previous_close, 1) if previous_close else 0,
        }

    @staticmethod
    def _normalize_label(rating: str, score: float) -> str:
        """API rating 문자열을 표준 라벨로 정규화"""
        if rating:
            r = rating.lower().replace(" ", "_")
            label_map = {
                "extreme_fear": "Extreme Fear",
                "fear": "Fear",
                "neutral": "Neutral",
                "greed": "Greed",
                "extreme_greed": "Extreme Greed",
            }
            if r in label_map:
                return label_map[r]

        # rating이 없으면 score 기반 판별
        if score <= 25:
            return "Extreme Fear"
        elif score <= 45:
            return "Fear"
        elif score <= 55:
            return "Neutral"
        elif score <= 75:
            return "Greed"
        else:
            return "Extreme Greed"

    def is_retryable_error(self, error: Exception) -> Optional[RetryableError]:
        return _classify_retryable_error(error)
