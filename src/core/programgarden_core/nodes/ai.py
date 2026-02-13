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
        description="LLM API credential (llm_openai, llm_anthropic 등)",
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
                credential_types=["llm_openai", "llm_anthropic", "llm_google", "llm_azure_openai", "llm_ollama"],
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
        }
