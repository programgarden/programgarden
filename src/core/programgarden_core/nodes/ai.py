"""
ProgramGarden Core - AI 노드 정의

AI Agent 시스템을 구성하는 노드:
- LLMModelNode: LLM API 연결 제공 (BrokerNode 패턴)
- AIAgentNode: 범용 AI 에이전트 (tool 엣지로 연결된 기존 노드를 도구로 활용)
"""

from typing import Optional, Dict, Any, List, Literal, ClassVar

from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)
from programgarden_core.models.field_binding import (
    FieldSchema,
    FieldType,
    FieldCategory,
    ExpressionMode,
    UIComponent,
)
from programgarden_core.models.connection_rule import (
    ConnectionRule,
    ConnectionSeverity,
    RateLimitConfig,
    REALTIME_SOURCE_NODE_TYPES,
)


class LLMModelNode(BaseNode):
    """
    LLM 모델 연결 노드 - AI Agent에 LLM 연결을 제공

    BrokerNode 패턴과 동일: credential로 API 연결, ai_model 엣지로 AIAgentNode에 전파.
    같은 LLMModelNode를 여러 AIAgentNode가 공유 가능.
    """

    type: Literal["LLMModelNode"] = "LLMModelNode"
    category: NodeCategory = NodeCategory.AI

    # === LLM 설정 ===
    credential_id: Optional[str] = Field(
        default=None,
        description="LLM API credential (llm_openai, llm_anthropic, llm_deepseek 등)",
    )
    model: str = Field(
        default="gpt-4o",
        description="LLM 모델 ID",
    )
    temperature: float = Field(
        default=0.7,
        description="생성 온도 (0.0 ~ 2.0)",
    )
    max_tokens: int = Field(
        default=1000,
        description="최대 출력 토큰 수",
    )
    seed: Optional[int] = Field(
        default=None,
        description="재현성용 시드 (OpenAI seed 파라미터)",
    )
    streaming: bool = Field(
        default=False,
        description="스트리밍 응답 사용 여부",
    )

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Provide an LLM API connection to one or more AIAgentNodes — analogous to OverseasStockBrokerNode for broker connections",
            "Switch between LLM providers (OpenAI, Anthropic, DeepSeek, Google) without changing AIAgentNode configuration",
            "Share one LLMModelNode connection across multiple AIAgentNodes in the same workflow",
            "Control model parameters (temperature, max_tokens, seed) centrally for reproducible AI responses",
        ],
        "when_not_to_use": [
            "LLMModelNode itself does not generate responses — it only provides the connection. Always pair it with AIAgentNode.",
            "For simple text processing without LLM — use FieldMappingNode or expression bindings instead",
        ],
        "typical_scenarios": [
            "LLMModelNode (OpenAI gpt-4o) → AIAgentNode (ai_model edge) — basic LLM-powered agent",
            "LLMModelNode (Anthropic claude) → AIAgentNode1 (risk_manager) + AIAgentNode2 (news_analyst) — shared LLM for two agents",
            "LLMModelNode (temperature=0) → AIAgentNode (structured output) — deterministic trading signal generation",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Supports four LLM providers: llm_openai, llm_anthropic, llm_deepseek, llm_google via credential_id",
        "Configurable model ID, temperature (0.0-2.0), max_tokens, seed (for reproducibility), and streaming flag",
        "Connects to AIAgentNode via 'ai_model' edge type — NOT a 'main' edge",
        "One LLMModelNode can supply multiple AIAgentNodes (fan-out pattern, each agent gets its own connection context)",
        "is_tool_enabled=False — LLMModelNode itself cannot be used as a tool by AIAgentNode",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Connecting LLMModelNode to AIAgentNode with a regular 'main' edge instead of an 'ai_model' edge",
            "reason": "A main edge triggers DAG execution order but does not inject the LLM connection into AIAgentNode. The agent will fail with 'no LLM model configured'.",
            "alternative": "Use edge type 'ai_model': {\"from\": \"llm\", \"to\": \"agent\", \"type\": \"ai_model\"}",
        },
        {
            "pattern": "Using an OpenAI credential_id with a model name from Anthropic (e.g. credential=llm_openai, model='claude-sonnet-4')",
            "reason": "The credential type determines which API endpoint is called. Mixing providers causes authentication errors.",
            "alternative": "Match credential type to model: llm_openai → gpt-4o/gpt-4o-mini, llm_anthropic → claude-* models.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Minimal LLM connection to AIAgentNode",
            "description": "LLMModelNode connects to AIAgentNode via ai_model edge, providing GPT-4o for market commentary generation.",
            "workflow_snippet": {
                "id": "llm_basic",
                "name": "LLM Basic Connection",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm_cred", "model": "gpt-4o", "temperature": 0.7, "max_tokens": 500},
                    {"id": "agent", "type": "AIAgentNode", "user_prompt": "Describe the current market sentiment in one paragraph.", "output_format": "text", "max_tool_calls": 0, "cooldown_sec": 60},
                    {"id": "summary", "type": "SummaryDisplayNode", "title": "Market Commentary", "data": "{{ nodes.agent.response }}"},
                ],
                "edges": [
                    {"from": "start", "to": "llm"},
                    {"from": "llm", "to": "agent", "type": "ai_model"},
                    {"from": "agent", "to": "summary"},
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
            "expected_output": "A text response from GPT-4o displayed in the SummaryDisplayNode.",
        },
        {
            "title": "Anthropic Claude with low temperature for deterministic structured output",
            "description": "Use Anthropic Claude at temperature=0 with seed for reproducible structured trading signals via AIAgentNode.",
            "workflow_snippet": {
                "id": "llm_anthropic_structured",
                "name": "Claude Structured Signal",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm_cred", "model": "claude-haiku-4-5-20251001", "temperature": 0.0, "max_tokens": 200, "seed": 42},
                    {"id": "market", "type": "OverseasStockMarketDataNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}]},
                    {
                        "id": "agent",
                        "type": "AIAgentNode",
                        "system_prompt": "You are a trading signal generator. Return only valid JSON.",
                        "user_prompt": "Based on the market data tool output, generate a trading signal for AAPL.",
                        "output_format": "structured",
                        "output_schema": {"signal": {"type": "string", "enum": ["buy", "hold", "sell"]}, "confidence": {"type": "number"}},
                        "max_tool_calls": 3,
                        "cooldown_sec": 60,
                    },
                    {"id": "summary", "type": "SummaryDisplayNode", "title": "Trading Signal", "data": "{{ nodes.agent.response }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "start", "to": "llm"},
                    {"from": "broker", "to": "market"},
                    {"from": "llm", "to": "agent", "type": "ai_model"},
                    {"from": "market", "to": "agent", "type": "tool"},
                    {"from": "agent", "to": "summary"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    },
                    {
                        "credential_id": "llm_cred",
                        "type": "llm_anthropic",
                        "data": [
                            {"key": "api_key", "value": "", "type": "password", "label": "API Key"},
                        ],
                    },
                ],
            },
            "expected_output": "A structured JSON object: {signal: 'buy'|'hold'|'sell', confidence: 0.0-1.0} validated against output_schema.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "LLMModelNode requires a credential_id referencing a valid LLM credential (llm_openai, llm_anthropic, llm_deepseek, or llm_google). Set model to the exact model ID for the provider. No data input is needed — this node only establishes the API connection.",
        "output_consumption": "The 'connection' output port uses edge type 'ai_model', NOT 'main'. Connect it to AIAgentNode's ai_model input. The connection object is not a data value — it is an internal LLM client handle passed to the agent.",
        "common_combinations": [
            "LLMModelNode → AIAgentNode (ai_model edge) — always paired",
            "LLMModelNode → AIAgentNode1 + AIAgentNode2 (fan-out: share one LLM across two agents)",
        ],
        "pitfalls": [
            "Edge type must be 'ai_model' — omitting the type field defaults to 'main' which does NOT inject the LLM connection.",
            "streaming=True streams tokens via on_llm_stream callback but may cause issues with structured output parsing — keep streaming=False for json/structured output_format.",
            "max_tokens applies to the LLM output only, not the total context window. If max_tokens is too low the response may be truncated mid-sentence.",
        ],
    }

    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="실행 트리거",
            required=False,
        ),
    ]

    _outputs: List[OutputPort] = [
        OutputPort(
            name="connection",
            type="ai_model",
            description="LLM 연결 정보 (AIAgentNode의 ai_model 포트에 연결)",
        ),
    ]

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return False

    @classmethod
    def get_field_schema(cls) -> Dict[str, FieldSchema]:
        return {
            "credential_id": FieldSchema(
                name="credential_id",
                type=FieldType.CREDENTIAL,
                description="i18n:fields.LLMModelNode.credential_id",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CUSTOM_CREDENTIAL_SELECT,
                credential_types=["llm_openai", "llm_anthropic", "llm_deepseek", "llm_google"],
            ),
            "model": FieldSchema(
                name="model",
                type=FieldType.STRING,
                description="i18n:fields.LLMModelNode.model",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                default="gpt-4o",
                placeholder="gpt-4o, claude-sonnet-4-5-20250929, llama3.1 등",
                help_text="i18n:fields.LLMModelNode.model_help",
            ),
            "temperature": FieldSchema(
                name="temperature",
                type=FieldType.NUMBER,
                description="i18n:fields.LLMModelNode.temperature",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                default=0.7,
                min_value=0.0,
                max_value=2.0,
                ui_component=UIComponent.SLIDER,
                ui_options={"step": 0.1},
            ),
            "max_tokens": FieldSchema(
                name="max_tokens",
                type=FieldType.INTEGER,
                description="i18n:fields.LLMModelNode.max_tokens",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                default=1000,
                min_value=100,
                max_value=128000,
            ),
            "seed": FieldSchema(
                name="seed",
                type=FieldType.INTEGER,
                description="i18n:fields.LLMModelNode.seed",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                help_text="i18n:fields.LLMModelNode.seed_help",
            ),
            "streaming": FieldSchema(
                name="streaming",
                type=FieldType.BOOLEAN,
                description="i18n:fields.LLMModelNode.streaming",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                default=False,
            ),
        }


class AIAgentNode(BaseNode):
    """
    AI Agent 노드 - tool 엣지로 연결된 기존 노드들을 도구로 활용하는 범용 에이전트

    워크플로우에서 LLM을 호출하여 데이터 분석, 의사결정을 수행하고,
    필요 시 tool 엣지로 연결된 노드들을 도구로 호출합니다.

    매 실행마다 stateless로 동작 (트레이딩 자동화에서 대화 기억은 불필요,
    현재 데이터를 Tool로 직접 조회하여 판단).

    포트:
    - trigger (main 엣지): 실행 트리거
    - ai_model (ai_model 엣지): LLMModelNode에서 LLM 연결 주입
    - tools (tool 엣지, 복수): 기존 노드를 Tool로 등록
    - response (출력): AI 응답 (output_format에 따라 string/object)
    """

    type: Literal["AIAgentNode"] = "AIAgentNode"
    category: NodeCategory = NodeCategory.AI

    # 실시간 노드에서 직접 연결 차단 (ThrottleNode 경유 필수)
    _connection_rules: ClassVar[List[ConnectionRule]] = [
        ConnectionRule(
            deny_direct_from=REALTIME_SOURCE_NODE_TYPES,
            required_intermediate="ThrottleNode",
            severity=ConnectionSeverity.ERROR,
            reason="i18n:connection_rules.realtime_to_ai_agent.reason",
            suggestion="i18n:connection_rules.realtime_to_ai_agent.suggestion",
        ),
    ]

    # 런타임 rate limit: 기본 60초 간격 (사용자 cooldown_sec이 우선), 동시 실행 1개
    _rate_limit: ClassVar[Optional[RateLimitConfig]] = RateLimitConfig(
        min_interval_sec=60,
        max_concurrent=1,
        on_throttle="skip",
    )

    _usage: ClassVar[Dict[str, Any]] = {
        "when_to_use": [
            "Analyze market data, account positions, or news using an LLM and produce a text summary or structured trading signal",
            "Orchestrate multiple data sources (market data, account, historical) as tools and let the LLM decide which to call",
            "Generate structured buy/sell/hold signals with confidence scores and reasoning using output_format='structured'",
            "Perform periodic risk assessments on portfolio positions using the risk_manager or technical_analyst preset",
        ],
        "when_not_to_use": [
            "For simple rule-based signal generation — use ConditionNode with a plugin (much faster, no LLM cost)",
            "For real-time tick-by-tick decisions — AIAgentNode has a minimum cooldown_sec and must not connect directly to real-time nodes",
            "For stateful multi-turn conversations — AIAgentNode is stateless by design. Each execution starts fresh.",
        ],
        "typical_scenarios": [
            "LLMModelNode → AIAgentNode (risk_manager preset) + OverseasStockAccountNode (tool) → TableDisplayNode",
            "LLMModelNode → AIAgentNode (technical_analyst preset) + OverseasStockMarketDataNode (tool) → SummaryDisplayNode",
            "LLMModelNode → AIAgentNode (structured output) → IfNode (check signal field) → OverseasStockNewOrderNode",
        ],
    }
    _features: ClassVar[List[str]] = [
        "Stateless per execution — no conversation memory. Current data is fetched via tool calls each cycle.",
        "Tool edges: any node connected via 'tool' edge type becomes an LLM-callable function. All connected tools are passed to the LLM; tool selection is handled by the LLM's own reasoning.",
        "Four output formats: text (raw string), json (parsed dict), structured (Pydantic-validated against output_schema)",
        "Four built-in presets: risk_manager, technical_analyst, news_analyst, strategist — each pre-fills system_prompt",
        "Real-time node direct connection is blocked (ERROR). Use ThrottleNode as intermediary for real-time data sources.",
        "cooldown_sec (default 60) prevents the agent from executing more often than once per minute",
        "max_total_tokens (default 100,000) caps total token spend per execution cycle",
    ]
    _anti_patterns: ClassVar[List[Dict[str, str]]] = [
        {
            "pattern": "Connecting a real-time node (RealMarketDataNode) directly to AIAgentNode without ThrottleNode",
            "reason": "Real-time nodes fire on every tick. Without throttling, AIAgentNode would call the LLM API thousands of times per minute, causing massive cost and rate limit errors. The workflow validator blocks this with an ERROR.",
            "alternative": "Insert ThrottleNode between the real-time source and AIAgentNode. Set ThrottleNode interval to match your intended analysis frequency (e.g. 60s).",
        },
        {
            "pattern": "Setting output_format='structured' without defining output_schema",
            "reason": "Without output_schema, the structured format parser has no schema to validate against, so output falls back to raw JSON without type guarantees.",
            "alternative": "Always provide output_schema when using output_format='structured'. Define the expected fields, types, and enums explicitly.",
        },
        {
            "pattern": "Using AIAgentNode for simple threshold-based decisions (e.g. if RSI < 30 then buy)",
            "reason": "LLM calls are slow (1-10 seconds), costly, and non-deterministic. A simple threshold check is better served by ConditionNode which is instantaneous and free.",
            "alternative": "Use ConditionNode with RSI plugin for threshold logic. Reserve AIAgentNode for complex reasoning that genuinely requires language understanding.",
        },
    ]
    _examples: ClassVar[List[Dict[str, Any]]] = [
        {
            "title": "Risk manager agent with account and market data tools",
            "description": "AIAgentNode with risk_manager preset uses OverseasStockAccountNode and OverseasStockMarketDataNode as tools to analyze portfolio risk and suggest position adjustments.",
            "workflow_snippet": {
                "id": "aiagent_risk_manager",
                "name": "AI Risk Manager",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm_cred", "model": "gpt-4o", "temperature": 0.3, "max_tokens": 1000},
                    {"id": "account", "type": "OverseasStockAccountNode"},
                    {"id": "market", "type": "OverseasStockMarketDataNode", "symbols": [{"symbol": "AAPL", "exchange": "NASDAQ"}, {"symbol": "NVDA", "exchange": "NASDAQ"}]},
                    {
                        "id": "agent",
                        "type": "AIAgentNode",
                        "preset": "risk_manager",
                        "user_prompt": "Analyze my current portfolio positions and assess risk. Suggest stop-loss levels for each position.",
                        "output_format": "structured",
                        "output_schema": {"positions": {"type": "array", "items": {"type": "object", "properties": {"symbol": {"type": "string"}, "risk_level": {"type": "string"}, "suggested_stop_loss": {"type": "number"}}}}},
                        "max_tool_calls": 5,
                        "cooldown_sec": 60,
                    },
                    {"id": "table", "type": "TableDisplayNode", "title": "Risk Analysis", "data": "{{ nodes.agent.response }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "start", "to": "llm"},
                    {"from": "broker", "to": "account"},
                    {"from": "broker", "to": "market"},
                    {"from": "llm", "to": "agent", "type": "ai_model"},
                    {"from": "account", "to": "agent", "type": "tool"},
                    {"from": "market", "to": "agent", "type": "tool"},
                    {"from": "agent", "to": "table"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    },
                    {
                        "credential_id": "llm_cred",
                        "type": "llm_openai",
                        "data": [
                            {"key": "api_key", "value": "", "type": "password", "label": "API Key"},
                        ],
                    },
                ],
            },
            "expected_output": "Structured JSON with positions array containing symbol, risk_level, and suggested_stop_loss for each holding.",
        },
        {
            "title": "Technical analyst agent generating buy/hold/sell signals",
            "description": "AIAgentNode in technical_analyst mode uses historical data and market quote tools to generate a structured trading signal with confidence and reasoning.",
            "workflow_snippet": {
                "id": "aiagent_tech_analyst",
                "name": "AI Technical Analyst",
                "nodes": [
                    {"id": "start", "type": "StartNode"},
                    {"id": "broker", "type": "OverseasStockBrokerNode", "credential_id": "broker_cred", "paper_trading": False},
                    {"id": "llm", "type": "LLMModelNode", "credential_id": "llm_cred", "model": "gpt-4o", "temperature": 0.2, "max_tokens": 800},
                    {"id": "historical", "type": "OverseasStockHistoricalDataNode", "symbols": [{"symbol": "TSLA", "exchange": "NASDAQ"}], "period": "1d", "count": 60},
                    {"id": "market", "type": "OverseasStockMarketDataNode", "symbols": [{"symbol": "TSLA", "exchange": "NASDAQ"}]},
                    {
                        "id": "agent",
                        "type": "AIAgentNode",
                        "preset": "technical_analyst",
                        "user_prompt": "Analyze TSLA using the available historical and market data tools. Generate a trading signal.",
                        "output_format": "structured",
                        "output_schema": {"signal": {"type": "string", "enum": ["buy", "hold", "sell"]}, "confidence": {"type": "number"}, "reasoning": {"type": "string"}},
                        "max_tool_calls": 5,
                        "cooldown_sec": 60,
                    },
                    {"id": "summary", "type": "SummaryDisplayNode", "title": "TSLA Signal", "data": "{{ nodes.agent.response }}"},
                ],
                "edges": [
                    {"from": "start", "to": "broker"},
                    {"from": "start", "to": "llm"},
                    {"from": "broker", "to": "historical"},
                    {"from": "broker", "to": "market"},
                    {"from": "llm", "to": "agent", "type": "ai_model"},
                    {"from": "historical", "to": "agent", "type": "tool"},
                    {"from": "market", "to": "agent", "type": "tool"},
                    {"from": "agent", "to": "summary"},
                ],
                "credentials": [
                    {
                        "credential_id": "broker_cred",
                        "type": "broker_ls_overseas_stock",
                        "data": [
                            {"key": "appkey", "value": "", "type": "password", "label": "App Key"},
                            {"key": "appsecret", "value": "", "type": "password", "label": "App Secret"},
                        ],
                    },
                    {
                        "credential_id": "llm_cred",
                        "type": "llm_openai",
                        "data": [
                            {"key": "api_key", "value": "", "type": "password", "label": "API Key"},
                        ],
                    },
                ],
            },
            "expected_output": "Structured JSON: {signal: 'buy'|'hold'|'sell', confidence: 0.0-1.0, reasoning: 'Technical analysis summary...'}, validated against output_schema.",
        },
    ]
    _node_guide: ClassVar[Dict[str, Any]] = {
        "input_handling": "Connect LLMModelNode via 'ai_model' edge (required). Connect tool nodes via 'tool' edges (optional, zero or more). The 'trigger' input port fires the agent via a 'main' edge from an upstream node. Set user_prompt using {{ }} expressions to inject live data context into the prompt.",
        "output_consumption": "For output_format='text': response is a string — pipe to SummaryDisplayNode. For 'json': response is a dict — pipe to TableDisplayNode or IfNode. For 'structured': response is a validated dict matching output_schema — use dot notation in expressions ({{ nodes.agent.response.signal }}) for downstream branching.",
        "common_combinations": [
            "LLMModelNode + AccountNode(tool) + MarketDataNode(tool) → AIAgentNode (risk analysis)",
            "LLMModelNode + HistoricalDataNode(tool) → AIAgentNode → IfNode (route by signal field)",
            "AIAgentNode (structured) → IfNode (check signal) → OverseasStockNewOrderNode",
        ],
        "pitfalls": [
            "tool_selection and tool_top_k fields were removed. All tool-edge nodes are passed to the LLM. The LLM decides which tools to call based on their descriptions.",
            "cooldown_sec minimum is enforced at runtime. Setting cooldown_sec=1 does not guarantee 1-second execution — it depends on the rate_limit configuration.",
            "output_format='structured' requires a valid JSON Schema in output_schema. Invalid schemas cause parsing failures.",
        ],
    }

    # === 프롬프트 ===
    preset: Optional[str] = Field(
        default=None,
        description="프리셋 (risk_manager, news_analyst 등)",
    )
    system_prompt: str = Field(
        default="",
        description="역할/페르소나 정의 (시스템 프롬프트)",
    )
    user_prompt: str = Field(
        default="",
        description="사용자 지시 ({{ }} 표현식 지원)",
    )

    # === 출력 (내장 Output Parser) ===
    output_format: Literal["text", "json", "structured"] = Field(
        default="text",
        description="출력 형식",
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="structured 모드용 출력 스키마",
    )

    # === 고급 설정 ===
    max_tool_calls: int = Field(
        default=10,
        description="실행당 최대 Tool 호출 수",
    )
    timeout_seconds: int = Field(
        default=60,
        description="LLM 호출 타임아웃 (초)",
    )
    cooldown_sec: int = Field(
        default=60,
        description="최소 실행 간격 (초)",
    )
    tool_error_strategy: Literal["retry_with_context", "skip", "abort"] = Field(
        default="retry_with_context",
        description="Tool 호출 실패 시 전략",
    )

    # === 토큰 제한 ===
    max_total_tokens: int = Field(
        default=100000,
        description="실행당 최대 총 토큰 수 (입력+출력 합계, 0=무제한)",
    )

    # === 포트 정의 ===
    _inputs: List[InputPort] = [
        InputPort(
            name="trigger",
            type="signal",
            description="실행 트리거 (main 엣지)",
            required=False,
        ),
        InputPort(
            name="ai_model",
            type="ai_model",
            description="LLM 연결 (ai_model 엣지로 LLMModelNode 연결)",
            required=True,
        ),
        InputPort(
            name="tools",
            type="tool",
            description="AI 도구 (tool 엣지로 기존 노드 연결, 복수 가능)",
            required=False,
            multiple=True,
        ),
    ]

    _outputs: List[OutputPort] = [
        OutputPort(
            name="response",
            type="any",
            description="AI 응답 (output_format에 따라: text→string, json/structured→object)",
        ),
    ]

    @classmethod
    def is_tool_enabled(cls) -> bool:
        return False

    @classmethod
    def get_field_schema(cls) -> Dict[str, FieldSchema]:
        return {
            # ═══════════════════════════════════════════════════════════
            # PARAMETERS 탭 (핵심: 프리셋 + 프롬프트 + 출력)
            # ═══════════════════════════════════════════════════════════
            "preset": FieldSchema(
                name="preset",
                type=FieldType.ENUM,
                description="i18n:fields.AIAgentNode.preset",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                enum_values=["custom", "risk_manager", "news_analyst", "technical_analyst", "strategist"],
                enum_labels={
                    "custom": "커스텀",
                    "risk_manager": "위험관리자",
                    "news_analyst": "뉴스분석가",
                    "technical_analyst": "기술분석가",
                    "strategist": "전략본부장",
                },
                default="custom",
            ),
            "system_prompt": FieldSchema(
                name="system_prompt",
                type=FieldType.STRING,
                description="i18n:fields.AIAgentNode.system_prompt",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CUSTOM_CODE_EDITOR,
                ui_options={"language": "markdown", "min_lines": 4, "max_lines": 10},
                placeholder="당신은 10년 경력의 퀀트 트레이더입니다...",
                help_text="i18n:fields.AIAgentNode.system_prompt_help",
            ),
            "user_prompt": FieldSchema(
                name="user_prompt",
                type=FieldType.STRING,
                description="i18n:fields.AIAgentNode.user_prompt",
                required=True,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.BOTH,
                ui_component=UIComponent.CUSTOM_CODE_EDITOR,
                ui_options={"language": "markdown", "min_lines": 3, "max_lines": 8},
                placeholder="현재 포지션을 분석하고 리스크를 평가해주세요.",
                example_binding="{{ nodes.account.positions }}",
                help_text="i18n:fields.AIAgentNode.user_prompt_help",
            ),
            "output_format": FieldSchema(
                name="output_format",
                type=FieldType.ENUM,
                description="i18n:fields.AIAgentNode.output_format",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                enum_values=["text", "json", "structured"],
                enum_labels={
                    "text": "텍스트",
                    "json": "JSON",
                    "structured": "구조화 (스키마)",
                },
                default="text",
            ),
            "output_schema": FieldSchema(
                name="output_schema",
                type=FieldType.JSON,
                description="i18n:fields.AIAgentNode.output_schema",
                required=False,
                category=FieldCategory.PARAMETERS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                ui_component=UIComponent.CUSTOM_CODE_EDITOR,
                ui_options={"language": "json", "min_lines": 3},
                visible_when={"output_format": "structured"},
                example={
                    "signal": {"type": "string", "enum": ["buy", "hold", "sell"], "description": "매매 신호"},
                    "confidence": {"type": "number", "description": "확신도 (0~1)"},
                    "reasoning": {"type": "string", "description": "판단 근거"},
                },
            ),

            # ═══════════════════════════════════════════════════════════
            # SETTINGS 탭 (고급: 기본값으로 충분, 필요 시 조정)
            # ═══════════════════════════════════════════════════════════
            "max_tool_calls": FieldSchema(
                name="max_tool_calls",
                type=FieldType.INTEGER,
                description="i18n:fields.AIAgentNode.max_tool_calls",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                default=10,
                min_value=1,
                max_value=50,
                help_text="i18n:fields.AIAgentNode.max_tool_calls_help",
            ),
            "timeout_seconds": FieldSchema(
                name="timeout_seconds",
                type=FieldType.INTEGER,
                description="i18n:fields.AIAgentNode.timeout_seconds",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                default=60,
                min_value=10,
                max_value=300,
            ),
            "cooldown_sec": FieldSchema(
                name="cooldown_sec",
                type=FieldType.INTEGER,
                description="i18n:fields.AIAgentNode.cooldown_sec",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                default=60,
                min_value=1,
                max_value=3600,
            ),
            "tool_error_strategy": FieldSchema(
                name="tool_error_strategy",
                type=FieldType.ENUM,
                description="i18n:fields.AIAgentNode.tool_error_strategy",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                enum_values=["retry_with_context", "skip", "abort"],
                enum_labels={
                    "retry_with_context": "재시도 (에러 컨텍스트 전달)",
                    "skip": "무시하고 계속",
                    "abort": "노드 실행 실패",
                },
                default="retry_with_context",
            ),
            "max_total_tokens": FieldSchema(
                name="max_total_tokens",
                type=FieldType.INTEGER,
                description="i18n:fields.AIAgentNode.max_total_tokens",
                required=False,
                category=FieldCategory.SETTINGS,
                expression_mode=ExpressionMode.FIXED_ONLY,
                default=100000,
                min_value=0,
                max_value=10000000,
                help_text="실행당 최대 토큰 수. 0=무제한. 초과 시 현재까지의 결과로 응답 생성.",
            ),
        }
